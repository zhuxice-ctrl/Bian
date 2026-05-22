import sqlite3

from trading_learning.ops import backup_database
from trading_learning.ops import build_local_health
from trading_learning.ops import restore_database
from trading_learning.storage.db import connect, initialize_schema


def test_build_local_health_reports_core_tables_and_counts(tmp_path):
    db_path = tmp_path / "health.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into daily_reviews (
              external_id, review_date, symbols_watched, trade_count, plan_followed, pnl
            ) values ('review-1', '2026-05-22', '["BTCUSDT"]', 1, 1, 0)
            """
        )
        conn.commit()

    health = build_local_health(db_path)

    assert health["status"] == "ok"
    assert health["database"]["exists"] is True
    assert health["counts"]["daily_reviews"] == 1
    assert health["counts"]["strategy_experiments"] == 0
    assert "secret" not in str(health).lower()


def test_backup_and_restore_database_round_trip(tmp_path):
    db_path = tmp_path / "source.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into knowledge_cards (external_id, title, category, content)
            values ('card-1', 'Risk', 'risk', 'Keep keys local')
            """
        )
        conn.commit()

    backup = backup_database(db_path, tmp_path / "backups")
    restored_path = tmp_path / "restored.sqlite3"
    restore_database(backup["backup_path"], restored_path)

    with sqlite3.connect(restored_path) as conn:
        count = conn.execute("select count(*) from knowledge_cards").fetchone()[0]

    assert backup["status"] == "ok"
    assert backup["backup_path"].endswith(".sqlite3")
    assert count == 1
