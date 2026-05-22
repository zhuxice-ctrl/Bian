from __future__ import annotations

import sqlite3
from typing import Any

from trading_learning.config import DEFAULT_ALLOWED_SYMBOLS
from trading_learning.market_data.catalog import inventory_datasets
from trading_learning.workspace import build_workspace_state


def build_daily_coach_plan(
    conn: sqlite3.Connection,
    *,
    allowed_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
) -> dict[str, Any]:
    workspace = build_workspace_state(conn)
    datasets = inventory_datasets(allowed_symbols=allowed_symbols)
    cached = [dataset for dataset in datasets if dataset["exists"]]
    counts = workspace["counts"]

    if sum(counts.values()) == 0:
        return {
            "stage": "empty_workspace",
            "summary": "Workspace is clean. Start by creating real local market data, then run one baseline backtest.",
            "actions": workspace["next_steps"],
        }
    if not cached:
        return {
            "stage": "missing_market_data",
            "summary": "Learning records exist, but local market cache is missing.",
            "actions": [
                {
                    "title": "Refresh public BTC/ETH market data",
                    "command": "trading-learning refresh-market-data --limit 500",
                }
            ],
        }
    if counts["strategy_experiments"] == 0:
        return {
            "stage": "ready_for_backtest",
            "summary": "Market data is cached. Run one baseline MA backtest before adding more strategy ideas.",
            "actions": [
                {
                    "title": "Run baseline MA backtest",
                    "command": (
                        "trading-learning backtest-ma --csv data/local/market_data/BTCUSDT/BTCUSDT-1h.csv "
                        "--symbol BTCUSDT --short-window 20 --long-window 60"
                    ),
                }
            ],
        }
    if counts["experiment_review_drafts"] == 0:
        experiment_id = _latest_experiment_id(conn)
        return {
            "stage": "review_experiment",
            "summary": "An experiment exists but has not been reviewed. Review before running more parameter searches.",
            "actions": [
                {
                    "title": "Generate experiment review",
                    "command": f"/experiment-review experiment={experiment_id}",
                }
            ],
        }
    return {
        "stage": "continue_research",
        "summary": "Workspace has data, experiments, and review material. Ask the coach for the next hypothesis.",
        "actions": [
            {
                "title": "Create next experiment proposal",
                "command": "/coach-next",
            }
        ],
    }


def _latest_experiment_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("select external_id from strategy_experiments order by id desc limit 1").fetchone()
    return row["external_id"] if row else "<experiment_id>"
