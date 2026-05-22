from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4


def build_next_experiment_proposal(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        """
        select external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
        from strategy_experiments
        order by id desc
        limit 1
        """
    ).fetchone()
    if row is None:
        return {
            "external_id": "",
            "source_experiment_external_id": "",
            "hypothesis": {
                "external_id": "",
                "title": "Establish moving-average baseline",
                "statement": "Run the first BTCUSDT 1h moving-average baseline before changing strategy complexity.",
            },
            "suggested_parameters": {
                "short_window": 20,
                "long_window": 60,
                "quote_amount": 100,
            },
            "suggested_command": (
                "/queue-backtest-ma symbol=BTCUSDT interval=1h "
                "csv=data/local/market_data/BTCUSDT/BTCUSDT-1h.csv short=20 long=60"
            ),
            "learning_value": "Create a stable baseline for later comparison.",
            "stop_criteria": ["At least one completed backtest experiment exists."],
            "tasks": ["Run the queued baseline backtest", "Review the report before changing parameters"],
        }

    parameters = json.loads(row["parameters"])
    metrics = json.loads(row["metrics"])
    realized_pnl = float(metrics.get("realized_pnl", 0.0))
    win_rate = float(metrics.get("win_rate", 0.0))
    short_window = int(parameters.get("short_window", parameters.get("short", 20)))
    long_window = int(parameters.get("long_window", parameters.get("long", 60)))
    quote_amount = float(parameters.get("quote_amount", 100))

    if realized_pnl < 0 or win_rate < 0.4:
        next_short = max(short_window + 5, short_window)
        next_long = max(long_window + 15, next_short + 10)
        statement = "Reduce noisy entries by testing slower moving-average windows after weak recent performance."
        learning_value = "Check whether fewer signals improve PnL and win rate."
        stop_criteria = ["realized_pnl improves versus source experiment", "win_rate improves versus source experiment"]
    else:
        next_short = max(2, short_window - 3)
        next_long = max(next_short + 10, long_window - 10)
        statement = "Test a slightly faster variant after profitable baseline performance."
        learning_value = "Check whether faster response keeps risk acceptable."
        stop_criteria = ["realized_pnl does not deteriorate", "trade_count does not grow excessively"]

    suggested_parameters = {
        "short_window": next_short,
        "long_window": next_long,
        "quote_amount": quote_amount,
    }
    return {
        "external_id": "",
        "source_experiment_external_id": row["external_id"],
        "hypothesis": {
            "external_id": "",
            "title": f"Next MA test after {row['external_id']}",
            "statement": statement,
        },
        "suggested_parameters": suggested_parameters,
        "suggested_command": (
            f"/queue-backtest-ma symbol={row['symbol']} interval={row['interval']} "
            f"csv={row['source_csv']} short={next_short} long={next_long} quote_amount={quote_amount:g}"
        ),
        "learning_value": learning_value,
        "stop_criteria": stop_criteria,
        "tasks": [
            "Queue and run the proposed backtest on the local runner",
            "Compare the follow-up experiment with the source experiment",
            "Commit the experiment review if the result teaches a clear lesson",
        ],
    }


def save_experiment_proposal(conn: sqlite3.Connection, proposal: dict[str, Any]) -> dict[str, Any]:
    proposal_id = f"proposal-{uuid4()}"
    hypothesis_id = f"hypothesis-{uuid4()}"
    saved = {
        **proposal,
        "external_id": proposal_id,
        "hypothesis": {
            **proposal["hypothesis"],
            "external_id": hypothesis_id,
        },
    }
    with conn:
        conn.execute(
            """
            insert into strategy_hypotheses (external_id, title, statement, status)
            values (?, ?, ?, 'active')
            """,
            (
                hypothesis_id,
                saved["hypothesis"]["title"],
                saved["hypothesis"]["statement"],
            ),
        )
        conn.execute(
            """
            insert into experiment_proposals (
              external_id, hypothesis_external_id, source_experiment_external_id, content
            ) values (?, ?, ?, ?)
            """,
            (
                proposal_id,
                hypothesis_id,
                saved["source_experiment_external_id"],
                json.dumps(saved, ensure_ascii=False, sort_keys=True),
            ),
        )
    return saved


def evaluate_experiment_proposal(
    conn: sqlite3.Connection,
    *,
    proposal_id: str,
    experiment_id: str,
) -> dict[str, Any]:
    proposal_row = conn.execute(
        "select * from experiment_proposals where external_id = ?",
        (proposal_id,),
    ).fetchone()
    if proposal_row is None:
        raise ValueError(f"proposal not found: {proposal_id}")
    proposal = json.loads(proposal_row["content"])
    source_id = proposal.get("source_experiment_external_id", "")
    followup = _experiment_metrics(conn, experiment_id)
    source = _experiment_metrics(conn, source_id) if source_id else {}
    realized_delta = float(followup.get("realized_pnl", 0.0)) - float(source.get("realized_pnl", 0.0))
    win_rate_delta = float(followup.get("win_rate", 0.0)) - float(source.get("win_rate", 0.0))
    verdict = "improved" if realized_delta > 0 and win_rate_delta >= 0 else "mixed"
    outcome = {
        "proposal_external_id": proposal_id,
        "experiment_external_id": experiment_id,
        "source_experiment_external_id": source_id,
        "verdict": verdict,
        "comparison": {
            "realized_pnl_delta": realized_delta,
            "win_rate_delta": win_rate_delta,
        },
        "next_tasks": [
            "Write or commit the experiment review",
            "Use /coach-next for the next hypothesis after review",
        ],
    }
    with conn:
        conn.execute(
            """
            update experiment_proposals
            set status = 'evaluated',
                outcome = ?,
                updated_at = CURRENT_TIMESTAMP
            where external_id = ?
            """,
            (json.dumps(outcome, ensure_ascii=False, sort_keys=True), proposal_id),
        )
    return outcome


def _experiment_metrics(conn: sqlite3.Connection, experiment_id: str) -> dict[str, Any]:
    if not experiment_id:
        return {}
    row = conn.execute(
        "select metrics from strategy_experiments where external_id = ?",
        (experiment_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"experiment not found: {experiment_id}")
    return json.loads(row["metrics"])
