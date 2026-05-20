from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4


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
        self.executor.test_order(
            symbol=payload["symbol"],
            side=payload["side"],
            order_type=payload["order_type"],
            quote_order_qty=payload["quote_order_qty"],
        )
        self.conn.execute("delete from brain_pending_confirmations where id = ?", (row["id"],))
        self.conn.commit()
        return {
            "status": "executed",
            "message": "Spot Testnet test order executed.",
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
