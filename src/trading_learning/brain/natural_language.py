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
            "Only include suggested_command when it is a complete command with all required arguments; "
            "never return a bare command prefix such as /plan-set or /review-add. "
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


def mock_mode_guidance() -> dict[str, Any]:
    return {
        "status": "chat_unavailable",
        "message": (
            "当前是 mock 模式：本地 Codex/LLM 没有连接，仍可使用确定性指令。"
            "如需自然语言聊天，请在本地环境配置 LOCAL_CODEX_API_KEY。"
            "可用示例：/status，/llm-status，/experiment-summary limit=5，"
            "/learning-next，/review-summary limit=5。"
        ),
        "requires_confirmation": False,
    }
