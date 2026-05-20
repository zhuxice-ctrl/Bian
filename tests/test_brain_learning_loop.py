from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    def test_order(self, **kwargs):
        return {}


def _seed_review_experiment_and_knowledge(handler, conn):
    handler.handle(
        "/review-add date=2026-05-21 symbols=BTCUSDT trades=2 plan=no pnl=-12.5 tags=late_entry lesson=Wait_for_confirmation note=Anxious",
        user_id="owner",
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
            '{"trade_count": 2, "realized_pnl": -2.5, "win_rate": 0.0}',
            "replay after review",
        ),
    )
    knowledge = handler.handle(
        "/knowledge-add title=Late_entry_control category=psychology content=Wait_for_close_confirmation tags=late_entry,discipline",
        user_id="owner",
    )
    handler.handle(
        f"/mistake-link review=review-2026-05-21 card={knowledge['external_id']} tag=late_entry",
        user_id="owner",
    )


def test_experiment_link_persists_review_to_experiment_link(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        _seed_review_experiment_and_knowledge(handler, conn)

        response = handler.handle(
            "/experiment-link review=review-2026-05-21 experiment=experiment-ma-BTCUSDT-1h tag=late_entry note=Replay_matches_review",
            user_id="owner",
        )
        row = conn.execute("select * from review_experiment_links").fetchone()

    assert response["status"] == "saved"
    assert response["requires_confirmation"] is False
    assert row["review_external_id"] == "review-2026-05-21"
    assert row["experiment_external_id"] == "experiment-ma-BTCUSDT-1h"
    assert row["tag"] == "late_entry"
    assert row["note"] == "Replay matches review"


def test_experiment_link_rejects_missing_review_or_experiment(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        missing_review = handler.handle(
            "/experiment-link review=review-missing experiment=experiment-missing tag=late_entry",
            user_id="owner",
        )

    assert missing_review["status"] == "not_found"
    assert "review" in missing_review["message"]


def test_experiment_link_rejects_missing_experiment_after_review_exists(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        handler.handle(
            "/review-add date=2026-05-21 symbols=BTCUSDT trades=1 plan=yes pnl=0 tags=calm lesson=Follow_plan note=Calm",
            user_id="owner",
        )

        response = handler.handle(
            "/experiment-link review=review-2026-05-21 experiment=experiment-missing tag=late_entry",
            user_id="owner",
        )
        link_count = conn.execute("select count(*) from review_experiment_links").fetchone()[0]

    assert response["status"] == "not_found"
    assert "experiment" in response["message"]
    assert link_count == 0


def test_review_context_returns_review_experiments_and_knowledge(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        _seed_review_experiment_and_knowledge(handler, conn)
        handler.handle(
            "/experiment-link review=review-2026-05-21 experiment=experiment-ma-BTCUSDT-1h tag=late_entry note=Replay_matches_review",
            user_id="owner",
        )

        response = handler.handle("/review-context review=review-2026-05-21", user_id="owner")

    assert response["status"] == "ok"
    assert response["review"]["external_id"] == "review-2026-05-21"
    assert response["review"]["mistake_tags"] == ["late_entry"]
    assert response["experiments"] == [
        {
            "external_id": "experiment-ma-BTCUSDT-1h",
            "strategy_name": "moving_average_crossover",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "parameters": {"short_window": 2, "long_window": 3},
            "metrics": {"trade_count": 2, "realized_pnl": -2.5, "win_rate": 0.0},
            "link_tag": "late_entry",
            "link_note": "Replay matches review",
        }
    ]
    assert response["knowledge_cards"][0]["title"] == "Late entry control"
    assert response["knowledge_cards"][0]["link_tag"] == "late_entry"
    assert response["requires_confirmation"] is False


def test_review_context_rejects_missing_review(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/review-context review=review-missing", user_id="owner")

    assert response["status"] == "not_found"
    assert "review" in response["message"]
