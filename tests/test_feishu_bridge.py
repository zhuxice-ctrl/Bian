import hashlib
import json
from http.server import HTTPServer
from threading import Thread

from trading_learning.brain.feishu import FeishuEventAdapter, calculate_lark_signature
from trading_learning.brain.service import build_handler


class FakeCommandHandler:
    def __init__(self):
        self.calls = []

    def handle(self, text, *, user_id):
        self.calls.append((text, user_id))
        return {"status": "ok", "message": "brain response"}


def test_feishu_url_verification_returns_challenge():
    adapter = FeishuEventAdapter(FakeCommandHandler(), verification_token="verify-token")

    response = adapter.handle({"type": "url_verification", "token": "verify-token", "challenge": "abc"})

    assert response["status"] == "verified"
    assert response["challenge"] == "abc"


def test_feishu_url_verification_does_not_require_signature():
    adapter = FeishuEventAdapter(
        FakeCommandHandler(),
        verification_token="verify-token",
        encrypt_key="encrypt-key",
    )

    response = adapter.handle({"type": "url_verification", "token": "verify-token", "challenge": "abc"})

    assert response["status"] == "verified"
    assert response["challenge"] == "abc"


def test_feishu_rejects_invalid_verification_token():
    adapter = FeishuEventAdapter(FakeCommandHandler(), verification_token="verify-token")

    response = adapter.handle({"header": {"token": "wrong"}})

    assert response["status"] == "forbidden"


def test_feishu_text_message_routes_to_brain_with_user_mapping():
    command_handler = FakeCommandHandler()
    adapter = FeishuEventAdapter(
        command_handler,
        verification_token="verify-token",
        user_id_map={"ou_owner": "owner"},
    )

    response = adapter.handle(
        {
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1", "token": "verify-token"},
            "event": {
                "sender": {"sender_id": {"open_id": "ou_owner"}},
                "message": {
                    "chat_id": "oc_chat",
                    "message_type": "text",
                    "content": json.dumps({"text": "/status"}),
                },
            },
        }
    )

    assert response["status"] == "ok"
    assert response["brain"]["status"] == "ok"
    assert response["chat_id"] == "oc_chat"
    assert command_handler.calls == [("/status", "owner")]


def test_feishu_signature_check_uses_raw_body():
    raw_body = json.dumps({"header": {"token": "verify-token"}}).encode("utf-8")
    signature = calculate_lark_signature("1000", "nonce", "encrypt-key", raw_body)

    assert signature == hashlib.sha256(b"1000nonceencrypt-key" + raw_body).hexdigest()


def test_feishu_http_endpoint_handles_event():
    command_handler = FakeCommandHandler()
    adapter = FeishuEventAdapter(command_handler)
    handler_cls = build_handler(command_handler, feishu_adapter=adapter)
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/feishu/events",
            data=json.dumps(
                {
                    "schema": "2.0",
                    "header": {"event_type": "im.message.receive_v1"},
                    "event": {
                        "sender": {"sender_id": {"open_id": "ou_owner"}},
                        "message": {"message_type": "text", "content": json.dumps({"text": "/status"})},
                    },
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join()

    assert body["status"] == "ok"
    assert command_handler.calls == [("/status", "ou_owner")]
