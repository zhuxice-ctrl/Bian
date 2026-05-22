import pytest

from trading_learning.brain.remote_tasks import TaskQueue
from trading_learning.storage.db import connect, initialize_schema


def test_task_queue_creates_lists_claims_and_completes_task(tmp_path):
    with connect(tmp_path / "tasks.sqlite3") as conn:
        initialize_schema(conn)
        queue = TaskQueue(conn)

        task = queue.create_task(
            requester_user_id="owner",
            command_text="/queue-backtest-ma symbol=BTCUSDT interval=1h csv=data/local/BTCUSDT-1h.csv short=20 long=60",
            task_type="backtest_ma",
            payload={"symbol": "BTCUSDT", "interval": "1h"},
            risk_level="backtest",
        )
        listed = queue.list_recent(limit=5)
        claimed = queue.claim_next(runner_id="pc-1", capabilities=("backtest_ma",))
        queue.complete_task(
            task.external_id,
            runner_id="pc-1",
            state="succeeded",
            result_summary="saved experiment experiment-1",
            result_payload={"external_id": "experiment-1"},
        )
        completed = queue.get_task(task.external_id)

    assert listed[0].external_id == task.external_id
    assert claimed is not None
    assert claimed.external_id == task.external_id
    assert completed is not None
    assert completed.state == "succeeded"
    assert completed.result_summary == "saved experiment experiment-1"


def test_task_queue_rejects_unsupported_task_type(tmp_path):
    with connect(tmp_path / "tasks.sqlite3") as conn:
        initialize_schema(conn)
        queue = TaskQueue(conn)

        with pytest.raises(ValueError, match="unsupported task type"):
            queue.create_task(
                requester_user_id="owner",
                command_text="real buy",
                task_type="real_order",
                payload={},
                risk_level="real_trading",
            )
