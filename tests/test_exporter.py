import json
import zipfile
from datetime import datetime

import pytest

from trading_learning.export_import.exporter import _rows_as_dicts, export_zip
from trading_learning.journal.repository import save_daily_review
from trading_learning.storage.db import connect, initialize_schema


def test_export_zip_contains_manifest_and_jsonl(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    export_path = tmp_path / "export.zip"
    with connect(db_path) as conn:
        initialize_schema(conn)
        save_daily_review(
            conn,
            external_id="review-2026-05-01",
            review_date="2026-05-01",
            symbols_watched=["BTCUSDT"],
            trade_count=1,
            plan_followed=True,
            pnl=1.2,
            mistake_tags=["追单"],
            emotion_note="有点焦虑",
            lesson="follow the plan",
        )
        export_zip(conn, export_path)

    with zipfile.ZipFile(export_path) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        daily_reviews_text = archive.read("daily_reviews.jsonl").decode("utf-8")
        daily_reviews = [
            json.loads(line)
            for line in daily_reviews_text.splitlines()
            if line.strip()
        ]
        markdown = archive.read("markdown/daily_reviews.md").decode("utf-8")

    assert names == {
        "manifest.json",
        "daily_reviews.jsonl",
        "knowledge_cards.jsonl",
        "strategy_hypotheses.jsonl",
        "ai_drafts.jsonl",
        "markdown/daily_reviews.md",
    }
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["source_system"] == "trading_learning"
    exported_at = datetime.fromisoformat(manifest["exported_at"])
    assert exported_at.tzinfo is not None

    assert len(daily_reviews) == 1
    review = daily_reviews[0]
    assert review["external_id"] == "review-2026-05-01"
    assert review["review_date"] == "2026-05-01"
    assert review["trade_count"] == 1
    assert review["pnl"] == 1.2
    assert review["lesson"] == "follow the plan"
    assert review["emotion_note"] == "有点焦虑"
    assert "追单" in daily_reviews_text
    assert "有点焦虑" in daily_reviews_text

    assert "# Daily Reviews" in markdown
    assert "## 2026-05-01" in markdown
    assert "Trade count: 1" in markdown
    assert "PnL: 1.2" in markdown
    assert "follow the plan" in markdown


def test_rows_as_dicts_rejects_unknown_tables(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)

        with pytest.raises(ValueError):
            _rows_as_dicts(conn, "not_allowed")
