from datetime import datetime

from trading_learning.brain.remote_tasks import RemoteTask
from trading_learning.runner import QuantTaskExecutor
from trading_learning.runner import run_runner_once
from trading_learning.storage.db import connect, initialize_schema


def _task(task_type, payload):
    return RemoteTask(
        external_id="task-1",
        requester_user_id="owner",
        command_text="queued",
        task_type=task_type,
        risk_level="query",
        payload=payload,
        state="claimed",
        runner_id="pc-1",
        result_summary="",
        result_payload={},
        error_message="",
        created_at="2026-05-22 00:00:00",
        claimed_at="2026-05-22 00:00:01",
        completed_at=None,
        updated_at="2026-05-22 00:00:01",
    )


class FakeClient:
    def __init__(self, task):
        self.task = task
        self.completed = None

    def claim(self, runner_id, capabilities):
        return self.task

    def complete(self, task_id, runner_id, state, result_summary, result_payload, error_message=""):
        self.completed = {
            "task_id": task_id,
            "runner_id": runner_id,
            "state": state,
            "result_summary": result_summary,
            "result_payload": result_payload,
            "error_message": error_message,
        }


def test_quant_task_executor_handles_local_status(tmp_path):
    with connect(tmp_path / "local.sqlite3") as conn:
        initialize_schema(conn)
        executor = QuantTaskExecutor(conn, allowed_symbols=("BTCUSDT", "ETHUSDT"))

        result = executor.execute(_task("local_status", {}))

    assert result["state"] == "succeeded"
    assert "local runner online" in result["result_summary"]
    assert result["result_payload"]["capabilities"] == ["local_status", "backtest_ma", "market_refresh"]


def test_quant_task_executor_runs_backtest_ma(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    rows = ["opened_at,open,high,low,close,volume"]
    for index in range(80):
        rows.append(f"{datetime(2026, 5, 1, index % 24).isoformat()}+00:00,100,101,99,{100 + index},10")
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    with connect(tmp_path / "local.sqlite3") as conn:
        initialize_schema(conn)
        executor = QuantTaskExecutor(conn, allowed_symbols=("BTCUSDT",))

        result = executor.execute(
            _task(
                "backtest_ma",
                {
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "csv": "data/local/BTCUSDT-1h.csv",
                    "short": 3,
                    "long": 8,
                    "starting_cash": 1000,
                    "quote_amount": 100,
                    "fee": 0.001,
                    "daily_limit": 5,
                },
            )
        )
        experiment_count = conn.execute("select count(*) from strategy_experiments").fetchone()[0]

    assert result["state"] == "succeeded"
    assert result["result_payload"]["status"] == "saved"
    assert experiment_count == 1


def test_quant_task_executor_runs_market_refresh_with_safe_fetcher(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_fetcher(symbol, interval, limit, **kwargs):
        from datetime import timezone

        from trading_learning.models import Candle

        assert symbol == "BTCUSDT"
        assert interval == "1h"
        assert limit == 2
        return [
            Candle(
                symbol=symbol,
                opened_at=datetime(2026, 5, 21, 0, 0, tzinfo=timezone.utc),
                open=100,
                high=110,
                low=90,
                close=105,
                volume=1,
            )
        ]

    with connect(tmp_path / "local.sqlite3") as conn:
        initialize_schema(conn)
        executor = QuantTaskExecutor(conn, allowed_symbols=("BTCUSDT",), kline_fetcher=fake_fetcher)

        result = executor.execute(
            _task(
                "market_refresh",
                {"symbols": ["BTCUSDT"], "intervals": ["1h"], "limit": 2},
            )
        )

    assert result["state"] == "succeeded"
    assert "refreshed 1 datasets" in result["result_summary"]
    assert result["result_payload"]["count"] == 1


def test_run_runner_once_claims_executes_and_reports(tmp_path):
    with connect(tmp_path / "local.sqlite3") as conn:
        initialize_schema(conn)
        client = FakeClient(_task("local_status", {}))

        did_work = run_runner_once(
            client=client,
            conn=conn,
            runner_id="pc-1",
            allowed_symbols=("BTCUSDT",),
        )

    assert did_work is True
    assert client.completed["state"] == "succeeded"
    assert client.completed["task_id"] == "task-1"
