from datetime import date

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class RecordingExecutor:
    def __init__(self):
        self.test_orders = []
        self.created_orders = []
        self.cancelled_orders = []
        self.get_orders = []

    def test_order(self, **kwargs):
        self.test_orders.append(kwargs)
        return {"ok": True}

    def create_order(self, **kwargs):
        self.created_orders.append(kwargs)
        return {"orderId": 123, "status": "NEW"}

    def cancel_order(self, **kwargs):
        self.cancelled_orders.append(kwargs)
        return {"orderId": kwargs["order_id"], "status": "CANCELED"}

    def get_order(self, **kwargs):
        self.get_orders.append(kwargs)
        return {"orderId": kwargs["order_id"], "status": "NEW"}


def _today():
    return date.today().isoformat()


def test_plan_and_checklist_allow_test_buy(tmp_path):
    executor = RecordingExecutor()
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor, confirmation_code=lambda: "111111")

        missing = handler.handle("/test-buy BTCUSDT 10", user_id="owner")
        plan = handler.handle(
            f"/plan-set date={_today()} symbols=BTCUSDT,ETHUSDT max_trades=5 bias=long_only conditions=trend_up forbidden=fomo",
            user_id="owner",
        )
        checklist = handler.handle(
            "/checklist symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm",
            user_id="owner",
        )
        pending = handler.handle("/test-buy BTCUSDT 10", user_id="owner")
        executed = handler.handle("/confirm 111111", user_id="owner")

        assert missing["status"] == "blocked"
        assert "plan" in missing["message"].lower()
        assert plan["status"] == "saved"
        assert checklist["status"] == "saved"
        assert pending["status"] == "pending_confirmation"
        assert executed["status"] == "executed"
        assert executor.test_orders == [
            {"symbol": "BTCUSDT", "side": "BUY", "order_type": "MARKET", "quote_order_qty": 10.0}
        ]


def test_plan_blocks_symbol_not_allowed(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=RecordingExecutor())
        handler.handle(
            f"/plan-set date={_today()} symbols=ETHUSDT max_trades=5 bias=neutral conditions=only_eth forbidden=btc",
            user_id="owner",
        )
        handler.handle("/checklist symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm", user_id="owner")

        response = handler.handle("/test-buy BTCUSDT 10", user_id="owner")

        assert response["status"] == "blocked"
        assert "not in today's plan" in response["message"]


def test_plan_status_returns_current_plan_and_checklists(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=RecordingExecutor())
        handler.handle(
            f"/plan-set date={_today()} symbols=BTCUSDT max_trades=3 bias=neutral conditions=range forbidden=chase",
            user_id="owner",
        )
        handler.handle("/checklist symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm", user_id="owner")

        response = handler.handle(f"/plan-status date={_today()}", user_id="owner")

        assert response["status"] == "ok"
        assert response["plan"]["symbols"] == ["BTCUSDT"]
        assert response["plan"]["max_trades"] == 3
        assert response["checklists"][0]["symbol"] == "BTCUSDT"


def test_knowledge_add_search_and_mistake_link(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=RecordingExecutor())
        review = handler.handle(
            "/review-add date=2026-05-20 symbols=BTCUSDT trades=1 plan=no pnl=-1 tags=fomo lesson=Pause note=Anxious",
            user_id="owner",
        )
        card = handler.handle(
            "/knowledge-add title=FOMO_control category=psychology content=Pause_before_entry tags=fomo,discipline",
            user_id="owner",
        )
        search = handler.handle("/knowledge-search query=FOMO limit=5", user_id="owner")
        link = handler.handle(
            f"/mistake-link review={review['external_id']} card={card['external_id']} tag=fomo",
            user_id="owner",
        )

        assert card["status"] == "saved"
        assert search["status"] == "ok"
        assert search["cards"][0]["title"] == "FOMO control"
        assert search["cards"][0]["tags"] == ["fomo", "discipline"]
        assert link["status"] == "saved"
        assert conn.execute("select count(*) from mistake_knowledge_links").fetchone()[0] == 1


def test_testnet_create_cancel_and_get_order_commands(tmp_path):
    executor = RecordingExecutor()
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor, confirmation_code=lambda: "222222")
        handler.handle(
            f"/plan-set date={_today()} symbols=BTCUSDT max_trades=5 bias=neutral conditions=test forbidden=none",
            user_id="owner",
        )
        handler.handle("/checklist symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm", user_id="owner")

        pending_create = handler.handle("/testnet-create-buy BTCUSDT 10", user_id="owner")
        created = handler.handle("/confirm 222222", user_id="owner")
        pending_cancel = handler.handle("/testnet-cancel symbol=BTCUSDT order_id=123", user_id="owner")
        cancelled = handler.handle("/confirm 222222", user_id="owner")
        order = handler.handle("/testnet-order symbol=BTCUSDT order_id=123", user_id="owner")

        assert pending_create["status"] == "pending_confirmation"
        assert created["status"] == "executed"
        assert executor.created_orders == [
            {"symbol": "BTCUSDT", "side": "BUY", "order_type": "MARKET", "quote_order_qty": 10.0}
        ]
        assert pending_cancel["status"] == "pending_confirmation"
        assert cancelled["status"] == "executed"
        assert executor.cancelled_orders == [{"symbol": "BTCUSDT", "order_id": 123}]
        assert order["status"] == "ok"
        assert order["order"]["status"] == "NEW"
