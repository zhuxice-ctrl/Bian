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
            user_prompt=self._build_user_prompt(text, context),
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
            "你是 Bian，一个本地低频加密货币量化交易学习系统的大脑。"
            "你管理一个基于 Carver 框架的 4 信号系统（EWMAC趋势、动量、均值回归、波动率regime），"
            "使用 FDM 合成预测、波动率目标仓位管理，当前正在 paper trading 观察期。\n\n"
            "你的核心命令：\n"
            "- 策略状态 / /paper-status：查看当前仓位和信号\n"
            "- 策略历史 / /paper-history：最近N天的仓位变化\n"
            "- /coach-next：获取下一步学习建议\n"
            "- /learning-next：今天应该学什么\n"
            "- /review-summary：复盘摘要\n"
            "- /knowledge-search 关键词：搜索知识卡\n\n"
            "规则：\n"
            "1. 始终用中文回答，简洁直接\n"
            "2. 绝不执行交易，绝不给出买卖建议\n"
            "3. 可以解释信号含义（如 FAST=-0.04 表示短期趋势微弱看空）\n"
            "4. 用户问操作时，建议具体命令而非自己执行\n"
            "5. 只在有完整命令时返回 suggested_command，不返回不完整的命令前缀\n"
            "6. 返回 JSON，keys: message 和可选的 suggested_command"
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

    @staticmethod
    def _build_user_prompt(text: str, context: dict[str, Any]) -> str:
        parts = [f"用户说：{text}"]
        paper = context.get("paper_trading")
        if paper:
            parts.append(
                f"\n当前策略状态：权益{paper.get('equity', '?')} "
                f"收益率{paper.get('cumulative_return_pct', '?')}% "
                f"今日PnL {paper.get('daily_pnl', '?')}% "
                f"仓位{paper.get('target_position', '?')}"
            )
            signals = paper.get("signals") or {}
            if signals:
                parts.append(
                    f"信号：FAST={signals.get('trend_fast','?')} "
                    f"MOM={signals.get('momentum','?')} "
                    f"MR={signals.get('mean_rev','?')} "
                    f"VOL={signals.get('vol_regime','?')} "
                    f"Combined={signals.get('combined','?')}"
                )
        plan = context.get("plan")
        if plan:
            parts.append(f"今日计划：{plan.get('strategy_goal', '无')}")
        parts.append("\n请用 JSON 回答，格式：{\"message\": \"...\", \"suggested_command\": \"...或空\"}")
        return "\n".join(parts)


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
