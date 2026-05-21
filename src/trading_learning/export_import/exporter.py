from __future__ import annotations

import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path


_ALLOWED_EXPORT_TABLES = {
    "trades",
    "daily_reviews",
    "knowledge_cards",
    "strategy_hypotheses",
    "strategy_experiments",
    "review_experiment_links",
    "learning_reports",
    "experiment_review_drafts",
    "ai_drafts",
}


def _rows_as_dicts(conn: sqlite3.Connection, table: str) -> list[dict]:
    if table not in _ALLOWED_EXPORT_TABLES:
        raise ValueError(f"Table is not allowed for export: {table}")
    rows = conn.execute(f"select * from {table} order by id").fetchall()
    return [dict(row) for row in rows]


def export_zip(conn: sqlite3.Connection, export_path: Path) -> None:
    export_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.4.0",
        "source_system": "trading_learning",
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    daily_reviews = _rows_as_dicts(conn, "daily_reviews")
    trades = _rows_as_dicts(conn, "trades")
    knowledge_cards = _rows_as_dicts(conn, "knowledge_cards")
    hypotheses = _rows_as_dicts(conn, "strategy_hypotheses")
    experiments = _rows_as_dicts(conn, "strategy_experiments")
    review_experiment_links = _rows_as_dicts(conn, "review_experiment_links")
    learning_reports = _rows_as_dicts(conn, "learning_reports")
    experiment_review_drafts = _rows_as_dicts(conn, "experiment_review_drafts")
    ai_drafts = _rows_as_dicts(conn, "ai_drafts")

    markdown_reviews = ["# Daily Reviews", ""]
    for review in daily_reviews:
        markdown_reviews.extend(
            [
                f"## {review['review_date']}",
                "",
                f"- Trade count: {review['trade_count']}",
                f"- PnL: {review['pnl']}",
                f"- Lesson: {review['lesson']}",
                "",
            ]
        )

    with zipfile.ZipFile(export_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("daily_reviews.jsonl", to_jsonl(daily_reviews))
        archive.writestr("trades.jsonl", to_jsonl(trades))
        archive.writestr("knowledge_cards.jsonl", to_jsonl(knowledge_cards))
        archive.writestr("strategy_hypotheses.jsonl", to_jsonl(hypotheses))
        archive.writestr("strategy_experiments.jsonl", to_jsonl(experiments))
        archive.writestr("review_experiment_links.jsonl", to_jsonl(review_experiment_links))
        archive.writestr("learning_reports.jsonl", to_jsonl(learning_reports))
        archive.writestr("experiment_review_drafts.jsonl", to_jsonl(experiment_review_drafts))
        archive.writestr("ai_drafts.jsonl", to_jsonl(ai_drafts))
        archive.writestr("markdown/daily_reviews.md", "\n".join(markdown_reviews))


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
