from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
from typing import Any

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.brain.remote_tasks import RemoteTask
from trading_learning.brain.remote_tasks import remote_task_from_dict


CAPABILITIES = ("local_status", "backtest_ma", "market_refresh")


class MissingRunnerExecutor:
    pass


class RunnerClient:
    def __init__(self, *, server_url: str, token: str) -> None:
        self.server_url = server_url.rstrip("/")
        self.token = token

    def claim(self, runner_id: str, capabilities: tuple[str, ...]) -> RemoteTask | None:
        body = self._post(
            "/runner/claim",
            {"runner_id": runner_id, "capabilities": list(capabilities)},
        )
        if body["status"] == "empty":
            return None
        return remote_task_from_dict(body["task"])

    def complete(
        self,
        task_id: str,
        *,
        runner_id: str,
        state: str,
        result_summary: str,
        result_payload: dict[str, Any],
        error_message: str = "",
    ) -> None:
        self._post(
            "/runner/complete",
            {
                "runner_id": runner_id,
                "task_id": task_id,
                "state": state,
                "result_summary": result_summary,
                "result_payload": result_payload,
                "error_message": error_message,
            },
        )

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.server_url}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Bian-Runner-Token": self.token,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


class QuantTaskExecutor:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        allowed_symbols: tuple[str, ...],
        kline_fetcher: Any | None = None,
    ) -> None:
        self.conn = conn
        self.allowed_symbols = allowed_symbols
        self.kline_fetcher = kline_fetcher

    def execute(self, task: RemoteTask) -> dict[str, Any]:
        if task.task_type == "local_status":
            return {
                "state": "succeeded",
                "result_summary": "local runner online",
                "result_payload": {
                    "capabilities": list(CAPABILITIES),
                    "allowed_symbols": list(self.allowed_symbols),
                },
            }
        if task.task_type == "backtest_ma":
            return self._execute_backtest_ma(task)
        if task.task_type == "market_refresh":
            return self._execute_market_refresh(task)
        return {
            "state": "rejected",
            "result_summary": f"unsupported local task type: {task.task_type}",
            "result_payload": {},
            "error_message": f"unsupported local task type: {task.task_type}",
        }

    def _execute_backtest_ma(self, task: RemoteTask) -> dict[str, Any]:
        payload = task.payload
        command = (
            "/backtest-ma "
            f"csv={payload.get('csv', '')} "
            f"symbol={payload.get('symbol', '')} "
            f"interval={payload.get('interval', '')} "
            f"short={payload.get('short', '')} "
            f"long={payload.get('long', '')} "
            f"starting_cash={payload.get('starting_cash', 1000)} "
            f"quote_amount={payload.get('quote_amount', 100)} "
            f"fee={payload.get('fee', 0.001)} "
            f"daily_limit={payload.get('daily_limit', 5)}"
        )
        handler = BrainCommandHandler(
            self.conn,
            executor=MissingRunnerExecutor(),
            allowed_market_symbols=self.allowed_symbols,
        )
        response = handler.handle(command, user_id="local-runner")
        if response["status"] == "saved":
            return {
                "state": "succeeded",
                "result_summary": response["message"],
                "result_payload": response,
            }
        return {
            "state": "failed",
            "result_summary": response.get("message", "local backtest failed"),
            "result_payload": response,
            "error_message": response.get("message", ""),
        }

    def _execute_market_refresh(self, task: RemoteTask) -> dict[str, Any]:
        payload = task.payload
        command = (
            "/market-refresh "
            f"symbols={','.join(str(symbol) for symbol in payload.get('symbols', []))} "
            f"intervals={','.join(str(interval) for interval in payload.get('intervals', []))} "
            f"limit={payload.get('limit', 500)}"
        )
        handler = BrainCommandHandler(
            self.conn,
            executor=MissingRunnerExecutor(),
            allowed_market_symbols=self.allowed_symbols,
            kline_fetcher=self.kline_fetcher,
        )
        response = handler.handle(command, user_id="local-runner")
        if response["status"] == "saved":
            return {
                "state": "succeeded",
                "result_summary": response["message"],
                "result_payload": response,
            }
        return {
            "state": "failed",
            "result_summary": response.get("message", "local market refresh failed"),
            "result_payload": response,
            "error_message": response.get("message", ""),
        }


def run_runner_once(
    *,
    client: Any,
    conn: sqlite3.Connection,
    runner_id: str,
    allowed_symbols: tuple[str, ...],
) -> bool:
    task = client.claim(runner_id, CAPABILITIES)
    if task is None:
        return False
    result = QuantTaskExecutor(conn, allowed_symbols=allowed_symbols).execute(task)
    client.complete(
        task.external_id,
        runner_id=runner_id,
        state=result["state"],
        result_summary=result.get("result_summary", ""),
        result_payload=result.get("result_payload", {}),
        error_message=result.get("error_message", ""),
    )
    return True


def run_runner_loop(
    *,
    client: RunnerClient,
    conn: sqlite3.Connection,
    runner_id: str,
    allowed_symbols: tuple[str, ...],
    interval_seconds: float,
    once: bool,
) -> None:
    while True:
        run_runner_once(
            client=client,
            conn=conn,
            runner_id=runner_id,
            allowed_symbols=allowed_symbols,
        )
        if once:
            return
        time.sleep(interval_seconds)
