from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from trading_learning.ops import backup_database


RESET_CONFIRMATION = "RESET_LOCAL_WORKSPACE"

BUSINESS_TABLES = (
    "trades",
    "daily_reviews",
    "knowledge_cards",
    "knowledge_card_tags",
    "mistake_knowledge_links",
    "review_experiment_links",
    "learning_reports",
    "strategy_hypotheses",
    "strategy_experiments",
    "ai_drafts",
    "experiment_review_drafts",
    "brain_suggested_commands",
    "brain_pending_confirmations",
    "brain_audit_logs",
    "trading_plans",
    "pre_trade_checklists",
    "remote_tasks",
    "experiment_proposals",
    "strategy_profiles",
    "parameter_sweeps",
    "testnet_order_records",
)

WORKSPACE_COUNT_TABLES = (
    "daily_reviews",
    "knowledge_cards",
    "learning_reports",
    "strategy_experiments",
    "trades",
    "remote_tasks",
    "testnet_order_records",
    "experiment_review_drafts",
    "experiment_proposals",
    "strategy_profiles",
    "parameter_sweeps",
)


def build_workspace_state(conn: sqlite3.Connection) -> dict[str, Any]:
    counts = {table: _table_count(conn, table) for table in WORKSPACE_COUNT_TABLES}
    total_records = sum(counts.values())
    return {
        "status": "empty" if total_records == 0 else "active",
        "has_real_learning_data": any(
            counts[table] > 0
            for table in ("daily_reviews", "knowledge_cards", "learning_reports")
        ),
        "has_research_data": any(
            counts[table] > 0
            for table in ("strategy_experiments", "trades", "experiment_review_drafts", "parameter_sweeps")
        ),
        "counts": counts,
        "source_counts": {
            "manual_learning": counts["daily_reviews"] + counts["knowledge_cards"] + counts["learning_reports"],
            "backtest_generated": counts["strategy_experiments"] + counts["trades"] + counts["experiment_review_drafts"],
            "remote_task": counts["remote_tasks"],
            "testnet": counts["testnet_order_records"],
            "strategy_research": counts["experiment_proposals"] + counts["strategy_profiles"] + counts["parameter_sweeps"],
        },
        "next_steps": _next_steps(counts),
    }


def reset_workspace(
    conn: sqlite3.Connection,
    *,
    db_path: Path,
    backup_dir: Path,
    confirm: str,
) -> dict[str, Any]:
    if confirm != RESET_CONFIRMATION:
        return {
            "status": "confirmation_required",
            "message": f"Pass confirm={RESET_CONFIRMATION} to clear local workspace records.",
            "requires_confirmation": False,
        }
    backup = backup_database(db_path, backup_dir)
    existing = _existing_tables(conn)
    conn.execute("begin")
    try:
        for table in BUSINESS_TABLES:
            if table in existing:
                conn.execute(f"delete from {table}")
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    return {
        "status": "reset",
        "message": "Local workspace records cleared after backup. Market CSV cache and environment secrets were not touched.",
        "backup": backup,
        "workspace_state": build_workspace_state(conn),
        "requires_confirmation": False,
    }


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"select count(*) from {table}").fetchone()[0])
    except sqlite3.Error:
        return 0


def _existing_tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("select name from sqlite_master where type = 'table'").fetchall()
    }


def _next_steps(counts: dict[str, int]) -> list[dict[str, str]]:
    if sum(counts.values()) == 0:
        return [
            {
                "title": "Refresh public market data",
                "command": "trading-learning refresh-market-data --limit 500",
            },
            {
                "title": "Run the first local backtest",
                "command": (
                    "trading-learning backtest-ma --csv data/local/market_data/BTCUSDT/BTCUSDT-1h.csv "
                    "--symbol BTCUSDT --short-window 20 --long-window 60"
                ),
            },
            {
                "title": "Record the first real review",
                "command": "添加复盘 日期=2026-05-22 币种=BTCUSDT 交易数=0 遵守计划=是 盈亏=0 教训=从真实数据开始",
            },
        ]
    if counts.get("strategy_experiments", 0) > 0 and counts.get("experiment_review_drafts", 0) == 0:
        return [
            {
                "title": "Generate an experiment review draft",
                "command": "/experiment-review experiment=<experiment_id>",
            }
        ]
    if counts.get("daily_reviews", 0) == 0:
        return [
            {
                "title": "Record a daily review",
                "command": "添加复盘 日期=2026-05-22 币种=BTCUSDT 交易数=0 遵守计划=是 盈亏=0 教训=记录今天学到的内容",
            }
        ]
    return [
        {
            "title": "Ask the coach for the next study step",
            "command": "/coach-next",
        }
    ]
