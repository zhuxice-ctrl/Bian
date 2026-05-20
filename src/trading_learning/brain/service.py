from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any


class BrainRequestHandler(BaseHTTPRequestHandler):
    command_handler: Any
    feishu_adapter: Any | None = None

    def do_POST(self) -> None:
        if self.path not in {"/brain/command", "/feishu/events"}:
            self._write_json({"status": "not_found", "message": "not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            body = json.loads(raw_body.decode("utf-8"))
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

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, body: dict[str, Any], status: HTTPStatus) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def build_handler(command_handler: Any, *, feishu_adapter: Any | None = None) -> type[BrainRequestHandler]:
    class ConfiguredBrainRequestHandler(BrainRequestHandler):
        pass

    ConfiguredBrainRequestHandler.command_handler = command_handler
    ConfiguredBrainRequestHandler.feishu_adapter = feishu_adapter
    return ConfiguredBrainRequestHandler
