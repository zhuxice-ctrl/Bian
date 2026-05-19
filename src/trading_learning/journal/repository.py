from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from trading_learning.models import Trade


def save_daily_review(
    conn: sqlite3.Connection,
    external_id: str,
    review_date: str,
    symbols_watched: list[str],
    trade_count: int,
    plan_followed: bool,
    pnl: float,
    mistake_tags: list[str],
    emotion_note: str,
    lesson: str,
) -> None:
    conn.execute(
        """
        insert into daily_reviews (
          external_id, review_date, symbols_watched, trade_count, plan_followed,
          pnl, mistake_tags, emotion_note, lesson
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            external_id,
            review_date,
            json.dumps(symbols_watched, ensure_ascii=False),
            trade_count,
            1 if plan_followed else 0,
            pnl,
            json.dumps(mistake_tags, ensure_ascii=False),
            emotion_note,
            lesson,
        ),
    )
    conn.commit()


def save_trades(
    conn: sqlite3.Connection,
    trades: Iterable[Trade],
    source: str = "backtest",
) -> None:
    conn.executemany(
        """
        insert into trades (
          external_id, symbol, side, quantity, price, fee, timestamp, reason, source
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                trade.external_id,
                trade.symbol,
                trade.side.value,
                trade.quantity,
                trade.price,
                trade.fee,
                trade.timestamp.isoformat(),
                trade.reason,
                source,
            )
            for trade in trades
        ],
    )
    conn.commit()
