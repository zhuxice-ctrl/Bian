from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any


class BrainRequestHandler(BaseHTTPRequestHandler):
    command_handler: Any
    feishu_adapter: Any | None = None
    task_queue: Any | None = None
    runner_token: str | None = None

    def do_POST(self) -> None:
        if self.path not in {"/brain/command", "/feishu/events", "/runner/claim", "/runner/complete"}:
            self._write_json({"status": "not_found", "message": "not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            body = json.loads(raw_body.decode("utf-8"))
            if self.path in {"/runner/claim", "/runner/complete"}:
                response, status = self._handle_runner_request(body)
                self._write_json(response, status)
                return
            if self.path == "/feishu/events":
                if self.feishu_adapter is None:
                    self._write_json({"status": "not_configured", "message": "Feishu adapter not configured"}, HTTPStatus.NOT_FOUND)
                    return
                response = self.feishu_adapter.handle(
                    body,
                    raw_body=raw_body,
                    headers=dict(self.headers.items()),
                )
                self._write_json(response, HTTPStatus.OK)
                return
            response = self.command_handler.handle(
                str(body.get("text", "")),
                user_id=str(body.get("user_id", "")),
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._write_json({"status": "invalid", "message": "invalid json"}, HTTPStatus.BAD_REQUEST)
            return

        self._write_json(response, HTTPStatus.OK)

    def _handle_runner_request(self, body: dict[str, Any]) -> tuple[dict[str, Any], HTTPStatus]:
        if self.task_queue is None or not self.runner_token:
            return {"status": "not_configured", "message": "runner queue is not configured"}, HTTPStatus.NOT_FOUND
        if self.headers.get("X-Bian-Runner-Token", "") != self.runner_token:
            return {"status": "forbidden", "message": "runner token is invalid"}, HTTPStatus.FORBIDDEN

        runner_id = str(body.get("runner_id", "")).strip()
        if not runner_id:
            return {"status": "invalid", "message": "runner_id is required"}, HTTPStatus.BAD_REQUEST

        if self.path == "/runner/claim":
            capabilities = tuple(str(item) for item in body.get("capabilities", []) if str(item).strip())
            task = self.task_queue.claim_next(runner_id=runner_id, capabilities=capabilities)
            if task is None:
                return {"status": "empty", "task": None}, HTTPStatus.OK
            return {"status": "claimed", "task": task.to_dict()}, HTTPStatus.OK

        task_id = str(body.get("task_id", "")).strip()
        if not task_id:
            return {"status": "invalid", "message": "task_id is required"}, HTTPStatus.BAD_REQUEST
        task = self.task_queue.complete_task(
            task_id,
            runner_id=runner_id,
            state=str(body.get("state", "")),
            result_summary=str(body.get("result_summary", "")),
            result_payload=body.get("result_payload") if isinstance(body.get("result_payload"), dict) else {},
            error_message=str(body.get("error_message", "")),
        )
        return {"status": "ok", "task": task.to_dict()}, HTTPStatus.OK

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, body: dict[str, Any], status: HTTPStatus) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def build_handler(
    command_handler: Any,
    *,
    feishu_adapter: Any | None = None,
    task_queue: Any | None = None,
    runner_token: str | None = None,
) -> type[BrainRequestHandler]:
    class ConfiguredBrainRequestHandler(BrainRequestHandler):
        pass

    ConfiguredBrainRequestHandler.command_handler = command_handler
    ConfiguredBrainRequestHandler.feishu_adapter = feishu_adapter
    ConfiguredBrainRequestHandler.task_queue = task_queue
    ConfiguredBrainRequestHandler.runner_token = runner_token
    return ConfiguredBrainRequestHandler
