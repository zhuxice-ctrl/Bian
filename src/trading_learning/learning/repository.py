from __future__ import annotations

import sqlite3


def save_knowledge_card(
    conn: sqlite3.Connection,
    external_id: str,
    title: str,
    category: str,
    content: str,
) -> None:
    conn.execute(
        """
        insert into knowledge_cards (external_id, title, category, content)
        values (?, ?, ?, ?)
        """,
        (external_id, title, category, content),
    )
    conn.commit()


def save_strategy_hypothesis(
    conn: sqlite3.Connection,
    external_id: str,
    title: str,
    statement: str,
) -> None:
    conn.execute(
        """
        insert into strategy_hypotheses (external_id, title, statement)
        values (?, ?, ?)
        """,
        (external_id, title, statement),
    )
    conn.commit()
