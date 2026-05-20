import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from trading_learning.ai_assistant.local_codex import LocalCodexClient
from trading_learning.brain.natural_language import LocalCodexBrainAssistant
from trading_learning.cli import build_natural_language_assistant
from trading_learning.config import AppConfig


class ChatHandler(BaseHTTPRequestHandler):
    captured = {}

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        ChatHandler.captured = body
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "message": "你好，我在。你可以先用 /status 看状态。",
                                        "suggested_command": "/status",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def test_local_codex_brain_assistant_returns_chat_response():
    server = HTTPServer(("127.0.0.1", 0), ChatHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = LocalCodexClient(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            api_key="local-key",
            model="test-model",
        )
        assistant = LocalCodexBrainAssistant(client)

        response = assistant.reply("你好", user_id="owner", context={"plan": None})
    finally:
        server.shutdown()
        thread.join()

    assert response == {
        "status": "chat",
        "message": "你好，我在。你可以先用 /status 看状态。",
        "suggested_command": "/status",
        "requires_confirmation": False,
    }
    system_prompt = ChatHandler.captured["messages"][0]["content"].lower()
    assert "never execute trades" in system_prompt
    assert "complete command" in system_prompt
    assert ChatHandler.captured["messages"][1]["content"]


def test_local_codex_brain_assistant_handles_plain_text_response():
    class PlainTextHandler(ChatHandler):
        def do_POST(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"choices": [{"message": {"content": "你好，我在。"}}]}).encode("utf-8")
            )

    server = HTTPServer(("127.0.0.1", 0), PlainTextHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = LocalCodexClient(
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            api_key="local-key",
            model="test-model",
        )
        assistant = LocalCodexBrainAssistant(client)

        response = assistant.reply("你好", user_id="owner", context={})
    finally:
        server.shutdown()
        thread.join()

    assert response["status"] == "chat"
    assert response["message"] == "你好，我在。"
    assert response["requires_confirmation"] is False


def test_build_natural_language_assistant_requires_local_key(tmp_path):
    config = AppConfig(
        db_path=tmp_path / "test.sqlite3",
        local_codex_base_url="http://127.0.0.1:61771/v1",
        local_codex_model="test-model",
        local_codex_api_key=None,
        binance_testnet_base_url="https://testnet.binance.vision",
        binance_testnet_api_key=None,
        binance_testnet_api_secret=None,
        feishu_verification_token=None,
        feishu_encrypt_key=None,
        feishu_user_map="",
    )

    assert build_natural_language_assistant(config) is None


def test_build_natural_language_assistant_rejects_non_loopback_base_url(tmp_path):
    config = AppConfig(
        db_path=tmp_path / "test.sqlite3",
        local_codex_base_url="https://api.example.com/v1",
        local_codex_model="test-model",
        local_codex_api_key="local-key",
        binance_testnet_base_url="https://testnet.binance.vision",
        binance_testnet_api_key=None,
        binance_testnet_api_secret=None,
        feishu_verification_token=None,
        feishu_encrypt_key=None,
        feishu_user_map="",
    )

    assert build_natural_language_assistant(config) is None
