from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.backtest.report import summarize_backtest
from trading_learning.backtest.validation import filter_candles_by_date, split_train_test, stress_windows, validation_warning
from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.config import DEFAULT_ALLOWED_SYMBOLS
from trading_learning.journal.repository import save_trades
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.strategy.library import generate_strategy_signals


def run_local_ma_backtest_action(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    allowed_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
) -> dict[str, Any]:
    try:
        symbol = str(payload.get("symbol", "")).upper()
        interval = str(payload.get("interval", "")).strip()
        csv_path = _safe_data_local_path(str(payload.get("csv", "")))
        strategy_name = str(payload.get("strategy", "moving_average_crossover")).strip() or "moving_average_crossover"
        starting_cash = float(payload.get("starting_cash", 1000.0))
        quote_amount = float(payload.get("quote_amount", 100.0))
        fee_rate = float(payload.get("fee", payload.get("fee_rate", 0.001)))
        daily_limit = int(payload.get("daily_limit", 5))
        start = str(payload.get("start", "")).strip()
        end = str(payload.get("end", "")).strip()
        train_ratio = float(payload.get("train_ratio", 0.7))
    except ValueError as exc:
        return {"status": "invalid", "message": str(exc), "requires_confirmation": False}

    if not symbol:
        return {"status": "invalid", "message": "missing fields: symbol", "requires_confirmation": False}
    if symbol not in tuple(item.upper() for item in allowed_symbols):
        return {
            "status": "invalid",
            "message": f"symbol not allowed: {symbol}. allowed: {', '.join(allowed_symbols)}",
            "requires_confirmation": False,
        }
    try:
        strategy_parameters = _strategy_parameters_from_payload(strategy_name, payload)
    except ValueError as exc:
        return {"status": "invalid", "message": str(exc), "requires_confirmation": False}

    try:
        candles = filter_candles_by_date(load_candles_csv(csv_path, symbol), start=start, end=end)
        if not candles:
            return {"status": "invalid", "message": "selected date range has no candles", "requires_confirmation": False}
        signals = generate_strategy_signals(strategy_name, candles, strategy_parameters)
        prices = {candle.opened_at: candle.close for candle in candles}
        result = run_spot_backtest(
            symbol=symbol,
            signals=signals,
            prices_by_timestamp=prices,
            starting_cash=starting_cash,
            quote_amount_per_buy=quote_amount,
            fee_rate=fee_rate,
            daily_trade_limit=daily_limit,
        )
        metrics = summarize_backtest(result)
        train_candles, test_candles = split_train_test(candles, train_ratio=train_ratio)
        train_metrics = _backtest_metrics_for_candles(
            symbol=symbol,
            candles=train_candles,
            strategy_name=strategy_name,
            strategy_parameters=strategy_parameters,
            starting_cash=starting_cash,
            quote_amount=quote_amount,
            fee_rate=fee_rate,
            daily_limit=daily_limit,
        )
        test_metrics = _backtest_metrics_for_candles(
            symbol=symbol,
            candles=test_candles,
            strategy_name=strategy_name,
            strategy_parameters=strategy_parameters,
            starting_cash=starting_cash,
            quote_amount=quote_amount,
            fee_rate=fee_rate,
            daily_limit=daily_limit,
        )
        stress = stress_windows(candles, window_size=min(24, max(2, len(candles) // 3)), top_n=3)
    except Exception as exc:
        return {"status": "failed", "message": str(exc), "requires_confirmation": False}

    external_id = f"experiment-{uuid4()}"
    namespaced_trades = [
        replace(trade, external_id=f"{external_id}-{index}-{trade.side.value.lower()}")
        for index, trade in enumerate(result.trades, start=1)
    ]
    parameters = {
        **strategy_parameters,
        "starting_cash": starting_cash,
        "quote_amount": quote_amount,
        "fee_rate": fee_rate,
        "daily_trade_limit": daily_limit,
        "start": start,
        "end": end,
        "train_ratio": train_ratio,
    }
    metrics_payload = {
        "trade_count": result.trade_count,
        "ending_cash": result.ending_cash,
        "position_quantity": result.position_quantity,
        "round_trips": metrics.round_trips,
        "win_count": metrics.win_count,
        "loss_count": metrics.loss_count,
        "win_rate": metrics.win_rate,
        "realized_pnl": metrics.realized_pnl,
        "total_fees": metrics.total_fees,
        "validation": {
            "train": train_metrics,
            "out_of_sample": test_metrics,
            "stress_windows": stress,
            "warning": validation_warning(
                train_pnl=float(train_metrics.get("realized_pnl", 0.0)),
                test_pnl=float(test_metrics.get("realized_pnl", 0.0)),
                stress_window_count=len(stress),
            ),
        },
    }
    try:
        with conn:
            save_trades(conn, namespaced_trades, source=external_id)
            conn.execute(
                """
                insert into strategy_experiments (
                  external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    external_id,
                    strategy_name,
                    symbol,
                    interval,
                    str(csv_path),
                    json.dumps(parameters, ensure_ascii=False, sort_keys=True),
                    json.dumps(metrics_payload, ensure_ascii=False, sort_keys=True),
                    str(payload.get("note", "dashboard local backtest")).replace("_", " "),
                ),
            )
    except sqlite3.Error as exc:
        return {"status": "failed", "message": str(exc), "requires_confirmation": False}
    return {
        "status": "saved",
        "message": f"saved local backtest {external_id}",
        "external_id": external_id,
        "strategy_name": strategy_name,
        "symbol": symbol,
        "interval": interval,
        "source_csv": str(csv_path),
        "parameters": parameters,
        "metrics": metrics_payload,
        "requires_confirmation": False,
    }


def persist_experiment_review_action(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    allowed_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
) -> dict[str, Any]:
    experiment_id = str(payload.get("experiment", "")).strip()
    if not experiment_id:
        return {"status": "invalid", "message": "missing fields: experiment", "requires_confirmation": False}
    handler = BrainCommandHandler(conn, executor=object(), allowed_market_symbols=allowed_symbols)
    return handler.handle(f"/experiment-review experiment={experiment_id}", user_id="dashboard")


def commit_experiment_review_action(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    allowed_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
) -> dict[str, Any]:
    experiment_id = str(payload.get("experiment", "")).strip()
    review_date = str(payload.get("date", "")).strip()
    if not experiment_id:
        return {"status": "invalid", "message": "missing fields: experiment", "requires_confirmation": False}
    command = f"/experiment-review-commit experiment={experiment_id}"
    if review_date:
        command = f"{command} date={review_date}"
    handler = BrainCommandHandler(conn, executor=object(), allowed_market_symbols=allowed_symbols)
    return handler.handle(command, user_id="dashboard")


def _safe_data_local_path(value: str) -> Path:
    if not value.strip():
        raise ValueError("missing fields: csv")
    path = Path(value.replace("\\", "/"))
    allowed_root = Path("data/local").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("path must be under data/local") from exc
    return path


def _strategy_parameters_from_payload(strategy_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = strategy_name.strip().lower()
    if normalized in {"moving_average_crossover", "ma_cross", "ma"}:
        short_window = int(payload.get("short", payload.get("short_window", 20)))
        long_window = int(payload.get("long", payload.get("long_window", 60)))
        if short_window <= 0 or long_window <= 0 or short_window >= long_window:
            raise ValueError("short window must be positive and smaller than long window")
        return {"short_window": short_window, "long_window": long_window}
    if normalized == "breakout":
        lookback = int(payload.get("lookback", 20))
        if lookback < 2:
            raise ValueError("lookback must be at least 2")
        return {"lookback": lookback}
    if normalized == "mean_reversion":
        window = int(payload.get("window", 20))
        threshold_pct = float(payload.get("threshold_pct", 0.03))
        if window < 2 or threshold_pct <= 0:
            raise ValueError("mean reversion window must be at least 2 and threshold_pct must be positive")
        return {"window": window, "threshold_pct": threshold_pct}
    if normalized == "volatility_filter":
        short_window = int(payload.get("short", payload.get("short_window", 20)))
        long_window = int(payload.get("long", payload.get("long_window", 60)))
        min_range_pct = float(payload.get("min_range_pct", 0.01))
        if short_window <= 0 or long_window <= 0 or short_window >= long_window or min_range_pct <= 0:
            raise ValueError("volatility filter parameters are invalid")
        return {"short_window": short_window, "long_window": long_window, "min_range_pct": min_range_pct}
    raise ValueError(f"unknown strategy: {strategy_name}")


def _backtest_metrics_for_candles(
    *,
    symbol: str,
    candles: list[Any],
    strategy_name: str,
    strategy_parameters: dict[str, Any],
    starting_cash: float,
    quote_amount: float,
    fee_rate: float,
    daily_limit: int,
) -> dict[str, Any]:
    if not candles:
        return {"candle_count": 0, "trade_count": 0, "realized_pnl": 0.0, "win_rate": 0.0}
    signals = generate_strategy_signals(strategy_name, candles, strategy_parameters)
    prices = {candle.opened_at: candle.close for candle in candles}
    result = run_spot_backtest(
        symbol=symbol,
        signals=signals,
        prices_by_timestamp=prices,
        starting_cash=starting_cash,
        quote_amount_per_buy=quote_amount,
        fee_rate=fee_rate,
        daily_trade_limit=daily_limit,
    )
    metrics = summarize_backtest(result)
    return {
        "candle_count": len(candles),
        "trade_count": result.trade_count,
        "realized_pnl": metrics.realized_pnl,
        "win_rate": metrics.win_rate,
        "max_drawdown": 0.0,
    }
