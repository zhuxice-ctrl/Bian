from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def calculate_lark_signature(timestamp: str, nonce: str, encrypt_key: str, raw_body: bytes) -> str:
    base = timestamp.encode("utf-8") + nonce.encode("utf-8") + encrypt_key.encode("utf-8")
    return hashlib.sha256(base + raw_body).hexdigest()


class FeishuEventAdapter:
    def __init__(
        self,
        command_handler: Any,
        *,
        verification_token: str | None = None,
        encrypt_key: str | None = None,
        user_id_map: dict[str, str] | None = None,
    ) -> None:
        self.command_handler = command_handler
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self.user_id_map = user_id_map or {}

    def handle(
        self,
        payload: dict[str, Any],
        *,
        raw_body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if payload.get("type") == "url_verification":
            if not self._valid_token(payload.get("token")):
                return {"status": "forbidden", "message": "invalid Feishu verification token"}
            return {"status": "verified", "challenge": payload.get("challenge", "")}

        if self.encrypt_key and not self._valid_signature(headers or {}, raw_body):
            return {"status": "forbidden", "message": "invalid Feishu signature"}

        header = payload.get("header", {})
        if not self._valid_token(header.get("token")):
            return {"status": "forbidden", "message": "invalid Feishu verification token"}

        if header.get("event_type") != "im.message.receive_v1":
            return {"status": "ignored", "message": "unsupported Feishu event"}

        event = payload.get("event", {})
        message = event.get("message", {})
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
        return {
            "status": "ok",
            "brain": brain_response,
            "chat_id": message.get("chat_id", ""),
        }

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
