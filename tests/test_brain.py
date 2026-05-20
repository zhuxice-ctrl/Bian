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


def test_review_add_command_persists_daily_review(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/review-add date=2026-05-20 symbols=BTCUSDT,ETHUSDT trades=2 plan=yes pnl=12.5 tags=late_entry,chasing lesson=Wait_for_planned_entries note=Calm",
            user_id="owner",
        )

        row = conn.execute("select * from daily_reviews where review_date = '2026-05-20'").fetchone()
        assert response["status"] == "saved"
        assert response["external_id"] == "review-2026-05-20"
        assert row["symbols_watched"] == '["BTCUSDT", "ETHUSDT"]'
        assert row["trade_count"] == 2
        assert row["plan_followed"] == 1
        assert row["pnl"] == 12.5
        assert row["mistake_tags"] == '["late_entry", "chasing"]'
        assert row["lesson"] == "Wait for planned entries"
        assert row["emotion_note"] == "Calm"


def test_review_summary_command_returns_recent_reviews(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        handler.handle(
            "/review-add date=2026-05-20 symbols=BTCUSDT trades=2 plan=yes pnl=12.5 tags=late_entry lesson=Wait note=Calm",
            user_id="owner",
        )
        handler.handle(
            "/review-add date=2026-05-21 symbols=ETHUSDT trades=1 plan=no pnl=-3 tags=fomo lesson=Pause note=Anxious",
            user_id="owner",
        )

        response = handler.handle("/review-summary limit=1", user_id="owner")

        assert response["status"] == "ok"
        assert response["reviews"] == [
            {
                "review_date": "2026-05-21",
                "symbols_watched": ["ETHUSDT"],
                "trade_count": 1,
                "plan_followed": False,
                "pnl": -3.0,
                "mistake_tags": ["fomo"],
                "lesson": "Pause",
            }
        ]


def test_lesson_command_persists_knowledge_card(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/lesson title=MA_lag category=technical content=Moving_average_signals_lag_price",
            user_id="owner",
        )

        row = conn.execute("select title, category, content from knowledge_cards").fetchone()
        assert response["status"] == "saved"
        assert response["external_id"].startswith("knowledge-")
        assert row["title"] == "MA lag"
        assert row["category"] == "technical"
        assert row["content"] == "Moving average signals lag price"
