from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Any


HIGH_RISK_TAGS = {"negative_pnl", "drawdown"}
MEDIUM_RISK_TAGS = {"low_win_rate", "losing_trades"}


def build_failed_experiment_learning(conn: sqlite3.Connection, experiment_external_id: str) -> dict[str, Any]:
    experiment = conn.execute(
        """
        select external_id, strategy_name, symbol, interval, metrics
        from strategy_experiments
        where external_id = ?
        """,
        (experiment_external_id,),
    ).fetchone()
    if experiment is None:
        return {"status": "not_found", "message": f"experiment not found: {experiment_external_id}"}

    draft = _experiment_review_draft(conn, experiment_external_id)
    risk_flags = _risk_flags_from_experiment(experiment, draft)
    if not risk_flags:
        return {
            "status": "ok",
            "experiment_external_id": experiment_external_id,
            "tasks": [],
            "knowledge_cards": [],
        }

    tasks = _learning_tasks(experiment, draft, risk_flags)
    card_ids: list[str] = []
    for flag in sorted(risk_flags, key=lambda item: item["code"]):
        code = str(flag["code"])
        external_id = f"knowledge-mistake-{experiment_external_id}-{code}"
        title = f"{experiment['symbol']} {experiment['interval']} {code}"
        content = _mistake_card_content(experiment, flag)
        conn.execute(
            """
            insert into knowledge_cards (external_id, title, category, content, source)
            values (?, ?, 'mistake_pattern', ?, 'failed_experiment')
            on conflict(external_id) do update set
              title = excluded.title,
              category = excluded.category,
              content = excluded.content,
              source = excluded.source,
              updated_at = CURRENT_TIMESTAMP
            """,
            (external_id, title, content),
        )
        for tag in (code, experiment["strategy_name"], experiment["symbol"]):
            conn.execute(
                """
                insert or ignore into knowledge_card_tags (card_external_id, tag)
                values (?, ?)
                """,
                (external_id, str(tag)),
            )
        card_ids.append(external_id)
    conn.commit()

    return {
        "status": "saved",
        "experiment_external_id": experiment_external_id,
        "tasks": tasks,
        "knowledge_cards": card_ids,
    }


def build_review_queue(
    conn: sqlite3.Connection,
    *,
    today: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    today_date = date.fromisoformat(today) if today else date.today()
    rows = conn.execute(
        """
        select external_id, title, category, content, source, updated_at, created_at
        from knowledge_cards
        where status = 'active'
        """
    ).fetchall()
    queue: list[dict[str, Any]] = []
    for row in rows:
        tags = _tags_for_card(conn, row["external_id"])
        updated = _parse_sqlite_date(row["updated_at"] or row["created_at"])
        age_days = max(0, (today_date - updated).days)
        importance = _importance(row, tags, age_days)
        queue.append(
            {
                "card_external_id": row["external_id"],
                "title": row["title"],
                "category": row["category"],
                "source": row["source"],
                "tags": tags,
                "updated_at": row["updated_at"],
                "importance": importance,
                "reason": _queue_reason(row, tags),
            }
        )
    queue.sort(key=lambda item: (-int(item["importance"]), str(item["updated_at"])), reverse=False)
    return queue[: max(0, limit)]


def _experiment_review_draft(conn: sqlite3.Connection, experiment_external_id: str) -> dict[str, Any]:
    row = conn.execute(
        "select content from experiment_review_drafts where experiment_external_id = ?",
        (experiment_external_id,),
    ).fetchone()
    if row is None:
        return {}
    return _json(row["content"], {})


def _risk_flags_from_experiment(experiment: sqlite3.Row, draft: dict[str, Any]) -> list[dict[str, Any]]:
    flags = [
        {"code": str(flag.get("code", "")), "severity": str(flag.get("severity", "medium")), "message": str(flag.get("message", ""))}
        for flag in draft.get("risk_flags", [])
        if isinstance(flag, dict) and flag.get("code")
    ]
    metrics = _json(experiment["metrics"], {})
    if float(metrics.get("realized_pnl", 0.0) or 0.0) < 0 and not _has_flag(flags, "negative_pnl"):
        flags.append({"code": "negative_pnl", "severity": "high", "message": "Experiment ended with negative realized PnL."})
    if float(metrics.get("win_rate", 1.0) or 0.0) < 0.5 and not _has_flag(flags, "low_win_rate"):
        flags.append({"code": "low_win_rate", "severity": "medium", "message": "Experiment win rate is below 50%."})
    return flags


def _learning_tasks(
    experiment: sqlite3.Row,
    draft: dict[str, Any],
    risk_flags: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tasks = [
        str(task)
        for task in draft.get("learning_tasks", [])
        if str(task).strip()
    ]
    if not tasks:
        tasks = [f"Replay {experiment['symbol']} {experiment['interval']} {experiment['strategy_name']} losing conditions."]
    return [
        {
            "title": task,
            "experiment_external_id": experiment["external_id"],
            "priority": "high" if any(flag["code"] in HIGH_RISK_TAGS for flag in risk_flags) else "medium",
        }
        for task in tasks
    ]


def _mistake_card_content(experiment: sqlite3.Row, flag: dict[str, Any]) -> str:
    return (
        f"Experiment {experiment['external_id']} ({experiment['strategy_name']} "
        f"{experiment['symbol']} {experiment['interval']}) triggered {flag['code']}. "
        f"{flag.get('message', '')} Review this before changing parameters or promoting the strategy."
    )


def _importance(row: sqlite3.Row, tags: list[str], age_days: int) -> int:
    score = 30
    if row["category"] == "mistake_pattern":
        score += 25
    if row["source"] in {"failed_experiment", "experiment_review"}:
        score += 15
    if any(tag in HIGH_RISK_TAGS for tag in tags):
        score += 30
    elif any(tag in MEDIUM_RISK_TAGS for tag in tags):
        score += 15
    score += max(0, 14 - min(age_days, 14))
    return score


def _queue_reason(row: sqlite3.Row, tags: list[str]) -> str:
    if row["category"] == "mistake_pattern" and any(tag in HIGH_RISK_TAGS for tag in tags):
        return "high-risk mistake pattern"
    if row["category"] == "mistake_pattern":
        return "mistake pattern"
    return "general review"


def _tags_for_card(conn: sqlite3.Connection, external_id: str) -> list[str]:
    rows = conn.execute(
        "select tag from knowledge_card_tags where card_external_id = ? order by tag",
        (external_id,),
    ).fetchall()
    return [row["tag"] for row in rows]


def _parse_sqlite_date(value: str) -> date:
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return date.fromisoformat(value[:10])


def _json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _has_flag(flags: list[dict[str, Any]], code: str) -> bool:
    return any(flag.get("code") == code for flag in flags)
