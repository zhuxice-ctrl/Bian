from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.backtest.report import summarize_backtest
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.strategy.library import generate_strategy_signals


def save_strategy_profile(
    conn: sqlite3.Connection,
    *,
    name: str,
    symbol: str,
    interval: str,
    source_csv: str,
    parameters: dict[str, Any],
    strategy_name: str = "moving_average_crossover",
    description: str = "",
) -> dict[str, Any]:
    external_id = f"profile-{uuid4()}"
    with conn:
        conn.execute(
            """
            insert into strategy_profiles (
              external_id, name, strategy_name, symbol, interval, source_csv, parameters, description
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(name) do update set
              symbol = excluded.symbol,
              interval = excluded.interval,
              source_csv = excluded.source_csv,
              parameters = excluded.parameters,
              description = excluded.description,
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                external_id,
                name,
                strategy_name,
                symbol,
                interval,
                source_csv,
                json.dumps(parameters, ensure_ascii=False, sort_keys=True),
                description,
            ),
        )
    row = conn.execute("select * from strategy_profiles where name = ?", (name,)).fetchone()
    return _profile(row)


def list_strategy_profiles(conn: sqlite3.Connection, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        "select * from strategy_profiles order by id desc limit ?",
        (limit,),
    ).fetchall()
    return [_profile(row) for row in rows]


def run_ma_parameter_sweep(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    interval: str,
    source_csv: Path,
    source_csv_text: str,
    shorts: list[int],
    longs: list[int],
    starting_cash: float,
    quote_amount: float,
    fee_rate: float,
    daily_limit: int,
) -> dict[str, Any]:
    grid = [(short, long) for short in shorts for long in longs if short < long]
    if not grid:
        raise ValueError("no valid parameter combinations; short must be less than long")

    candles = load_candles_csv(source_csv, symbol)
    prices = {candle.opened_at: candle.close for candle in candles}
    sweep_id = f"sweep-{uuid4()}"
    experiments = []
    with conn:
        for index, (short, long) in enumerate(grid, start=1):
            signals = generate_strategy_signals(
                "moving_average_crossover",
                candles,
                {"short_window": short, "long_window": long},
            )
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
            experiment_id = f"experiment-{uuid4()}"
            namespaced_trades = [
                replace(trade, external_id=f"{experiment_id}-{trade_index}-{trade.side.value.lower()}")
                for trade_index, trade in enumerate(result.trades, start=1)
            ]
            conn.executemany(
                """
                insert into trades (
                  external_id, symbol, side, quantity, price, fee, timestamp, reason, source
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        trade.external_id,
                        trade.symbol,
                        trade.side.value,
                        trade.quantity,
                        trade.price,
                        trade.fee,
                        trade.timestamp.isoformat(),
                        trade.reason,
                        experiment_id,
                    )
                    for trade in namespaced_trades
                ],
            )
            parameters = {
                "short_window": short,
                "long_window": long,
                "starting_cash": starting_cash,
                "quote_amount": quote_amount,
                "fee_rate": fee_rate,
                "daily_trade_limit": daily_limit,
                "sweep_external_id": sweep_id,
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
            conn.execute(
                """
                insert into strategy_experiments (
                  external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
                ) values (?, 'moving_average_crossover', ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    symbol,
                    interval,
                    source_csv_text,
                    json.dumps(parameters, ensure_ascii=False, sort_keys=True),
                    json.dumps(metrics_payload, ensure_ascii=False, sort_keys=True),
                    f"parameter_sweep {sweep_id} run {index}",
                ),
            )
            experiments.append(
                {
                    "external_id": experiment_id,
                    "parameters": {"short_window": short, "long_window": long},
                    "metrics": metrics_payload,
                }
            )

        best = max(experiments, key=lambda item: float(item["metrics"].get("realized_pnl", 0.0)))
        result_payload = {
            "external_id": sweep_id,
            "run_count": len(experiments),
            "experiments": experiments,
            "best_experiment": best["external_id"],
            "overfitting_warning": _overfitting_warning(len(experiments)),
        }
        conn.execute(
            """
            insert into parameter_sweeps (
              external_id, strategy_name, symbol, interval, source_csv, grid, result
            ) values (?, 'moving_average_crossover', ?, ?, ?, ?, ?)
            """,
            (
                sweep_id,
                symbol,
                interval,
                source_csv_text,
                json.dumps({"shorts": shorts, "longs": longs}, ensure_ascii=False, sort_keys=True),
                json.dumps(result_payload, ensure_ascii=False, sort_keys=True),
            ),
        )
    return result_payload


def _profile(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "external_id": row["external_id"],
        "name": row["name"],
        "strategy_name": row["strategy_name"],
        "symbol": row["symbol"],
        "interval": row["interval"],
        "source_csv": row["source_csv"],
        "parameters": json.loads(row["parameters"]),
        "description": row["description"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _overfitting_warning(run_count: int) -> str:
    if run_count >= 4:
        return "Parameter sweep is research-only; validate on a separate period before treating the best run as tradable."
    return "Small sweep; collect more out-of-sample evidence before changing execution rules."
