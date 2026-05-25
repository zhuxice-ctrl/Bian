from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_learning.brain.feishu import FeishuBotClient
from trading_learning.config import load_config
from trading_learning.paper_access import format_status_message
from trading_learning.paper_access import load_paper_config
from trading_learning.paper_access import load_status_payload
from trading_learning.paper_trading import daily_runner


def send_paper_summary_if_enabled(
    *,
    state_dir: str | Path = daily_runner.DEFAULT_STATE_DIR,
    messenger_cls: Any = FeishuBotClient,
) -> dict[str, Any]:
    paper_config = load_paper_config(state_dir=state_dir)
    if not bool(paper_config.get("feishu_push_enabled", False)):
        return {"status": "disabled"}
    chat_id = str(paper_config.get("feishu_push_chat_id", "") or "").strip()
    if not chat_id:
        return {"status": "warning", "message": "feishu_push_chat_id is empty"}

    app_config = load_config()
    if not app_config.feishu_app_id or not app_config.feishu_app_secret:
        return {"status": "warning", "message": "FEISHU_APP_ID and FEISHU_APP_SECRET are required"}

    try:
        payload = load_status_payload(state_dir=state_dir)
        if payload.get("status") != "ok":
            return {"status": "warning", "message": str(payload.get("message", "paper status unavailable"))}
        messenger = messenger_cls(app_config.feishu_app_id, app_config.feishu_app_secret)
        result = messenger.send_text(chat_id, format_status_message(payload))
    except Exception as exc:
        return {"status": "warning", "message": str(exc)}
    return {"status": "sent", "message_id": str(result.get("message_id", ""))}
