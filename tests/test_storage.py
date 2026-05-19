import sqlite3

import pytest

from trading_learning.journal.repository import save_daily_review, save_trades
from trading_learning.learning.repository import (
    save_knowledge_card,
    save_strategy_hypothesis,
)
from trading_learning.models import Side, Trade
from trading_learning.storage.db import connect, initialize_schema
from datetime import datetime


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
        save_daily_review(
            conn,
            external_id="review-2026-05-02",
            review_date="2026-05-02",
            symbols_watched=["ETHUSDT"],
            trade_count=1,
            plan_followed=False,
            pnl=-3.0,
            mistake_tags=["追单"],
            emotion_note="有点焦虑",
            lesson="reduce size after a loss",
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

        review = conn.execute(
            """
            select review_date, symbols_watched, trade_count, plan_followed, pnl,
                   mistake_tags, emotion_note, lesson
            from daily_reviews
            where external_id = 'review-2026-05-01'
            """
        ).fetchone()
        unicode_review = conn.execute(
            """
            select mistake_tags, emotion_note
            from daily_reviews
            where external_id = 'review-2026-05-02'
            """
        ).fetchone()
        card = conn.execute(
            """
            select title, category, content
            from knowledge_cards
            where external_id = 'card-ma-lag'
            """
        ).fetchone()
        hypothesis = conn.execute(
            """
            select title, statement, status
            from strategy_hypotheses
            where external_id = 'hypothesis-ma-cross'
            """
        ).fetchone()

    assert dict(review) == {
        "review_date": "2026-05-01",
        "symbols_watched": '["BTCUSDT"]',
        "trade_count": 2,
        "plan_followed": 1,
        "pnl": 12.5,
        "mistake_tags": '["late_entry"]',
        "emotion_note": "wanted to chase after a loss",
        "lesson": "wait for planned entries",
    }
    assert dict(unicode_review) == {
        "mistake_tags": '["追单"]',
        "emotion_note": "有点焦虑",
    }
    assert dict(card) == {
        "title": "Moving average lag",
        "category": "technical_analysis",
        "content": "Moving averages confirm trends after price has already moved.",
    }
    assert dict(hypothesis) == {
        "title": "MA crossover continuation",
        "statement": "If short MA crosses above long MA, momentum may continue.",
        "status": "draft",
    }


def test_save_trades_persists_backtest_trade_fields(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    first_timestamp = datetime.fromisoformat("2026-05-20T09:00:00+00:00")
    second_timestamp = datetime.fromisoformat("2026-05-20T10:00:00+00:00")
    trades = [
        Trade(
            external_id="bt-BTCUSDT-1-buy",
            symbol="BTCUSDT",
            side=Side.BUY,
            quantity=0.01,
            price=100000.0,
            fee=1.0,
            timestamp=first_timestamp,
            reason="short MA crossed above long MA",
        ),
        Trade(
            external_id="bt-BTCUSDT-2-sell",
            symbol="BTCUSDT",
            side=Side.SELL,
            quantity=0.01,
            price=101000.0,
            fee=1.01,
            timestamp=second_timestamp,
            reason="short MA crossed below long MA",
        ),
    ]

    with connect(db_path) as conn:
        initialize_schema(conn)
        save_trades(conn, trades, source="backtest")

        rows = conn.execute(
            """
            select external_id, symbol, side, quantity, price, fee, timestamp, reason, source
            from trades
            order by id
            """
        ).fetchall()

    assert [dict(row) for row in rows] == [
        {
            "external_id": "bt-BTCUSDT-1-buy",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "price": 100000.0,
            "fee": 1.0,
            "timestamp": first_timestamp.isoformat(),
            "reason": "short MA crossed above long MA",
            "source": "backtest",
        },
        {
            "external_id": "bt-BTCUSDT-2-sell",
            "symbol": "BTCUSDT",
            "side": "SELL",
            "quantity": 0.01,
            "price": 101000.0,
            "fee": 1.01,
            "timestamp": second_timestamp.isoformat(),
            "reason": "short MA crossed below long MA",
            "source": "backtest",
        },
    ]
