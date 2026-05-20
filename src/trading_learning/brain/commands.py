from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from trading_learning.journal.repository import save_daily_review
from trading_learning.learning.repository import save_knowledge_card


@dataclass(frozen=True)
class PendingConfirmation:
    code: str
    user_id: str
    command_text: str
    payload: dict[str, Any]


class BrainCommandHandler:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        executor: Any,
        allowed_user_ids: tuple[str, ...] | None = None,
        confirmation_code: Callable[[], str] | None = None,
    ) -> None:
        self.conn = conn
        self.executor = executor
        self.allowed_user_ids = set(allowed_user_ids or ())
        self.confirmation_code = confirmation_code or self._default_confirmation_code

    def handle(self, text: str, *, user_id: str) -> dict[str, Any]:
        command_text = text.strip()
        if self.allowed_user_ids and user_id not in self.allowed_user_ids:
            response = {
                "status": "forbidden",
                "message": "user is not allowed to control this local brain",
                "requires_confirmation": False,
            }
            self._audit(user_id, command_text, response)
            return response

        if command_text == "/status":
            response = {
                "status": "ok",
                "message": "Binance Spot Testnet brain is online. Risky actions require confirmation.",
                "requires_confirmation": False,
            }
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/test-buy "):
            response = self._prepare_test_buy(command_text, user_id)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("确认-"):
            response = self._confirm(command_text.removeprefix("确认-"), user_id)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/confirm "):
            response = self._confirm(command_text.removeprefix("/confirm ").strip(), user_id)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/review-add "):
            response = self._save_review(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/review-summary"):
            response = self._review_summary(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/lesson "):
            response = self._save_lesson(command_text)
            self._audit(user_id, command_text, response)
            return response

        response = {
            "status": "unknown",
            "message": "unknown command",
            "requires_confirmation": False,
        }
        self._audit(user_id, command_text, response)
        return response

    def _prepare_test_buy(self, command_text: str, user_id: str) -> dict[str, Any]:
        parts = command_text.split()
        if len(parts) != 3:
            return {
                "status": "invalid",
                "message": "usage: /test-buy SYMBOL QUOTE_AMOUNT",
                "requires_confirmation": False,
            }

        symbol = parts[1].upper()
        try:
            quote_order_qty = float(parts[2])
        except ValueError:
            return {
                "status": "invalid",
                "message": "quote amount must be a number",
                "requires_confirmation": False,
            }

        code = self.confirmation_code()
        payload = {
            "action": "test_order",
            "symbol": symbol,
            "side": "BUY",
            "order_type": "MARKET",
            "quote_order_qty": quote_order_qty,
        }
        self.conn.execute(
            """
            insert into brain_pending_confirmations (code, user_id, command_text, payload)
            values (?, ?, ?, ?)
            """,
            (code, user_id, command_text, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
        )
        self.conn.commit()
        return {
            "status": "pending_confirmation",
            "message": f"Prepared Spot Testnet test buy. Reply 确认-{code} to execute the test order.",
            "requires_confirmation": True,
            "confirmation_code": code,
        }

    def _confirm(self, code: str, user_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """
            select id, payload
            from brain_pending_confirmations
            where code = ? and user_id = ?
            """,
            (code, user_id),
        ).fetchone()
        if row is None:
            return {
                "status": "not_found",
                "message": "pending confirmation was not found or already executed",
                "requires_confirmation": False,
            }

        payload = json.loads(row["payload"])
        try:
            self.executor.test_order(
                symbol=payload["symbol"],
                side=payload["side"],
                order_type=payload["order_type"],
                quote_order_qty=payload["quote_order_qty"],
            )
        except Exception as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }
        self.conn.execute("delete from brain_pending_confirmations where id = ?", (row["id"],))
        self.conn.commit()
        return {
            "status": "executed",
            "message": "Spot Testnet test order executed.",
            "requires_confirmation": False,
        }

    def _save_review(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/review-add "))
        required = {"date", "symbols", "trades", "plan", "pnl", "lesson"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }

        review_date = fields["date"]
        external_id = f"review-{review_date}"
        try:
            save_daily_review(
                self.conn,
                external_id=external_id,
                review_date=review_date,
                symbols_watched=self._csv_values(fields["symbols"]),
                trade_count=int(fields["trades"]),
                plan_followed=fields["plan"].lower() in {"yes", "true", "1"},
                pnl=float(fields["pnl"]),
                mistake_tags=self._csv_values(fields.get("tags", "")),
                emotion_note=self._display_value(fields.get("note", "")),
                lesson=self._display_value(fields["lesson"]),
            )
        except sqlite3.IntegrityError as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }

        return {
            "status": "saved",
            "message": f"saved review {external_id}",
            "external_id": external_id,
            "requires_confirmation": False,
        }

    def _review_summary(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/review-summary").strip())
        limit = int(fields.get("limit", "5"))
        rows = self.conn.execute(
            """
            select review_date, symbols_watched, trade_count, plan_followed, pnl, mistake_tags, lesson
            from daily_reviews
            order by review_date desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return {
            "status": "ok",
            "reviews": [
                {
                    "review_date": row["review_date"],
                    "symbols_watched": json.loads(row["symbols_watched"]),
                    "trade_count": row["trade_count"],
                    "plan_followed": bool(row["plan_followed"]),
                    "pnl": row["pnl"],
                    "mistake_tags": json.loads(row["mistake_tags"]),
                    "lesson": row["lesson"],
                }
                for row in rows
            ],
            "requires_confirmation": False,
        }

    def _save_lesson(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/lesson "))
        required = {"title", "category", "content"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }

        external_id = f"knowledge-{uuid4()}"
        save_knowledge_card(
            self.conn,
            external_id=external_id,
            title=self._display_value(fields["title"]),
            category=fields["category"],
            content=self._display_value(fields["content"]),
        )
        return {
            "status": "saved",
            "message": f"saved lesson {external_id}",
            "external_id": external_id,
            "requires_confirmation": False,
        }

    def _audit(self, user_id: str, command_text: str, response: dict[str, Any]) -> None:
        self.conn.execute(
            """
            insert into brain_audit_logs (external_id, user_id, command_text, status, response)
            values (?, ?, ?, ?, ?)
            """,
            (
                f"brain-audit-{uuid4()}",
                user_id,
                command_text,
                str(response.get("status", "unknown")),
                json.dumps(response, ensure_ascii=False, sort_keys=True),
            ),
        )
        self.conn.commit()

    @staticmethod
    def _default_confirmation_code() -> str:
        return uuid4().hex[:6]

    @staticmethod
    def _parse_key_value_args(value: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for part in value.split():
            key, separator, field_value = part.partition("=")
            if separator and key:
                fields[key] = field_value
        return fields

    @staticmethod
    def _csv_values(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _display_value(value: str) -> str:
        return value.replace("_", " ")
