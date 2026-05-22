from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


def _u(value: str) -> str:
    return value.encode("ascii").decode("unicode_escape")


class FakeExecutor:
    pass


def test_queue_backtest_ma_command_creates_remote_task(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/queue-backtest-ma symbol=BTCUSDT interval=1h csv=data/local/BTCUSDT-1h.csv short=20 long=60",
            user_id="owner",
        )
        row = conn.execute("select * from remote_tasks").fetchone()

    assert response["status"] == "queued"
    assert response["task"]["task_type"] == "backtest_ma"
    assert response["task"]["state"] == "queued"
    assert row["requester_user_id"] == "owner"


def test_task_status_lists_recent_tasks(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        queued = handler.handle(
            "/queue-backtest-ma symbol=ETHUSDT interval=1h csv=data/local/ETHUSDT-1h.csv short=10 long=30",
            user_id="owner",
        )

        response = handler.handle("/task-status limit=3", user_id="owner")

    assert response["status"] == "ok"
    assert response["tasks"][0]["external_id"] == queued["task"]["external_id"]
    assert response["tasks"][0]["state"] == "queued"


def test_queue_backtest_rejects_unsupported_symbol(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/queue-backtest-ma symbol=DOGEUSDT interval=1h csv=data/local/DOGEUSDT-1h.csv short=20 long=60",
            user_id="owner",
        )

    assert response["status"] == "invalid"
    assert "not allowed" in response["message"]


def test_chinese_remote_backtest_alias_queues_local_runner_task(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            _u(
                r"\u8fdc\u7a0b\u56de\u6d4b \u5e01\u79cd=BTCUSDT \u5468\u671f=1h "
                r"\u6587\u4ef6=data/local/BTCUSDT-1h.csv \u77ed\u7ebf=20 \u957f\u7ebf=60"
            ),
            user_id="owner",
        )

    assert response["status"] == "queued"
    assert response["task"]["task_type"] == "backtest_ma"
    assert response["task"]["payload"]["symbol"] == "BTCUSDT"
