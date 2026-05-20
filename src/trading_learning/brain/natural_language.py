from __future__ import annotations

import json
from typing import Any

from trading_learning.ai_assistant.local_codex import LocalCodexClient


class LocalCodexBrainAssistant:
    def __init__(self, client: LocalCodexClient) -> None:
        self.client = client

    def reply(self, text: str, *, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        content = self.client.chat(
            system_prompt=self._system_prompt(),
            user_prompt=json.dumps(
                {
                    "user_id": user_id,
                    "message": text,
                    "context": context,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        parsed = self._parse_response(content)
        return {
            "status": "chat",
            "message": parsed["message"],
            "suggested_command": parsed.get("suggested_command", ""),
            "requires_confirmation": False,
        }

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are the local Brain for a low-frequency crypto trading learning system. "
            "Answer in Chinese by default. You may explain available commands and help the user reflect. "
            "Never execute trades, never claim an order was placed, and never give direct buy/sell signals. "
            "If the user asks for an operation, suggest one safe existing command instead of executing it. "
            "High-risk actions must still go through plan, checklist, and confirmation code. "
            "Return JSON only with keys: message and optional suggested_command."
        )

    @staticmethod
    def _parse_response(content: str) -> dict[str, str]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {"message": content}
        if isinstance(data, dict) and isinstance(data.get("message"), str):
            result = {"message": data["message"]}
            if isinstance(data.get("suggested_command"), str):
                result["suggested_command"] = data["suggested_command"]
            return result
        return {"message": content}
