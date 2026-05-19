from __future__ import annotations

import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def rows_as_dicts(conn: sqlite3.Connection, table: str) -> list[dict]:
    rows = conn.execute(f"select * from {table} order by id").fetchall()
    return [dict(row) for row in rows]


def export_zip(conn: sqlite3.Connection, export_path: Path) -> None:
    export_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0.0",
        "source_system": "trading_learning",
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    daily_reviews = rows_as_dicts(conn, "daily_reviews")
    knowledge_cards = rows_as_dicts(conn, "knowledge_cards")
    hypotheses = rows_as_dicts(conn, "strategy_hypotheses")
    ai_drafts = rows_as_dicts(conn, "ai_drafts")

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
        archive.writestr("knowledge_cards.jsonl", to_jsonl(knowledge_cards))
        archive.writestr("strategy_hypotheses.jsonl", to_jsonl(hypotheses))
        archive.writestr("ai_drafts.jsonl", to_jsonl(ai_drafts))
        archive.writestr("markdown/daily_reviews.md", "\n".join(markdown_reviews))


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
