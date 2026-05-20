from datetime import date
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.models import Candle
from trading_learning.storage.db import connect, initialize_schema


def _u(value: str) -> str:
    return value.encode("ascii").decode("unicode_escape")


class FakeExecutor:
    def __init__(self):
        self.created_orders = []

    def create_order(self, **kwargs):
        self.created_orders.append(kwargs)
        return {"orderId": 123, "symbol": kwargs["symbol"], "status": "FILLED"}


def test_chinese_status_alias_returns_brain_status(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(_u(r"\u72b6\u6001"), user_id="owner")

        assert response["status"] == "ok"
        assert "testnet" in response["message"].lower()


def test_chinese_plan_and_checklist_aliases_persist_records(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        plan = handler.handle(
            _u(
                r"\u8bbe\u7f6e\u8ba1\u5212 \u65e5\u671f=2026-05-22 \u5e01\u79cd=BTCUSDT,ETHUSDT "
                r"\u6700\u5927\u4ea4\u6613=5 \u65b9\u5411=neutral \u6761\u4ef6=trend_up \u7981\u6b62=fomo"
            ),
            user_id="owner",
        )
        checklist = handler.handle(
            _u(
                r"\u4ea4\u6613\u524d\u68c0\u67e5 \u65e5\u671f=2026-05-22 \u5e01\u79cd=BTCUSDT "
                r"\u8ba1\u5212=\u662f \u5f62\u6001=\u662f \u98ce\u9669=\u662f \u60c5\u7eea=\u51b7\u9759"
            ),
            user_id="owner",
        )
        status = handler.handle(_u(r"\u8ba1\u5212\u72b6\u6001 \u65e5\u671f=2026-05-22"), user_id="owner")

        assert plan["status"] == "saved"
        assert checklist["status"] == "saved"
        assert status["plan"]["symbols"] == ["BTCUSDT", "ETHUSDT"]
        assert status["checklists"][0]["symbol"] == "BTCUSDT"


def test_chinese_review_alias_persists_daily_review(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            _u(
                r"\u6dfb\u52a0\u590d\u76d8 \u65e5\u671f=2026-05-22 \u5e01\u79cd=BTCUSDT "
                r"\u4ea4\u6613=2 \u9075\u5b88\u8ba1\u5212=\u662f \u76c8\u4e8f=3.5 "
                r"\u6807\u7b7e=chasing \u6559\u8bad=Wait_for_confirmation \u7b14\u8bb0=Calm"
            ),
            user_id="owner",
        )

        row = conn.execute("select * from daily_reviews where review_date = '2026-05-22'").fetchone()
        assert response["status"] == "saved"
        assert row["symbols_watched"] == '["BTCUSDT"]'
        assert row["trade_count"] == 2
        assert row["plan_followed"] == 1
        assert row["pnl"] == 3.5


def test_chinese_learning_and_summary_keywords_route_to_readonly_commands(tmp_path):
    today = date.today().isoformat()
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        handler.handle(
            f"/review-add date={today} symbols=BTCUSDT trades=1 plan=no pnl=-1 tags=fomo lesson=Pause note=Anxious",
            user_id="owner",
        )

        learning = handler.handle(_u(r"\u4eca\u5929\u5b66\u4ec0\u4e48"), user_id="owner")
        reviews = handler.handle(_u(r"\u6700\u8fd1\u590d\u76d8"), user_id="owner")
        experiments = handler.handle(_u(r"\u6700\u8fd1\u5b9e\u9a8c"), user_id="owner")

        assert learning["status"] == "ok"
        assert reviews["status"] == "ok"
        assert reviews["reviews"][0]["review_date"] == today
        assert experiments["status"] == "ok"


def test_chinese_testnet_buy_alias_still_requires_confirmation(tmp_path):
    executor = FakeExecutor()
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor, confirmation_code=lambda: "8392")
        today = date.today().isoformat()
        handler.handle(
            f"/plan-set date={today} symbols=BTCUSDT max_trades=5 bias=neutral conditions=test forbidden=none",
            user_id="owner",
        )
        handler.handle("/checklist symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm", user_id="owner")

        response = handler.handle(_u(r"\u6d4b\u8bd5\u7f51\u4e70\u5165 BTCUSDT 10U"), user_id="owner")

        assert response["status"] == "pending_confirmation"
        assert response["requires_confirmation"] is True
        assert response["confirmation_code"] == "8392"
        assert executor.created_orders == []


def test_chinese_confirm_alias_executes_pending_testnet_order(tmp_path):
    executor = FakeExecutor()
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=executor, confirmation_code=lambda: "8392")
        today = date.today().isoformat()
        handler.handle(
            f"/plan-set date={today} symbols=BTCUSDT max_trades=5 bias=neutral conditions=test forbidden=none",
            user_id="owner",
        )
        handler.handle("/checklist symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm", user_id="owner")
        handler.handle(_u(r"\u6d4b\u8bd5\u7f51\u4e70\u5165 BTCUSDT 10U"), user_id="owner")

        response = handler.handle(_u(r"\u786e\u8ba4 8392"), user_id="owner")

        assert response["status"] == "executed"
        assert executor.created_orders[0]["symbol"] == "BTCUSDT"


def test_chinese_history_download_file_alias_maps_to_output(tmp_path):
    def fake_fetcher(**kwargs):
        return [
            Candle(
                symbol="BTCUSDT",
                opened_at=datetime.fromisoformat("2026-05-22T00:00:00+00:00"),
                open=1.0,
                high=2.0,
                low=0.5,
                close=1.5,
                volume=10.0,
            )
        ]

    output = Path("data/local") / f"alias-{uuid4().hex}.csv"
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), kline_fetcher=fake_fetcher)
        try:
            command = (
                _u(
                    r"\u4e0b\u8f7d\u5386\u53f2 \u5e01\u79cd=BTCUSDT \u5468\u671f=1h "
                    r"\u6570\u91cf=1 \u6587\u4ef6="
                )
                + str(output)
            )
            response = handler.handle(
                command,
                user_id="owner",
            )
        finally:
            if output.exists():
                output.unlink()

        assert response["status"] == "saved"
        assert response["path"] == str(output)
