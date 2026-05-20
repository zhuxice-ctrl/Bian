import json
import zipfile
from datetime import datetime

import pytest

from trading_learning.export_import.exporter import _rows_as_dicts, export_zip
from trading_learning.journal.repository import save_daily_review, save_trades
from trading_learning.models import Side, Trade
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
        save_trades(
            conn,
            [
                Trade(
                    external_id="bt-BTCUSDT-1-buy",
                    symbol="BTCUSDT",
                    side=Side.BUY,
                    quantity=0.01,
                    price=100000.0,
                    fee=1.0,
                    timestamp=datetime.fromisoformat("2026-05-01T09:00:00+00:00"),
                    reason="short MA crossed above long MA",
                )
            ],
        )
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "experiment-ma-BTCUSDT-1h",
                "moving_average_crossover",
                "BTCUSDT",
                "1h",
                "data/local/BTCUSDT-1h.csv",
                '{"short_window": 2, "long_window": 3}',
                '{"trade_count": 2, "realized_pnl": 12.5}',
                "first replay",
            ),
        )
        conn.execute(
            """
            insert into review_experiment_links (
              review_external_id, experiment_external_id, tag, note
            ) values (?, ?, ?, ?)
            """,
            (
                "review-2026-05-01",
                "experiment-ma-BTCUSDT-1h",
                "late_entry",
                "replayed the same setup",
            ),
        )
        conn.execute(
            """
            insert into learning_reports (
              external_id, report_type, period_start, period_end, content
            ) values (?, ?, ?, ?, ?)
            """,
            (
                "learning-report-daily-2026-05-01",
                "daily",
                "2026-05-01",
                "2026-05-01",
                '{"summary": "follow the plan"}',
            ),
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
        trades_text = archive.read("trades.jsonl").decode("utf-8")
        trades = [
            json.loads(line)
            for line in trades_text.splitlines()
            if line.strip()
        ]
        experiments_text = archive.read("strategy_experiments.jsonl").decode("utf-8")
        experiments = [
            json.loads(line)
            for line in experiments_text.splitlines()
            if line.strip()
        ]
        review_experiment_links_text = archive.read("review_experiment_links.jsonl").decode("utf-8")
        review_experiment_links = [
            json.loads(line)
            for line in review_experiment_links_text.splitlines()
            if line.strip()
        ]
        learning_reports_text = archive.read("learning_reports.jsonl").decode("utf-8")
        learning_reports = [
            json.loads(line)
            for line in learning_reports_text.splitlines()
            if line.strip()
        ]
        markdown = archive.read("markdown/daily_reviews.md").decode("utf-8")

    assert names == {
        "manifest.json",
        "daily_reviews.jsonl",
        "trades.jsonl",
        "knowledge_cards.jsonl",
        "strategy_hypotheses.jsonl",
        "strategy_experiments.jsonl",
        "review_experiment_links.jsonl",
        "learning_reports.jsonl",
        "ai_drafts.jsonl",
        "markdown/daily_reviews.md",
    }
    assert manifest["schema_version"] == "1.3.0"
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

    assert len(trades) == 1
    assert trades[0]["external_id"] == "bt-BTCUSDT-1-buy"
    assert trades[0]["symbol"] == "BTCUSDT"
    assert trades[0]["side"] == "BUY"

    assert len(experiments) == 1
    assert experiments[0]["external_id"] == "experiment-ma-BTCUSDT-1h"
    assert experiments[0]["strategy_name"] == "moving_average_crossover"
    assert experiments[0]["symbol"] == "BTCUSDT"

    assert len(review_experiment_links) == 1
    assert review_experiment_links[0]["review_external_id"] == "review-2026-05-01"
    assert review_experiment_links[0]["experiment_external_id"] == "experiment-ma-BTCUSDT-1h"

    assert len(learning_reports) == 1
    assert learning_reports[0]["external_id"] == "learning-report-daily-2026-05-01"
    assert learning_reports[0]["report_type"] == "daily"

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
