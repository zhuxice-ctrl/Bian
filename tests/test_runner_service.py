import json
import urllib.error
import urllib.request
from http.server import HTTPServer
from threading import Thread

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.brain.remote_tasks import TaskQueue
from trading_learning.brain.service import build_handler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    pass


def _post(port, path, body, token="runner-token"):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Bian-Runner-Token": token,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_runner_claim_and_complete_endpoints_update_task(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        queue = TaskQueue(conn)
        task = queue.create_task(
            requester_user_id="owner",
            command_text="/queue-status",
            task_type="local_status",
            payload={},
            risk_level="query",
        )
        handler_cls = build_handler(
            BrainCommandHandler(conn, executor=FakeExecutor()),
            task_queue=queue,
            runner_token="runner-token",
        )
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            claimed = _post(
                server.server_port,
                "/runner/claim",
                {"runner_id": "pc-1", "capabilities": ["local_status"]},
            )
            completed = _post(
                server.server_port,
                "/runner/complete",
                {
                    "runner_id": "pc-1",
                    "task_id": task.external_id,
                    "state": "succeeded",
                    "result_summary": "local runner online",
                    "result_payload": {"ok": True},
                },
            )
        finally:
            server.shutdown()
            thread.join()

        assert claimed["status"] == "claimed"
        assert claimed["task"]["external_id"] == task.external_id
        assert completed["status"] == "ok"
        assert completed["task"]["state"] == "succeeded"


def test_runner_endpoints_require_token(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        queue = TaskQueue(conn)
        handler_cls = build_handler(
            BrainCommandHandler(conn, executor=FakeExecutor()),
            task_queue=queue,
            runner_token="runner-token",
        )
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            try:
                _post(
                    server.server_port,
                    "/runner/claim",
                    {"runner_id": "pc-1", "capabilities": ["local_status"]},
                    token="wrong",
                )
            except urllib.error.HTTPError as exc:
                status = exc.code
                body = json.loads(exc.read().decode("utf-8"))
        finally:
            server.shutdown()
            thread.join()

        assert status == 403
        assert body["status"] == "forbidden"
