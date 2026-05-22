from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.backtest.report import summarize_backtest
from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.config import DEFAULT_ALLOWED_SYMBOLS
from trading_learning.journal.repository import save_trades
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.strategy.moving_average import moving_average_crossover_signals


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
        short_window = int(payload.get("short", payload.get("short_window", 20)))
        long_window = int(payload.get("long", payload.get("long_window", 60)))
        starting_cash = float(payload.get("starting_cash", 1000.0))
        quote_amount = float(payload.get("quote_amount", 100.0))
        fee_rate = float(payload.get("fee", payload.get("fee_rate", 0.001)))
        daily_limit = int(payload.get("daily_limit", 5))
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
    if short_window <= 0 or long_window <= 0 or short_window >= long_window:
        return {"status": "invalid", "message": "short window must be positive and smaller than long window", "requires_confirmation": False}

    try:
        candles = load_candles_csv(csv_path, symbol)
        signals = moving_average_crossover_signals(candles, short_window=short_window, long_window=long_window)
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
    except Exception as exc:
        return {"status": "failed", "message": str(exc), "requires_confirmation": False}

    external_id = f"experiment-{uuid4()}"
    namespaced_trades = [
        replace(trade, external_id=f"{external_id}-{index}-{trade.side.value.lower()}")
        for index, trade in enumerate(result.trades, start=1)
    ]
    parameters = {
        "short_window": short_window,
        "long_window": long_window,
        "starting_cash": starting_cash,
        "quote_amount": quote_amount,
        "fee_rate": fee_rate,
        "daily_trade_limit": daily_limit,
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
                    "moving_average_crossover",
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
        "strategy_name": "moving_average_crossover",
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
