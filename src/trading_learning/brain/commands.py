from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
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
        natural_language: Any | None = None,
    ) -> None:
        self.conn = conn
        self.executor = executor
        self.allowed_user_ids = set(allowed_user_ids or ())
        self.confirmation_code = confirmation_code or self._default_confirmation_code
        self.natural_language = natural_language

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

        if command_text.startswith("/testnet-create-buy "):
            response = self._prepare_testnet_create_buy(command_text, user_id)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/testnet-cancel "):
            response = self._prepare_testnet_cancel(command_text, user_id)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/testnet-order "):
            response = self._testnet_order(command_text)
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

        if command_text.startswith("/plan-set "):
            response = self._save_plan(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/checklist "):
            response = self._save_checklist(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/plan-status"):
            response = self._plan_status(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/knowledge-add "):
            response = self._knowledge_add(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/knowledge-search"):
            response = self._knowledge_search(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/mistake-link "):
            response = self._mistake_link(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text == "/run suggested":
            response = self._run_suggested(user_id)
            self._audit(user_id, command_text, response)
            return response

        if self.natural_language is not None and not command_text.startswith("/"):
            response = self._natural_language_reply(command_text, user_id)
            self._audit(user_id, command_text, response)
            return response

        if not command_text.startswith("/"):
            response = {
                "status": "chat_unavailable",
                "message": "Natural language chat requires LOCAL_CODEX_API_KEY in the local environment.",
                "requires_confirmation": False,
            }
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

        block = self._execution_block(symbol)
        if block is not None:
            return block

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

    def _prepare_testnet_create_buy(self, command_text: str, user_id: str) -> dict[str, Any]:
        parts = command_text.split()
        if len(parts) != 3:
            return {
                "status": "invalid",
                "message": "usage: /testnet-create-buy SYMBOL QUOTE_AMOUNT",
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
        block = self._execution_block(symbol)
        if block is not None:
            return block
        payload = {
            "action": "create_order",
            "symbol": symbol,
            "side": "BUY",
            "order_type": "MARKET",
            "quote_order_qty": quote_order_qty,
        }
        return self._save_pending_confirmation(user_id, command_text, payload)

    def _prepare_testnet_cancel(self, command_text: str, user_id: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/testnet-cancel "))
        if "symbol" not in fields or "order_id" not in fields:
            return {
                "status": "invalid",
                "message": "usage: /testnet-cancel symbol=SYMBOL order_id=ID",
                "requires_confirmation": False,
            }
        payload = {
            "action": "cancel_order",
            "symbol": fields["symbol"].upper(),
            "order_id": int(fields["order_id"]),
        }
        return self._save_pending_confirmation(user_id, command_text, payload)

    def _testnet_order(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/testnet-order "))
        if "symbol" not in fields or "order_id" not in fields:
            return {
                "status": "invalid",
                "message": "usage: /testnet-order symbol=SYMBOL order_id=ID",
                "requires_confirmation": False,
            }
        try:
            order = self.executor.get_order(symbol=fields["symbol"].upper(), order_id=int(fields["order_id"]))
        except Exception as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }
        return {
            "status": "ok",
            "order": order,
            "requires_confirmation": False,
        }

    def _save_pending_confirmation(
        self,
        user_id: str,
        command_text: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        code = self.confirmation_code()
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
            "message": f"Prepared {payload['action']}. Reply 确认-{code} to execute.",
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
            if payload["action"] == "test_order":
                self.executor.test_order(
                    symbol=payload["symbol"],
                    side=payload["side"],
                    order_type=payload["order_type"],
                    quote_order_qty=payload["quote_order_qty"],
                )
            elif payload["action"] == "create_order":
                self.executor.create_order(
                    symbol=payload["symbol"],
                    side=payload["side"],
                    order_type=payload["order_type"],
                    quote_order_qty=payload["quote_order_qty"],
                )
            elif payload["action"] == "cancel_order":
                self.executor.cancel_order(
                    symbol=payload["symbol"],
                    order_id=payload["order_id"],
                )
            else:
                raise ValueError(f"unknown pending action {payload['action']}")
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

    def _save_plan(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/plan-set "))
        required = {"date", "symbols", "max_trades"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        external_id = f"plan-{fields['date']}"
        self.conn.execute(
            """
            insert into trading_plans (
              external_id, plan_date, symbols, max_trades, bias, conditions, forbidden
            ) values (?, ?, ?, ?, ?, ?, ?)
            on conflict(plan_date) do update set
              symbols = excluded.symbols,
              max_trades = excluded.max_trades,
              bias = excluded.bias,
              conditions = excluded.conditions,
              forbidden = excluded.forbidden,
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                external_id,
                fields["date"],
                json.dumps(self._csv_values(fields["symbols"]), ensure_ascii=False),
                int(fields["max_trades"]),
                self._display_value(fields.get("bias", "")),
                self._display_value(fields.get("conditions", "")),
                self._display_value(fields.get("forbidden", "")),
            ),
        )
        self.conn.commit()
        return {
            "status": "saved",
            "message": f"saved plan {external_id}",
            "external_id": external_id,
            "requires_confirmation": False,
        }

    def _save_checklist(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/checklist "))
        if "symbol" not in fields:
            return {
                "status": "invalid",
                "message": "missing fields: symbol",
                "requires_confirmation": False,
            }
        checklist_date = fields.get("date", self._today())
        symbol = fields["symbol"].upper()
        external_id = f"checklist-{checklist_date}-{symbol}-{uuid4()}"
        emotion = fields.get("emotion", "")
        self.conn.execute(
            """
            insert into pre_trade_checklists (
              external_id, checklist_date, symbol, plan_ok, setup_ok, risk_ok, emotion, emotion_ok
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                external_id,
                checklist_date,
                symbol,
                1 if self._truthy(fields.get("plan", "")) else 0,
                1 if self._truthy(fields.get("setup", "")) else 0,
                1 if self._truthy(fields.get("risk", "")) else 0,
                self._display_value(emotion),
                0 if emotion.lower() in {"panic", "fomo", "angry", "revenge"} else 1,
            ),
        )
        self.conn.commit()
        return {
            "status": "saved",
            "message": f"saved checklist {external_id}",
            "external_id": external_id,
            "requires_confirmation": False,
        }

    def _plan_status(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/plan-status").strip())
        plan_date = fields.get("date", self._today())
        plan = self._plan_for_date(plan_date)
        checklist_rows = self.conn.execute(
            """
            select symbol, plan_ok, setup_ok, risk_ok, emotion, emotion_ok, created_at
            from pre_trade_checklists
            where checklist_date = ?
            order by id desc
            """,
            (plan_date,),
        ).fetchall()
        return {
            "status": "ok",
            "plan": plan,
            "checklists": [
                {
                    "symbol": row["symbol"],
                    "plan_ok": bool(row["plan_ok"]),
                    "setup_ok": bool(row["setup_ok"]),
                    "risk_ok": bool(row["risk_ok"]),
                    "emotion": row["emotion"],
                    "emotion_ok": bool(row["emotion_ok"]),
                    "created_at": row["created_at"],
                }
                for row in checklist_rows
            ],
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

    def _knowledge_add(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/knowledge-add "))
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
        for tag in self._csv_values(fields.get("tags", "")):
            self.conn.execute(
                """
                insert or ignore into knowledge_card_tags (card_external_id, tag)
                values (?, ?)
                """,
                (external_id, tag),
            )
        self.conn.commit()
        return {
            "status": "saved",
            "message": f"saved knowledge card {external_id}",
            "external_id": external_id,
            "requires_confirmation": False,
        }

    def _knowledge_search(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/knowledge-search").strip())
        query = fields.get("query", "")
        limit = int(fields.get("limit", "5"))
        pattern = f"%{self._display_value(query)}%"
        rows = self.conn.execute(
            """
            select external_id, title, category, content
            from knowledge_cards
            where title like ? or category like ? or content like ?
            order by id desc
            limit ?
            """,
            (pattern, pattern, pattern, limit),
        ).fetchall()
        return {
            "status": "ok",
            "cards": [
                {
                    "external_id": row["external_id"],
                    "title": row["title"],
                    "category": row["category"],
                    "content": row["content"],
                    "tags": self._tags_for_card(row["external_id"]),
                }
                for row in rows
            ],
            "requires_confirmation": False,
        }

    def _mistake_link(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/mistake-link "))
        required = {"review", "card", "tag"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        self.conn.execute(
            """
            insert or ignore into mistake_knowledge_links (review_external_id, card_external_id, tag)
            values (?, ?, ?)
            """,
            (fields["review"], fields["card"], fields["tag"]),
        )
        self.conn.commit()
        return {
            "status": "saved",
            "message": "linked mistake to knowledge card",
            "requires_confirmation": False,
        }

    def _natural_language_reply(self, command_text: str, user_id: str) -> dict[str, Any]:
        try:
            response = self.natural_language.reply(
                command_text,
                user_id=user_id,
                context=self._brain_context(),
            )
        except Exception as exc:
            return {
                "status": "chat_unavailable",
                "message": str(exc),
                "requires_confirmation": False,
            }
        response.setdefault("requires_confirmation", False)
        suggested_command = response.get("suggested_command", "")
        if isinstance(suggested_command, str) and suggested_command.strip():
            self._store_suggested_command(
                user_id=user_id,
                source_text=command_text,
                command_text=suggested_command.strip(),
            )
        return response

    def _store_suggested_command(self, *, user_id: str, source_text: str, command_text: str) -> str:
        external_id = f"suggested-{uuid4()}"
        self.conn.execute(
            """
            insert into brain_suggested_commands (external_id, user_id, command_text, source_text)
            values (?, ?, ?, ?)
            """,
            (external_id, user_id, command_text, source_text),
        )
        self.conn.commit()
        return external_id

    def _run_suggested(self, user_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """
            select id, command_text
            from brain_suggested_commands
            where user_id = ? and status = 'pending'
            order by id desc
            limit 1
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            return {
                "status": "not_found",
                "message": "no pending suggested command",
                "requires_confirmation": False,
            }

        command_text = row["command_text"].strip()
        if not self._is_safe_suggested_command(command_text):
            response = {
                "status": "blocked",
                "message": "suggested command is not a safe command; type it manually if you want to proceed",
                "requires_confirmation": False,
            }
            self._update_suggestion(row["id"], "blocked", response)
            return response

        result = self.handle(command_text, user_id=user_id)
        response = {
            "status": "executed",
            "message": "suggested command executed",
            "executed_command": command_text,
            "result": result,
            "requires_confirmation": False,
        }
        self._update_suggestion(row["id"], "executed", response)
        return response

    def _update_suggestion(self, row_id: int, status: str, result: dict[str, Any]) -> None:
        self.conn.execute(
            """
            update brain_suggested_commands
            set status = ?, result = ?, updated_at = CURRENT_TIMESTAMP
            where id = ?
            """,
            (status, json.dumps(result, ensure_ascii=False, sort_keys=True), row_id),
        )
        self.conn.commit()

    @staticmethod
    def _is_safe_suggested_command(command_text: str) -> bool:
        safe_prefixes = (
            "/review-add ",
            "/lesson ",
            "/knowledge-add ",
            "/mistake-link ",
            "/plan-set ",
            "/checklist ",
        )
        return command_text.startswith(safe_prefixes)

    def _brain_context(self) -> dict[str, Any]:
        return {
            "today": self._today(),
            "plan": self._plan_for_date(self._today()),
            "available_commands": [
                "/status",
                "/plan-set",
                "/checklist",
                "/plan-status",
                "/test-buy",
                "/testnet-create-buy",
                "/review-add",
                "/review-summary",
                "/knowledge-add",
                "/knowledge-search",
            ],
        }

    def _execution_block(self, symbol: str) -> dict[str, Any] | None:
        plan = self._plan_for_date(self._today())
        if plan is None:
            return {
                "status": "blocked",
                "message": "today's trading plan is missing",
                "requires_confirmation": False,
            }
        if symbol not in plan["symbols"]:
            return {
                "status": "blocked",
                "message": f"{symbol} is not in today's plan",
                "requires_confirmation": False,
            }
        row = self.conn.execute(
            """
            select plan_ok, setup_ok, risk_ok, emotion_ok
            from pre_trade_checklists
            where checklist_date = ? and symbol = ?
            order by id desc
            limit 1
            """,
            (self._today(), symbol),
        ).fetchone()
        if row is None:
            return {
                "status": "blocked",
                "message": f"pre-trade checklist is missing for {symbol}",
                "requires_confirmation": False,
            }
        if not all(bool(row[key]) for key in ("plan_ok", "setup_ok", "risk_ok", "emotion_ok")):
            return {
                "status": "blocked",
                "message": f"pre-trade checklist is not fully approved for {symbol}",
                "requires_confirmation": False,
            }
        return None

    def _plan_for_date(self, plan_date: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            select external_id, plan_date, symbols, max_trades, bias, conditions, forbidden
            from trading_plans
            where plan_date = ?
            """,
            (plan_date,),
        ).fetchone()
        if row is None:
            return None
        return {
            "external_id": row["external_id"],
            "plan_date": row["plan_date"],
            "symbols": json.loads(row["symbols"]),
            "max_trades": row["max_trades"],
            "bias": row["bias"],
            "conditions": row["conditions"],
            "forbidden": row["forbidden"],
        }

    def _tags_for_card(self, external_id: str) -> list[str]:
        rows = self.conn.execute(
            """
            select tag
            from knowledge_card_tags
            where card_external_id = ?
            order by id
            """,
            (external_id,),
        ).fetchall()
        return [row["tag"] for row in rows]

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

    @staticmethod
    def _truthy(value: str) -> bool:
        return value.lower() in {"yes", "true", "1", "ok"}

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()
