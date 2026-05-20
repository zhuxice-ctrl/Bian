import pytest

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    def test_order(self, **kwargs):
        return {}


class SuggestingAssistant:
    def __init__(self, suggested_command):
        self.suggested_command = suggested_command

    def reply(self, text, *, user_id, context):
        return {
            "status": "chat",
            "message": "I prepared a suggested command.",
            "suggested_command": self.suggested_command,
        }


def test_natural_language_stores_suggested_command(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(
            conn,
            executor=FakeExecutor(),
            natural_language=SuggestingAssistant(
                "/review-add date=2026-05-21 symbols=BTCUSDT trades=1 plan=yes pnl=0 tags=calm lesson=Follow_plan note=Calm"
            ),
        )

        response = handler.handle("record today's review", user_id="owner")

        row = conn.execute("select user_id, command_text, status from brain_suggested_commands").fetchone()
        assert response["status"] == "chat"
        assert response["suggested_command"].startswith("/review-add")
        assert row["user_id"] == "owner"
        assert row["command_text"].startswith("/review-add")
        assert row["status"] == "pending"


def test_run_suggested_executes_latest_safe_command_once(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(
            conn,
            executor=FakeExecutor(),
            natural_language=SuggestingAssistant(
                "/review-add date=2026-05-21 symbols=BTCUSDT trades=1 plan=yes pnl=0 tags=calm lesson=Follow_plan note=Calm"
            ),
        )

        handler.handle("record today's review", user_id="owner")
        first = handler.handle("/run suggested", user_id="owner")
        second = handler.handle("/run suggested", user_id="owner")

        review_count = conn.execute("select count(*) from daily_reviews").fetchone()[0]
        suggestion = conn.execute("select status, result from brain_suggested_commands").fetchone()
        assert first["status"] == "executed"
        assert first["executed_command"].startswith("/review-add")
        assert first["result"]["status"] == "saved"
        assert second["status"] == "not_found"
        assert review_count == 1
        assert suggestion["status"] == "executed"
        assert '"status": "saved"' in suggestion["result"]


@pytest.mark.parametrize(
    "suggested_command",
    [
        "/test-buy BTCUSDT 10",
        "/testnet-create-buy BTCUSDT 10",
        "/testnet-cancel symbol=BTCUSDT order_id=123",
        "/confirm 8392",
        "确认-8392",
    ],
)
def test_run_suggested_blocks_high_risk_commands(tmp_path, suggested_command):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(
            conn,
            executor=FakeExecutor(),
            natural_language=SuggestingAssistant(suggested_command),
        )

        handler.handle("test buy BTCUSDT 10U", user_id="owner")
        response = handler.handle("/run suggested", user_id="owner")

        pending_count = conn.execute("select count(*) from brain_pending_confirmations").fetchone()[0]
        suggestion = conn.execute("select status from brain_suggested_commands").fetchone()
        assert response["status"] == "blocked"
        assert "type it manually" in response["message"]
        assert pending_count == 0
        assert suggestion["status"] == "blocked"


def test_run_suggested_ignores_unknown_or_malformed_suggestion(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(
            conn,
            executor=FakeExecutor(),
            natural_language=SuggestingAssistant("not-a-command"),
        )

        handler.handle("record something", user_id="owner")
        response = handler.handle("/run suggested", user_id="owner")

        assert response["status"] == "blocked"
        assert "safe command" in response["message"]


def test_run_suggested_allows_experiment_link_commands(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(
            conn,
            executor=FakeExecutor(),
            natural_language=SuggestingAssistant(
                "/experiment-link review=review-2026-05-21 experiment=experiment-ma-BTCUSDT-1h tag=late_entry note=Replay_matches_review"
            ),
        )
        handler.handle(
            "/review-add date=2026-05-21 symbols=BTCUSDT trades=1 plan=no pnl=-1 tags=late_entry lesson=Wait note=Calm",
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
                "{}",
                "{}",
                "",
            ),
        )

        handler.handle("link this replay", user_id="owner")
        response = handler.handle("/run suggested", user_id="owner")
        link_count = conn.execute("select count(*) from review_experiment_links").fetchone()[0]

    assert response["status"] == "executed"
    assert response["result"]["status"] == "saved"
    assert link_count == 1
