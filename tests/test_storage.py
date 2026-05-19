import sqlite3

import pytest

from trading_learning.journal.repository import save_daily_review
from trading_learning.learning.repository import (
    save_knowledge_card,
    save_strategy_hypothesis,
)
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


def test_repositories_store_review_and_learning_records(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        save_daily_review(
            conn,
            external_id="review-2026-05-01",
            review_date="2026-05-01",
            symbols_watched=["BTCUSDT"],
            trade_count=2,
            plan_followed=True,
            pnl=12.5,
            mistake_tags=["late_entry"],
            emotion_note="wanted to chase after a loss",
            lesson="wait for planned entries",
        )
        save_knowledge_card(
            conn,
            external_id="card-ma-lag",
            title="Moving average lag",
            category="technical_analysis",
            content="Moving averages confirm trends after price has already moved.",
        )
        save_strategy_hypothesis(
            conn,
            external_id="hypothesis-ma-cross",
            title="MA crossover continuation",
            statement="If short MA crosses above long MA, momentum may continue.",
        )

        review_count = conn.execute("select count(*) from daily_reviews").fetchone()[0]
        card_count = conn.execute("select count(*) from knowledge_cards").fetchone()[0]
        hypothesis_count = conn.execute(
            "select count(*) from strategy_hypotheses"
        ).fetchone()[0]

    assert review_count == 1
    assert card_count == 1
    assert hypothesis_count == 1
