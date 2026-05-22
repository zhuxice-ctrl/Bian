from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_RESEARCH_DECISIONS = {"kept", "rejected", "inconclusive", "risk_reduction_kept"}


@dataclass(frozen=True)
class HypothesisCard:
    hypothesis_id: str
    title: str
    created_at: datetime
    description: str
    parent_iteration: str
    change_summary: str
    predicted: dict[str, Any]
    decision_rule: str
    ran_at: datetime | None = None
    actual: dict[str, Any] | None = None
    decision: str | None = None
    reason: str | None = None
    hindsight_notes: str | None = None
    code_commit: str | None = None
    backtest_run_id: str | None = None


class HypothesisLog:
    def __init__(self, conn: sqlite3.Connection, *, cards_dir: Path | str = "docs/research/hypothesis-log"):
        self.conn = conn
        self.cards_dir = Path(cards_dir)

    def create(
        self,
        *,
        title: str,
        description: str,
        parent_iteration: str,
        change_summary: str,
        predicted: dict[str, Any],
        decision_rule: str,
    ) -> HypothesisCard:
        if not predicted:
            raise ValueError("predicted metrics are required")
        hypothesis_id = self._next_id()
        created_at = datetime.now(timezone.utc)
        card = HypothesisCard(
            hypothesis_id=hypothesis_id,
            title=title,
            created_at=created_at,
            description=description,
            parent_iteration=parent_iteration,
            change_summary=change_summary,
            predicted=dict(predicted),
            decision_rule=decision_rule,
        )
        with self.conn:
            self.conn.execute(
                """
                insert into hypothesis_log (
                  hypothesis_id, title, created_at, description, parent_iteration,
                  change_summary, predicted, decision_rule
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.hypothesis_id,
                    card.title,
                    card.created_at.isoformat(),
                    card.description,
                    card.parent_iteration,
                    card.change_summary,
                    json.dumps(card.predicted, ensure_ascii=False, sort_keys=True),
                    card.decision_rule,
                ),
            )
        self._write_markdown(card)
        return card

    def list(self) -> list[HypothesisCard]:
        rows = self.conn.execute("select * from hypothesis_log order by hypothesis_id").fetchall()
        return [self._card_from_row(row) for row in rows]

    def get(self, hypothesis_id: str) -> HypothesisCard:
        row = self.conn.execute("select * from hypothesis_log where hypothesis_id = ?", (hypothesis_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown hypothesis: {hypothesis_id}")
        return self._card_from_row(row)

    def resolve(
        self,
        hypothesis_id: str,
        *,
        actual: dict[str, Any],
        decision: str,
        reason: str,
        hindsight_notes: str = "",
        code_commit: str = "",
        backtest_run_id: str = "",
    ) -> HypothesisCard:
        if decision not in ALLOWED_RESEARCH_DECISIONS:
            raise ValueError(f"decision must be one of {sorted(ALLOWED_RESEARCH_DECISIONS)}")
        if not actual:
            raise ValueError("actual metrics are required")
        if not reason.strip():
            raise ValueError("reason is required")
        self.get(hypothesis_id)
        ran_at = datetime.now(timezone.utc)
        with self.conn:
            self.conn.execute(
                """
                update hypothesis_log
                set ran_at = ?, actual = ?, decision = ?, reason = ?, hindsight_notes = ?,
                    code_commit = ?, backtest_run_id = ?, updated_at = CURRENT_TIMESTAMP
                where hypothesis_id = ?
                """,
                (
                    ran_at.isoformat(),
                    json.dumps(actual, ensure_ascii=False, sort_keys=True),
                    decision,
                    reason.strip(),
                    hindsight_notes,
                    code_commit,
                    backtest_run_id,
                    hypothesis_id,
                ),
            )
        card = self.get(hypothesis_id)
        self._write_markdown(card)
        return card

    def tree(self) -> list[dict[str, str]]:
        return [
            {
                "hypothesis_id": card.hypothesis_id,
                "parent_iteration": card.parent_iteration,
                "title": card.title,
                "decision": card.decision or "",
            }
            for card in self.list()
        ]

    def _next_id(self) -> str:
        row = self.conn.execute("select hypothesis_id from hypothesis_log order by id desc limit 1").fetchone()
        if row is None:
            return "H-001"
        match = re.fullmatch(r"H-(\d+)", row["hypothesis_id"])
        next_number = int(match.group(1)) + 1 if match else 1
        return f"H-{next_number:03d}"

    def _write_markdown(self, card: HypothesisCard) -> None:
        self.cards_dir.mkdir(parents=True, exist_ok=True)
        path = self.cards_dir / f"{card.hypothesis_id}-{_slug(card.title)}.md"
        path.write_text(_markdown(card), encoding="utf-8")

    @staticmethod
    def _card_from_row(row: sqlite3.Row) -> HypothesisCard:
        return HypothesisCard(
            hypothesis_id=row["hypothesis_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            description=row["description"],
            parent_iteration=row["parent_iteration"],
            change_summary=row["change_summary"],
            predicted=json.loads(row["predicted"]),
            decision_rule=row["decision_rule"],
            ran_at=datetime.fromisoformat(row["ran_at"]) if row["ran_at"] else None,
            actual=json.loads(row["actual"]) if row["actual"] else None,
            decision=row["decision"] or None,
            reason=row["reason"] or None,
            hindsight_notes=row["hindsight_notes"] or None,
            code_commit=row["code_commit"] or None,
            backtest_run_id=row["backtest_run_id"] or None,
        )


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "hypothesis"


def _markdown(card: HypothesisCard) -> str:
    actual = card.actual or {}
    decision = card.decision or "unresolved"
    reason = card.reason or "unresolved"
    return "\n".join(
        [
            f"# {card.hypothesis_id} {card.title}",
            "",
            f"- Created: {card.created_at.isoformat()}",
            f"- Parent: {card.parent_iteration}",
            f"- Change: {card.change_summary}",
            f"- Decision: {decision}",
            f"- Reason: {reason}",
            "",
            "## Description",
            card.description,
            "",
            "## Predicted",
            "```json",
            json.dumps(card.predicted, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Decision Rule",
            card.decision_rule,
            "",
            "## Actual",
            "```json",
            json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Run Metadata",
            f"- Ran at: {card.ran_at.isoformat() if card.ran_at else ''}",
            f"- Commit: {card.code_commit or ''}",
            f"- Backtest run: {card.backtest_run_id or ''}",
            "",
            "## Hindsight Notes",
            card.hindsight_notes or "",
            "",
        ]
    )
