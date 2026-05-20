from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any


class BrainRequestHandler(BaseHTTPRequestHandler):
    command_handler: Any

    def do_POST(self) -> None:
        if self.path != "/brain/command":
            self._write_json({"status": "not_found", "message": "not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
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


def build_handler(command_handler: Any) -> type[BrainRequestHandler]:
    class ConfiguredBrainRequestHandler(BrainRequestHandler):
        pass

    ConfiguredBrainRequestHandler.command_handler = command_handler
    return ConfiguredBrainRequestHandler
