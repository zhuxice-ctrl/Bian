import zipfile

from trading_learning.export_import.exporter import export_zip
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
            mistake_tags=[],
            emotion_note="calm",
            lesson="follow the plan",
        )
        export_zip(conn, export_path)

    with zipfile.ZipFile(export_path) as archive:
        names = set(archive.namelist())

    assert "manifest.json" in names
    assert "daily_reviews.jsonl" in names
    assert "markdown/daily_reviews.md" in names
