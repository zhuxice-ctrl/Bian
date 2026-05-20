import json
from http.server import HTTPServer
from threading import Thread

from trading_learning.brain.commands import BrainCommandHandler, PendingConfirmation
from trading_learning.brain.service import BrainRequestHandler, build_handler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    def __init__(self):
        self.test_orders = []

    def test_order(self, **kwargs):
        self.test_orders.append(kwargs)
        return {}


class FailingExecutor:
    def test_order(self, **kwargs):
        raise RuntimeError("testnet credentials are not configured")


def test_brain_status_command_returns_safe_summary(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/status", user_id="owner")

        assert response["status"] == "ok"
        assert "testnet" in response["message"].lower()
        assert response["requires_confirmation"] is False


def test_test_order_requires_confirmation_before_execution(tmp_path):
    executor = FakeExecutor()
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor, confirmation_code=lambda: "8392")

        response = handler.handle("/test-buy BTCUSDT 10", user_id="owner")

        assert response["status"] == "pending_confirmation"
        assert response["confirmation_code"] == "8392"
        assert "确认-8392" in response["message"]
        assert executor.test_orders == []


def test_confirmation_executes_pending_test_order_once(tmp_path):
    executor = FakeExecutor()
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor, confirmation_code=lambda: "8392")

        handler.handle("/test-buy BTCUSDT 10", user_id="owner")
        response = handler.handle("确认-8392", user_id="owner")
        second_response = handler.handle("确认-8392", user_id="owner")

        assert response["status"] == "executed"
        assert executor.test_orders == [
            {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quote_order_qty": 10.0,
            }
        ]
        assert second_response["status"] == "not_found"
        audit_count = conn.execute("select count(*) from brain_audit_logs").fetchone()[0]
        pending_count = conn.execute("select count(*) from brain_pending_confirmations").fetchone()[0]
        assert audit_count >= 3
        assert pending_count == 0


def test_ascii_confirmation_executes_pending_test_order(tmp_path):
    executor = FakeExecutor()
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor, confirmation_code=lambda: "8392")

        handler.handle("/test-buy BTCUSDT 10", user_id="owner")
        response = handler.handle("/confirm 8392", user_id="owner")

        assert response["status"] == "executed"
        assert executor.test_orders == [
            {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quote_order_qty": 10.0,
            }
        ]


def test_confirmation_failure_keeps_pending_order(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FailingExecutor(), confirmation_code=lambda: "8392")

        handler.handle("/test-buy BTCUSDT 10", user_id="owner")
        response = handler.handle("确认-8392", user_id="owner")

        pending_count = conn.execute("select count(*) from brain_pending_confirmations").fetchone()[0]
        assert response["status"] == "failed"
        assert "testnet credentials" in response["message"]
        assert pending_count == 1


def test_rejects_unauthorized_user(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), allowed_user_ids=("owner",))

        response = handler.handle("/status", user_id="intruder")

        assert response["status"] == "forbidden"


def test_brain_http_service_handles_command(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        command_handler = BrainCommandHandler(conn, executor=FakeExecutor())
        handler_cls = build_handler(command_handler)
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/brain/command",
                data=json.dumps({"text": "/status", "user_id": "owner"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            thread.join()

        assert body["status"] == "ok"
