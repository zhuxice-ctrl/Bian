from __future__ import annotations

import sqlite3
from uuid import uuid4

from trading_learning.ai_assistant.local_codex import LocalCodexClient


REVIEW_SYSTEM_PROMPT = (
    "You are a trading learning assistant. Summarize reviews, ask learning questions, "
    "and never give buy or sell signals. Do not suggest changing live strategy parameters."
)


def create_daily_review_draft(
    conn: sqlite3.Connection,
    client: LocalCodexClient,
    source_external_id: str,
    review_text: str,
) -> str:
    content = client.chat(REVIEW_SYSTEM_PROMPT, review_text)
    external_id = f"ai-draft-{uuid4()}"
    conn.execute(
        """
        insert into ai_drafts (external_id, task_type, source_external_id, content, status)
        values (?, ?, ?, ?, 'draft')
        """,
        (external_id, "daily_review_summary", source_external_id, content),
    )
    conn.commit()
    return external_id
