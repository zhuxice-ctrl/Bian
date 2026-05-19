from trading_learning.storage.db import connect, initialize_schema


def test_initialize_schema_creates_core_tables(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        table_names = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert {
        "trades",
        "daily_reviews",
        "knowledge_cards",
        "strategy_hypotheses",
        "ai_drafts",
    }.issubset(table_names)
