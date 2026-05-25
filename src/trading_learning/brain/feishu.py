from __future__ import annotations

import hashlib
import hmac
import json
import urllib.request
from base64 import b64decode
from typing import Any
from urllib.parse import urlencode

from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import modes


def calculate_lark_signature(timestamp: str, nonce: str, encrypt_key: str, raw_body: bytes) -> str:
    base = timestamp.encode("utf-8") + nonce.encode("utf-8") + encrypt_key.encode("utf-8")
    return hashlib.sha256(base + raw_body).hexdigest()


class FeishuBotClient:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        base_url: str = "https://open.feishu.cn/open-apis",
        opener: Any = urllib.request.urlopen,
        timeout: int = 10,
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/")
        self.opener = opener
        self.timeout = timeout
        self._tenant_access_token: str | None = None

    def send_text(self, chat_id: str, text: str) -> dict[str, Any]:
        token = self._tenant_token()
        query = urlencode({"receive_id_type": "chat_id"})
        response = self._post_json(
            f"{self.base_url}/im/v1/messages?{query}",
            {
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.get("data", {})
        return {"message_id": data.get("message_id", "")}

    def _tenant_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token
        response = self._post_json(
            f"{self.base_url}/auth/v3/tenant_access_token/internal",
            {"app_id": self.app_id, "app_secret": self.app_secret},
        )
        token = str(response.get("tenant_access_token", ""))
        if not token:
            raise RuntimeError("Feishu tenant_access_token missing from response")
        self._tenant_access_token = token
        return token

    def _post_json(self, url: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8", **(headers or {})},
            method="POST",
        )
        with self.opener(request, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        if int(result.get("code", 0) or 0) != 0:
            raise RuntimeError(str(result.get("msg", "Feishu API request failed")))
        return result


class FeishuEventAdapter:
    def __init__(
        self,
        command_handler: Any,
        *,
        verification_token: str | None = None,
        encrypt_key: str | None = None,
        user_id_map: dict[str, str] | None = None,
        messenger: Any | None = None,
        dedup_max_size: int = 500,
    ) -> None:
        self.command_handler = command_handler
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self.user_id_map = user_id_map or {}
        self.messenger = messenger
        self._seen_message_ids: set[str] = set()
        self._dedup_max_size = dedup_max_size

    def handle(
        self,
        payload: dict[str, Any],
        *,
        raw_body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if "encrypt" in payload:
            if not self.encrypt_key:
                return {"status": "forbidden", "message": "Feishu encrypt key is required"}
            try:
                payload = self._decrypt_payload(str(payload.get("encrypt", "")))
            except (ValueError, json.JSONDecodeError):
                return {"status": "invalid", "message": "invalid encrypted Feishu payload"}

        if payload.get("type") == "url_verification":
            if not self._valid_token(payload.get("token")):
                return {"status": "forbidden", "message": "invalid Feishu verification token"}
            return {"challenge": payload.get("challenge", "")}

        header = payload.get("header", {})
        if header.get("event_type") == "url_verification":
            if not self._valid_token(header.get("token")):
                return {"status": "forbidden", "message": "invalid Feishu verification token"}
            event = payload.get("event", {})
            return {"challenge": event.get("challenge", payload.get("challenge", ""))}

        if self.encrypt_key and not self._valid_signature(headers or {}, raw_body):
            return {"status": "forbidden", "message": "invalid Feishu signature"}

        if not self._valid_token(header.get("token")):
            return {"status": "forbidden", "message": "invalid Feishu verification token"}

        if header.get("event_type") != "im.message.receive_v1":
            return {"status": "ignored", "message": "unsupported Feishu event"}

        event = payload.get("event", {})
        message = event.get("message", {})
        message_id = message.get("message_id", "")
        if message_id:
            if message_id in self._seen_message_ids:
                return {"status": "dedup", "message": "duplicate Feishu event ignored"}
            self._seen_message_ids.add(message_id)
            if len(self._seen_message_ids) > self._dedup_max_size:
                self._seen_message_ids = set(list(self._seen_message_ids)[-self._dedup_max_size // 2 :])
        if message.get("message_type") != "text":
            return {"status": "ignored", "message": "unsupported Feishu message type"}

        text = self._extract_text(message.get("content", ""))
        sender_open_id = (
            event.get("sender", {})
            .get("sender_id", {})
            .get("open_id", "")
        )
        user_id = self.user_id_map.get(sender_open_id, sender_open_id)
        brain_response = self.command_handler.handle(text, user_id=user_id)
        response = {
            "status": "ok",
            "brain": brain_response,
            "chat_id": message.get("chat_id", ""),
        }
        chat_id = response["chat_id"]
        if self.messenger is not None and chat_id:
            try:
                response["reply"] = self.messenger.send_text(chat_id, self._format_brain_reply(brain_response))
            except Exception as exc:  # Keep Feishu event acknowledgement independent from reply delivery.
                response["reply_error"] = str(exc)
        return response

    @staticmethod
    def _format_brain_reply(brain_response: dict[str, Any]) -> str:
        message = str(brain_response.get("message", "") or "")
        if message:
            return f"Brain：{message}"
        return f"Brain：{brain_response.get('status', 'ok')}"

    def _valid_token(self, token: Any) -> bool:
        if not self.verification_token:
            return True
        return hmac.compare_digest(str(token), self.verification_token)

    def _valid_signature(self, headers: dict[str, str], raw_body: bytes) -> bool:
        timestamp = self._header_value(headers, "X-Lark-Request-Timestamp")
        nonce = self._header_value(headers, "X-Lark-Request-Nonce")
        signature = self._header_value(headers, "X-Lark-Signature")
        if not timestamp or not nonce or not signature:
            return False
        expected = calculate_lark_signature(timestamp, nonce, self.encrypt_key or "", raw_body)
        return hmac.compare_digest(signature, expected)

    def _decrypt_payload(self, encrypted_payload: str) -> dict[str, Any]:
        encrypted = b64decode(encrypted_payload)
        if len(encrypted) <= 16:
            raise ValueError("encrypted Feishu payload is too short")
        key = hashlib.sha256((self.encrypt_key or "").encode("utf-8")).digest()
        iv = encrypted[:16]
        ciphertext = encrypted[16:]
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        padding_size = padded[-1]
        if padding_size < 1 or padding_size > 16:
            raise ValueError("invalid Feishu payload padding")
        plaintext = padded[:-padding_size]
        return json.loads(plaintext.decode("utf-8"))

    @staticmethod
    def _extract_text(content: str) -> str:
        try:
            body = json.loads(content)
        except json.JSONDecodeError:
            return content
        return str(body.get("text", ""))

    @staticmethod
    def _header_value(headers: dict[str, str], name: str) -> str:
        for key, value in headers.items():
            if key.lower() == name.lower():
                return value
        return ""
