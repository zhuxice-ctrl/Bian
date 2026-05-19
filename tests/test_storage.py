import sqlite3

import pytest

from trading_learning.storage.db import connect, initialize_schema


def _insert_trade(conn, external_id="trade-1", side="BUY"):
    conn.execute(
        """
        insert into trades (
          external_id, symbol, side, quantity, price, timestamp, reason
        )
        values (?, 'BTCUSDT', ?, 1, 100, '2026-05-20T00:00:00Z', 'test')
        """,
        (external_id, side),
    )


def _insert_daily_review(conn, external_id="review-1", plan_followed=1):
    conn.execute(
        """
        insert into daily_reviews (
          external_id, review_date, symbols_watched, trade_count, plan_followed
        )
        values (?, '2026-05-20', '[]', 0, ?)
        """,
        (external_id, plan_followed),
    )


def test_connect_sets_row_factory_to_sqlite_row(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        assert conn.row_factory is sqlite3.Row


def test_connect_enables_foreign_keys(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        foreign_keys_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]

    assert foreign_keys_enabled == 1


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


def test_initialize_schema_rolls_back_when_schema_fails(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite3"

    def invalid_schema(self, encoding=None):
        return """
        create table partial_table (
          id integer primary key autoincrement
        );
        this is invalid sql;
        """

    monkeypatch.setattr("pathlib.Path.read_text", invalid_schema)

    with connect(db_path) as conn:
        with pytest.raises(sqlite3.Error):
            initialize_schema(conn)

        table_names = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert "partial_table" not in table_names


def test_trades_external_id_rejects_duplicates(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        _insert_trade(conn)

        with pytest.raises(sqlite3.IntegrityError):
            _insert_trade(conn)


def test_trades_side_rejects_invalid_values(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)

        with pytest.raises(sqlite3.IntegrityError):
            _insert_trade(conn, side="HOLD")


def test_daily_reviews_plan_followed_rejects_invalid_values(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)

        with pytest.raises(sqlite3.IntegrityError):
            _insert_daily_review(conn, plan_followed=2)
