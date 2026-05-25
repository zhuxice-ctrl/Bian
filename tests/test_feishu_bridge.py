import hashlib
import json
from base64 import b64encode
from http.server import HTTPServer
from threading import Thread

from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import modes

from trading_learning.brain.feishu import FeishuBotClient, FeishuEventAdapter, calculate_lark_signature
from trading_learning.brain.service import build_handler


class FakeCommandHandler:
    def __init__(self):
        self.calls = []

    def handle(self, text, *, user_id):
        self.calls.append((text, user_id))
        return {"status": "ok", "message": "brain response"}


class FakeFeishuMessenger:
    def __init__(self):
        self.messages = []

    def send_text(self, chat_id, text):
        self.messages.append((chat_id, text))
        return {"message_id": "om_fake"}


class FailingFeishuMessenger:
    def send_text(self, chat_id, text):
        raise RuntimeError("Feishu API request failed")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def encrypt_feishu_payload(payload, encrypt_key="encrypt-key"):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    padding_size = 16 - (len(body) % 16)
    padded = body + bytes([padding_size]) * padding_size
    iv = b"1234567890abcdef"
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    encrypted = iv + encryptor.update(padded) + encryptor.finalize()
    return b64encode(encrypted).decode("ascii")


def test_feishu_url_verification_returns_challenge():
    adapter = FeishuEventAdapter(FakeCommandHandler(), verification_token="verify-token")

    response = adapter.handle({"type": "url_verification", "token": "verify-token", "challenge": "abc"})

    assert response == {"challenge": "abc"}


def test_feishu_url_verification_does_not_require_signature():
    adapter = FeishuEventAdapter(
        FakeCommandHandler(),
        verification_token="verify-token",
        encrypt_key="encrypt-key",
    )

    response = adapter.handle({"type": "url_verification", "token": "verify-token", "challenge": "abc"})

    assert response == {"challenge": "abc"}


def test_feishu_v2_url_verification_returns_event_challenge():
    adapter = FeishuEventAdapter(FakeCommandHandler(), verification_token="verify-token")

    response = adapter.handle(
        {
            "schema": "2.0",
            "header": {
                "event_type": "url_verification",
                "token": "verify-token",
            },
            "event": {
                "challenge": "abc-v2",
            },
        }
    )

    assert response == {"challenge": "abc-v2"}


def test_feishu_encrypted_url_verification_returns_challenge():
    adapter = FeishuEventAdapter(
        FakeCommandHandler(),
        verification_token="verify-token",
        encrypt_key="encrypt-key",
    )

    encrypted = encrypt_feishu_payload(
        {
            "type": "url_verification",
            "token": "verify-token",
            "challenge": "abc-encrypted",
        }
    )

    response = adapter.handle({"encrypt": encrypted})

    assert response == {"challenge": "abc-encrypted"}


def test_feishu_encrypted_v2_url_verification_returns_event_challenge():
    adapter = FeishuEventAdapter(
        FakeCommandHandler(),
        verification_token="verify-token",
        encrypt_key="encrypt-key",
    )

    encrypted = encrypt_feishu_payload(
        {
            "schema": "2.0",
            "header": {
                "event_type": "url_verification",
                "token": "verify-token",
            },
            "event": {
                "challenge": "abc-encrypted-v2",
            },
        }
    )

    response = adapter.handle({"encrypt": encrypted})

    assert response == {"challenge": "abc-encrypted-v2"}


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


def test_feishu_text_message_sends_concise_reply_to_chat():
    command_handler = FakeCommandHandler()
    messenger = FakeFeishuMessenger()
    adapter = FeishuEventAdapter(
        command_handler,
        verification_token="verify-token",
        user_id_map={"ou_owner": "owner"},
        messenger=messenger,
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
    assert response["reply"]["message_id"] == "om_fake"
    assert messenger.messages == [("oc_chat", "Brain：brain response")]


def test_feishu_duplicate_message_id_is_acknowledged_without_second_reply():
    command_handler = FakeCommandHandler()
    messenger = FakeFeishuMessenger()
    adapter = FeishuEventAdapter(
        command_handler,
        verification_token="verify-token",
        user_id_map={"ou_owner": "owner"},
        messenger=messenger,
    )
    payload = {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1", "token": "verify-token"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_owner"}},
            "message": {
                "message_id": "om_message_1",
                "chat_id": "oc_chat",
                "message_type": "text",
                "content": json.dumps({"text": "你好"}),
            },
        },
    }

    first = adapter.handle(payload)
    second = adapter.handle(payload)

    assert first["status"] == "ok"
    assert second == {"status": "dedup", "message": "duplicate Feishu event ignored"}
    assert command_handler.calls == [("你好", "owner")]
    assert messenger.messages == [("oc_chat", "Brain：brain response")]


def test_feishu_text_message_keeps_event_ack_when_reply_fails():
    command_handler = FakeCommandHandler()
    adapter = FeishuEventAdapter(
        command_handler,
        verification_token="verify-token",
        user_id_map={"ou_owner": "owner"},
        messenger=FailingFeishuMessenger(),
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
    assert response["reply_error"] == "Feishu API request failed"
    assert command_handler.calls == [("/status", "owner")]


def test_feishu_bot_client_gets_tenant_token_and_sends_text_message():
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "headers": dict(request.header_items()),
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        if request.full_url.endswith("/auth/v3/tenant_access_token/internal"):
            return FakeResponse({"code": 0, "tenant_access_token": "tenant-token"})
        return FakeResponse({"code": 0, "data": {"message_id": "om_123"}})

    client = FeishuBotClient("app-id", "app-secret", opener=fake_urlopen, base_url="https://open.feishu.test/open-apis")

    response = client.send_text("oc_chat", "Brain：ok")

    assert response == {"message_id": "om_123"}
    assert requests[0]["url"] == "https://open.feishu.test/open-apis/auth/v3/tenant_access_token/internal"
    assert requests[0]["body"] == {"app_id": "app-id", "app_secret": "app-secret"}
    assert requests[1]["url"] == "https://open.feishu.test/open-apis/im/v1/messages?receive_id_type=chat_id"
    assert requests[1]["headers"]["Authorization"] == "Bearer tenant-token"
    assert requests[1]["body"] == {
        "receive_id": "oc_chat",
        "msg_type": "text",
        "content": json.dumps({"text": "Brain：ok"}, ensure_ascii=False),
    }


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
