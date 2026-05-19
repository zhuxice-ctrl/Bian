import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from trading_learning.ai_assistant.local_codex import LocalCodexClient
from trading_learning.ai_assistant.tasks import create_daily_review_draft
from trading_learning.storage.db import connect, initialize_schema


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.server.requests.append(
            {
                "method": self.command,
                "path": self.path,
                "authorization": self.headers["Authorization"],
                "content_type": self.headers["Content-Type"],
                "body": body,
            }
        )
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
    server.requests = []
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        client = LocalCodexClient(base_url=base_url, api_key="local-key", model="test-model")
        assert client.chat("system", "user") == "draft summary"
    finally:
        server.shutdown()
        thread.join()

    assert server.requests == [
        {
            "method": "POST",
            "path": "/v1/chat/completions",
            "authorization": "Bearer local-key",
            "content_type": "application/json",
            "body": {
                "model": "test-model",
                "messages": [
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": "user"},
                ],
                "max_tokens": 1200,
            },
        }
    ]


class FakeClient:
    def __init__(self):
        self.calls = []

    def chat(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return "draft summary"


def test_create_daily_review_draft_persists_draft(tmp_path):
    conn = connect(tmp_path / "drafts.sqlite")
    initialize_schema(conn)
    client = FakeClient()

    external_id = create_daily_review_draft(
        conn,
        client,
        source_external_id="review-2026-05-01",
        review_text="review body",
    )

    assert external_id.startswith("ai-draft-")
    row = conn.execute(
        """
        select task_type, source_external_id, content, status
        from ai_drafts
        where external_id = ?
        """,
        (external_id,),
    ).fetchone()
    assert dict(row) == {
        "task_type": "daily_review_summary",
        "source_external_id": "review-2026-05-01",
        "content": "draft summary",
        "status": "draft",
    }
    assert len(client.calls) == 1
    system_prompt, user_prompt = client.calls[0]
    assert "never give buy or sell signals" in system_prompt
    assert user_prompt == "review body"
