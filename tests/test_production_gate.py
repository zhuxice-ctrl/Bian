from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.production_gate import production_readiness_status
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    pass


def test_production_readiness_status_is_disabled_by_default():
    status = production_readiness_status()

    assert status["real_trading_enabled"] is False
    assert status["kill_switch_active"] is True
    assert status["kill_switch"]["active"] is True
    assert status["ready"] is False
    assert "local_manual_approval" in status["missing"]


def test_brain_real_trading_status_reports_gate(tmp_path):
    with connect(tmp_path / "gate.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/real-trading-status", user_id="owner")

    assert response["status"] == "blocked"
    assert response["gate"]["real_trading_enabled"] is False
    assert response["requires_confirmation"] is False


def test_brain_real_trading_enable_is_never_enabled_by_remote_command(tmp_path):
    with connect(tmp_path / "gate.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/real-trading-enable", user_id="owner")

    assert response["status"] == "blocked"
    assert "local production readiness gate" in response["message"]


def test_brain_kill_switch_commands_keep_real_trading_blocked(tmp_path):
    with connect(tmp_path / "gate.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        status = handler.handle("/kill-switch-status", user_id="owner")
        enable = handler.handle("/kill-switch-enable", user_id="owner")
        gate = handler.handle("/real-trading-status", user_id="owner")

    assert status["status"] == "ok"
    assert status["kill_switch"]["active"] is True
    assert enable["status"] == "ok"
    assert enable["kill_switch"]["active"] is True
    assert gate["gate"]["real_trading_enabled"] is False
