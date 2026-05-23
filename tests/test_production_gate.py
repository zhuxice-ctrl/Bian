from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.production_gate import RealOrderIntent
from trading_learning.production_gate import RealTradingRiskConfig
from trading_learning.production_gate import evaluate_real_order_risk
from trading_learning.production_gate import production_readiness_status
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    def __init__(self):
        self.created = []

    def create_order(self, **kwargs):
        self.created.append(kwargs)
        return {"orderId": 1}


def test_production_readiness_status_is_disabled_by_default():
    status = production_readiness_status()

    assert status["real_trading_enabled"] is False
    assert status["kill_switch_active"] is True
    assert status["kill_switch"]["active"] is True
    assert status["ready"] is False
    assert "local_manual_approval" in status["missing"]
    assert "daily_loss_limit_configured" in status["missing"]
    assert "dry_run_verified" in status["missing"]


def test_real_order_risk_checks_are_independent_from_exchange_client():
    config = RealTradingRiskConfig(
        allowed_symbols=("BTCUSDT",),
        max_quote_order_qty=50,
        max_daily_loss=25,
        max_position_quote=100,
        cooldown_seconds=60,
    )

    allowed = evaluate_real_order_risk(
        RealOrderIntent(symbol="BTCUSDT", side="BUY", order_type="MARKET", quote_order_qty=25),
        config,
        daily_loss=0,
        current_position_quote=20,
        seconds_since_last_order=120,
    )
    too_large = evaluate_real_order_risk(
        RealOrderIntent(symbol="BTCUSDT", side="BUY", order_type="MARKET", quote_order_qty=60),
        config,
        daily_loss=0,
        current_position_quote=20,
        seconds_since_last_order=120,
    )
    cooldown = evaluate_real_order_risk(
        RealOrderIntent(symbol="BTCUSDT", side="BUY", order_type="MARKET", quote_order_qty=25),
        config,
        daily_loss=0,
        current_position_quote=20,
        seconds_since_last_order=10,
    )

    assert allowed.allowed is True
    assert too_large.allowed is False
    assert too_large.reason == "max quote order quantity exceeded"
    assert cooldown.allowed is False
    assert cooldown.reason == "cooldown active"


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


def test_brain_real_order_command_is_blocked_and_never_calls_executor(tmp_path):
    executor = FakeExecutor()
    with connect(tmp_path / "gate.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor)

        response = handler.handle("/real-create-buy BTCUSDT 10", user_id="owner")

    assert response["status"] == "blocked"
    assert response["requires_confirmation"] is False
    assert executor.created == []


def test_brain_real_dry_run_simulates_order_path_without_sending_order(tmp_path):
    executor = FakeExecutor()
    with connect(tmp_path / "gate.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor)

        response = handler.handle("/real-dry-run-buy symbol=BTCUSDT quote=10", user_id="owner")

    assert response["status"] == "dry_run"
    assert response["order_path"]["would_send_order"] is False
    assert response["order_path"]["symbol"] == "BTCUSDT"
    assert response["gate"]["real_trading_enabled"] is False
    assert executor.created == []


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
