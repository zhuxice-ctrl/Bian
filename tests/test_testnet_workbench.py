from datetime import date

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    def __init__(self):
        self.created = []

    def account(self):
        return {
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "0.5", "locked": "0.0"},
                {"asset": "USDT", "free": "1000", "locked": "0.0"},
                {"asset": "ETH", "free": "0", "locked": "0"},
            ],
        }

    def create_order(self, **kwargs):
        self.created.append(kwargs)
        return {"orderId": 123, "symbol": kwargs["symbol"], "status": "FILLED"}


def test_testnet_status_returns_sanitized_account_summary(tmp_path):
    with connect(tmp_path / "testnet.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/testnet-status", user_id="owner")

    assert response["status"] == "ok"
    assert response["account"]["account_type"] == "SPOT"
    assert response["account"]["balances"] == [
        {"asset": "BTC", "free": "0.5", "locked": "0.0"},
        {"asset": "USDT", "free": "1000", "locked": "0.0"},
    ]
    assert "api" not in str(response).lower()


def test_confirmed_testnet_order_writes_local_order_record(tmp_path):
    executor = FakeExecutor()
    today = date.today().isoformat()
    with connect(tmp_path / "testnet.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor, confirmation_code=lambda: "8392")
        handler.handle(
            f"/plan-set date={today} symbols=BTCUSDT max_trades=5 bias=neutral conditions=test forbidden=none",
            user_id="owner",
        )
        handler.handle("/checklist symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm", user_id="owner")
        handler.handle("/testnet-create-buy BTCUSDT 10", user_id="owner")

        response = handler.handle("/confirm 8392", user_id="owner")
        row = conn.execute("select * from testnet_order_records").fetchone()

    assert response["status"] == "executed"
    assert row["symbol"] == "BTCUSDT"
    assert row["order_id"] == "123"
    assert row["action"] == "create_order"
    assert row["status"] == "FILLED"


def test_feishu_style_testnet_command_still_requires_confirmation(tmp_path):
    with connect(tmp_path / "testnet.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), confirmation_code=lambda: "8392")

        response = handler.handle("/testnet-create-buy BTCUSDT 10", user_id="owner")

    assert response["requires_confirmation"] is False
    assert response["status"] == "blocked"
