from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.brain.remote_tasks import TaskQueue
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
    assert "任务" in response["message"]
    assert "queued" in response["message"]


def test_task_status_message_includes_completed_results(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        queue = TaskQueue(conn)
        task = queue.create_task(
            requester_user_id="owner",
            command_text="/queue-status",
            task_type="local_status",
            risk_level="query",
            payload={},
        )
        queue.complete_task(
            task.external_id,
            runner_id="pc-1",
            state="succeeded",
            result_summary="local runner online",
            result_payload={"ok": True},
        )
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/task-status limit=1", user_id="owner")

    assert response["status"] == "ok"
    assert "succeeded" in response["message"]
    assert "local runner online" in response["message"]


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


def test_queue_market_refresh_command_creates_token_protected_runner_task(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/queue-market-refresh symbols=BTCUSDT intervals=1h,4h limit=10",
            user_id="owner",
        )

    assert response["status"] == "queued"
    assert response["task"]["task_type"] == "market_refresh"
    assert response["task"]["risk_level"] == "data"
    assert response["task"]["payload"] == {"symbols": ["BTCUSDT"], "intervals": ["1h", "4h"], "limit": 10}
    assert "task-" in response["message"]


def test_chinese_feishu_study_aliases_route_to_safe_commands(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        queue = handler.handle(_u(r"\u5b66\u4e60\u961f\u5217"), user_id="owner")
        task_status = handler.handle(_u(r"\u4efb\u52a1\u72b6\u6001"), user_id="owner")
        coach = handler.handle(_u(r"\u4eca\u65e5\u6559\u7ec3"), user_id="owner")
        refresh = handler.handle(
            _u(r"\u8fdc\u7a0b\u5237\u65b0\u6570\u636e \u5e01\u79cd=BTCUSDT \u5468\u671f=1h \u6570\u91cf=10"),
            user_id="owner",
        )

    assert queue["status"] == "ok"
    assert "queue" in queue
    assert task_status["status"] == "ok"
    assert coach["status"] == "ok"
    assert refresh["status"] == "queued"
    assert refresh["task"]["task_type"] == "market_refresh"
