from __future__ import annotations

import sqlite3


VALID_EXPERIMENT_DECISIONS = {"rejected", "needs_more_data", "continue_research", "testnet_candidate", "archived"}


def save_experiment_decision(
    conn: sqlite3.Connection,
    *,
    experiment: str,
    decision: str,
    reason: str = "",
) -> dict[str, str]:
    normalized = decision.strip()
    if normalized not in VALID_EXPERIMENT_DECISIONS:
        raise ValueError(f"invalid decision: {decision}")
    row = conn.execute("select external_id from strategy_experiments where external_id = ?", (experiment,)).fetchone()
    if row is None:
        raise ValueError(f"experiment not found: {experiment}")
    with conn:
        conn.execute(
            """
            insert into experiment_decisions (experiment_external_id, decision, reason)
            values (?, ?, ?)
            on conflict(experiment_external_id) do update set
              decision = excluded.decision,
              reason = excluded.reason,
              updated_at = CURRENT_TIMESTAMP
            """,
            (experiment, normalized, reason),
        )
    return {"experiment_external_id": experiment, "decision": normalized, "reason": reason}


def list_experiment_decisions(conn: sqlite3.Connection, *, limit: int = 20) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        select experiment_external_id, decision, reason, created_at, updated_at
        from experiment_decisions
        order by updated_at desc, id desc
        limit ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "experiment_external_id": row["experiment_external_id"],
            "decision": row["decision"],
            "reason": row["reason"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]
