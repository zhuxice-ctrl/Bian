import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from trading_learning.ai_assistant.local_codex import LocalCodexClient


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        assert body["model"] == "test-model"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {"choices": [{"message": {"content": "draft summary"}}]}
            ).encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def test_local_codex_client_returns_text():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        client = LocalCodexClient(base_url=base_url, api_key="local-key", model="test-model")
        assert client.chat("system", "user") == "draft summary"
    finally:
        server.shutdown()
        thread.join()
