import sqlite3

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.cli import main
from trading_learning.storage.db import connect, initialize_schema
from trading_learning.workspace import RESET_CONFIRMATION
from trading_learning.workspace import build_workspace_state
from trading_learning.workspace import reset_workspace


class FakeExecutor:
    pass


def test_workspace_state_reports_empty_next_steps(tmp_path):
    db_path = tmp_path / "workspace.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        state = build_workspace_state(conn)

    assert state["status"] == "empty"
    assert state["has_real_learning_data"] is False
    assert state["counts"]["strategy_experiments"] == 0
    assert state["next_steps"][0]["command"].startswith("trading-learning refresh-market-data")


def test_reset_workspace_backs_up_and_clears_business_tables(tmp_path):
    db_path = tmp_path / "workspace.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into daily_reviews (
              external_id, review_date, symbols_watched, trade_count, plan_followed, pnl
            ) values ('review-1', '2026-05-22', '["BTCUSDT"]', 1, 1, 3.5)
            """
        )
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
            ) values ('exp-1', 'moving_average_crossover', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{}', '{}', 'real run')
            """
        )
        conn.commit()
        result = reset_workspace(conn, db_path=db_path, backup_dir=tmp_path / "backups", confirm=RESET_CONFIRMATION)
        state = build_workspace_state(conn)

    assert result["status"] == "reset"
    assert result["backup"]["backup_path"].endswith(".sqlite3")
    assert state["status"] == "empty"
    assert state["counts"]["daily_reviews"] == 0
    assert state["counts"]["strategy_experiments"] == 0

    with sqlite3.connect(result["backup"]["backup_path"]) as backup_conn:
        assert backup_conn.execute("select count(*) from daily_reviews").fetchone()[0] == 1


def test_reset_workspace_rejects_missing_confirmation(tmp_path):
    db_path = tmp_path / "workspace.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        result = reset_workspace(conn, db_path=db_path, backup_dir=tmp_path / "backups", confirm="wrong")

    assert result["status"] == "confirmation_required"


def test_cli_reset_workspace_requires_confirmation_and_clears_data(tmp_path, monkeypatch):
    db_path = tmp_path / "workspace.sqlite3"
    backup_dir = tmp_path / "backups"
    with connect(db_path) as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into knowledge_cards (external_id, title, category, content)
            values ('card-1', 'Risk', 'system', 'temporary')
            """
        )
        conn.commit()
    monkeypatch.setenv("TRADING_LEARNING_DB_PATH", str(db_path))

    rejected = main(["reset-workspace", "--confirm", "wrong", "--backup-dir", str(backup_dir)])
    accepted = main(["reset-workspace", "--confirm", RESET_CONFIRMATION, "--backup-dir", str(backup_dir)])

    with connect(db_path) as conn:
        count = conn.execute("select count(*) from knowledge_cards").fetchone()[0]

    assert rejected == 1
    assert accepted == 0
    assert count == 0
    assert list(backup_dir.glob("*.sqlite3"))


def test_brain_workspace_status_and_reset(tmp_path):
    db_path = tmp_path / "workspace.sqlite3"
    with connect(db_path) as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into knowledge_cards (external_id, title, category, content)
            values ('card-1', 'Risk', 'system', 'temporary')
            """
        )
        conn.commit()
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), db_path=db_path, backup_dir=tmp_path / "backups")

        status = handler.handle("/workspace-status", user_id="owner")
        reset = handler.handle(f"/workspace-reset confirm={RESET_CONFIRMATION}", user_id="owner")
        after = handler.handle("/workspace-status", user_id="owner")

    assert status["workspace_state"]["status"] == "active"
    assert reset["status"] == "reset"
    assert after["workspace_state"]["status"] == "empty"
