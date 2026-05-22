from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import pandas as pd

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.backtest.report import summarize_backtest
from trading_learning.backtest.walk_forward import WalkForwardConfig
from trading_learning.backtest.walk_forward import run_walk_forward
from trading_learning.brain.command_aliases import normalize_brain_command
from trading_learning.brain.natural_language import mock_mode_guidance
from trading_learning.brain.remote_tasks import TaskQueue
from trading_learning.config import DEFAULT_ALLOWED_SYMBOLS
from trading_learning.dashboard.data import DashboardData
from trading_learning.journal.repository import save_daily_review
from trading_learning.journal.repository import save_trades
from trading_learning.learning.experiment_review import build_experiment_review_draft
from trading_learning.learning.coach import build_next_experiment_proposal
from trading_learning.learning.coach import evaluate_experiment_proposal
from trading_learning.learning.coach import save_experiment_proposal
from trading_learning.learning.curriculum import build_failed_experiment_learning
from trading_learning.learning.curriculum import build_review_queue
from trading_learning.learning.daily_coach import build_daily_coach_plan
from trading_learning.learning.repository import save_knowledge_card
from trading_learning.market_data.binance_klines import fetch_klines, save_klines_csv
from trading_learning.market_data.catalog import DEFAULT_MARKET_INTERVALS
from trading_learning.market_data.catalog import inventory_datasets
from trading_learning.market_data.catalog import refresh_market_data
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.production_gate import RealOrderIntent
from trading_learning.production_gate import build_real_order_dry_run
from trading_learning.production_gate import production_readiness_status
from trading_learning.research.hypothesis_log import HypothesisLog
from trading_learning.strategy.moving_average import moving_average_crossover_signals
from trading_learning.strategy.mtf_trend import mtf_trend_strategy_factory
from trading_learning.strategy.lab import list_strategy_profiles
from trading_learning.strategy.lab import run_ma_parameter_sweep
from trading_learning.strategy.lab import save_strategy_profile
from trading_learning.strategy.decisions import save_experiment_decision
from trading_learning.workspace import build_workspace_state
from trading_learning.workspace import reset_workspace


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
        allowed_market_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
        confirmation_code: Callable[[], str] | None = None,
        natural_language: Any | None = None,
        llm_status_provider: Callable[[], dict[str, Any]] | None = None,
        kline_fetcher: Callable[..., Any] | None = None,
        db_path: Path | None = None,
        backup_dir: Path | None = None,
    ) -> None:
        self.conn = conn
        self.executor = executor
        self.allowed_user_ids = set(allowed_user_ids or ())
        self.allowed_market_symbols = tuple(symbol.upper() for symbol in allowed_market_symbols)
        self.confirmation_code = confirmation_code or self._default_confirmation_code
        self.natural_language = natural_language
        self.llm_status_provider = llm_status_provider or self._default_llm_status
        self.kline_fetcher = kline_fetcher or fetch_klines
        self.db_path = db_path
        self.backup_dir = backup_dir or Path("data/backups")

    def handle(self, text: str, *, user_id: str) -> dict[str, Any]:
        command_text = normalize_brain_command(text.strip())
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

        if command_text == "/llm-status":
            response = self._llm_status()
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

        if command_text.startswith("/testnet-signal-buy "):
            response = self._prepare_testnet_signal_buy(command_text, user_id)
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

        if command_text.startswith("/testnet-status"):
            response = self._testnet_status()
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/real-trading-status"):
            response = self._real_trading_status()
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/kill-switch-status"):
            response = self._kill_switch_status()
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/kill-switch-enable"):
            response = self._kill_switch_enable()
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/workspace-status"):
            response = self._workspace_status()
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/workspace-reset"):
            response = self._workspace_reset(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/real-trading-enable"):
            response = {
                "status": "blocked",
                "message": "Real trading can only be considered after the local production readiness gate is completed.",
                "requires_confirmation": False,
            }
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/real-create-buy"):
            response = {
                "status": "blocked",
                "message": "Real order routes are disabled. Use /real-dry-run-buy for local simulation only.",
                "requires_confirmation": False,
            }
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/real-dry-run-buy"):
            response = self._real_dry_run_buy(command_text)
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

        if command_text.startswith("/experiment-link "):
            response = self._experiment_link(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/review-context"):
            response = self._review_context(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/history-download "):
            response = self._history_download(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/market-refresh"):
            response = self._market_refresh(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/market-status"):
            response = self._market_status(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/queue-market-refresh"):
            response = self._queue_market_refresh(command_text, user_id)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/queue-backtest-ma "):
            response = self._queue_backtest_ma(command_text, user_id)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/queue-status"):
            response = self._queue_status(command_text, user_id)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/task-status"):
            response = self._task_status(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/backtest-ma "):
            response = self._backtest_ma(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/experiment-summary"):
            response = self._experiment_summary(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/experiment-review-commit"):
            response = self._experiment_review_commit(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/experiment-learning"):
            response = self._experiment_learning(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/experiment-review"):
            response = self._experiment_review(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/daily-report"):
            response = self._daily_report(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/weekly-report"):
            response = self._weekly_report(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/learning-next"):
            response = self._learning_next(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/learning-queue"):
            response = self._learning_queue(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/coach-next"):
            response = self._coach_next(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/coach-daily"):
            response = self._coach_daily()
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/coach-evaluate "):
            response = self._coach_evaluate(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/strategy-profile-set "):
            response = self._strategy_profile_set(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/strategy-profile-list"):
            response = self._strategy_profile_list(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/sweep-ma "):
            response = self._sweep_ma(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/experiment-decision "):
            response = self._experiment_decision(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/hypothesis-create "):
            response = self._hypothesis_create(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/hypothesis-resolve "):
            response = self._hypothesis_resolve(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/hypothesis-list"):
            response = self._hypothesis_list()
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/research-status"):
            response = self._research_status()
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/research-baseline"):
            response = self._research_baseline(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/research-test"):
            response = self._research_test(command_text)
            self._audit(user_id, command_text, response)
            return response

        if command_text.startswith("/research-ablation"):
            response = self._research_ablation(command_text)
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
            response = mock_mode_guidance()
            self._audit(user_id, command_text, response)
            return response

        response = {
            "status": "unknown",
            "message": "unknown command",
            "requires_confirmation": False,
        }
        self._audit(user_id, command_text, response)
        return response

    def _llm_status(self) -> dict[str, Any]:
        llm = self.llm_status_provider()
        return {
            "status": "ok",
            "llm": llm,
            "message": (
                f"LLM: {llm.get('mode', 'unknown')} | "
                f"reachable={bool(llm.get('reachable'))} | "
                f"base_url={llm.get('base_url', '')}"
            ),
            "requires_confirmation": False,
        }

    def _workspace_status(self) -> dict[str, Any]:
        state = build_workspace_state(self.conn)
        return {
            "status": "ok",
            "workspace_state": state,
            "message": f"Workspace: {state['status']} | experiments={state['counts']['strategy_experiments']} | reviews={state['counts']['daily_reviews']}",
            "requires_confirmation": False,
        }

    def _workspace_reset(self, command_text: str) -> dict[str, Any]:
        if self.db_path is None:
            return {
                "status": "not_configured",
                "message": "workspace reset requires BrainCommandHandler db_path configuration",
                "requires_confirmation": False,
            }
        fields = self._parse_key_value_args(command_text.removeprefix("/workspace-reset").strip())
        return reset_workspace(
            self.conn,
            db_path=self.db_path,
            backup_dir=self.backup_dir,
            confirm=fields.get("confirm", ""),
        )

    @staticmethod
    def _default_llm_status() -> dict[str, Any]:
        return {
            "mode": "mock",
            "configured": False,
            "reachable": False,
            "base_url": "",
            "model": "",
            "message": "Local Codex/LLM is not configured for this Brain process.",
        }

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

    def _prepare_testnet_signal_buy(self, command_text: str, user_id: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/testnet-signal-buy "))
        required = {"experiment", "signal", "quote"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        experiment_id = fields["experiment"].strip()
        experiment = self._experiment_row(experiment_id)
        if experiment is None:
            return {
                "status": "not_found",
                "message": f"experiment not found: {experiment_id}",
                "requires_confirmation": False,
            }
        decision = self._experiment_decision_value(experiment_id)
        if decision != "testnet_candidate":
            return {
                "status": "blocked",
                "message": "experiment must be marked testnet_candidate before testnet signal execution",
                "requires_confirmation": False,
            }
        try:
            quote_order_qty = float(fields["quote"])
        except ValueError:
            return {
                "status": "invalid",
                "message": "quote must be a number",
                "requires_confirmation": False,
            }
        symbol = str(experiment["symbol"]).upper()
        context = self._execution_context(symbol)
        if "block" in context:
            return context["block"]
        payload = {
            "action": "create_order",
            "symbol": symbol,
            "side": "BUY",
            "order_type": "MARKET",
            "quote_order_qty": quote_order_qty,
            "experiment_external_id": experiment_id,
            "signal_id": fields["signal"].strip(),
            "plan_external_id": context["plan_external_id"],
            "checklist_external_id": context["checklist_external_id"],
            "review_external_id": fields.get("review", "").strip(),
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
        result: dict[str, Any] = {}
        try:
            if payload["action"] == "test_order":
                result = self.executor.test_order(
                    symbol=payload["symbol"],
                    side=payload["side"],
                    order_type=payload["order_type"],
                    quote_order_qty=payload["quote_order_qty"],
                )
            elif payload["action"] == "create_order":
                result = self.executor.create_order(
                    symbol=payload["symbol"],
                    side=payload["side"],
                    order_type=payload["order_type"],
                    quote_order_qty=payload["quote_order_qty"],
                )
            elif payload["action"] == "cancel_order":
                result = self.executor.cancel_order(
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
        self._record_testnet_order(user_id=user_id, payload=payload, response=result)
        self.conn.execute("delete from brain_pending_confirmations where id = ?", (row["id"],))
        self.conn.commit()
        return {
            "status": "executed",
            "message": "Spot Testnet test order executed.",
            "requires_confirmation": False,
        }

    def _testnet_status(self) -> dict[str, Any]:
        try:
            account = self.executor.account()
        except Exception as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }
        balances = [
            {
                "asset": str(item.get("asset", "")),
                "free": str(item.get("free", "0")),
                "locked": str(item.get("locked", "0")),
            }
            for item in account.get("balances", [])
            if float(item.get("free", "0") or 0) != 0 or float(item.get("locked", "0") or 0) != 0
        ]
        return {
            "status": "ok",
            "account": {
                "account_type": account.get("accountType", ""),
                "balances": balances,
            },
            "requires_confirmation": False,
        }

    def _record_testnet_order(self, *, user_id: str, payload: dict[str, Any], response: dict[str, Any]) -> None:
        if payload.get("action") not in {"create_order", "cancel_order"}:
            return
        self.conn.execute(
            """
            insert into testnet_order_records (
              external_id, user_id, action, symbol, side, order_type, quote_order_qty,
              order_id, status, experiment_external_id, signal_id, plan_external_id,
              checklist_external_id, review_external_id, request_payload, response_payload
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"testnet-order-{uuid4()}",
                user_id,
                payload.get("action", ""),
                payload.get("symbol", ""),
                payload.get("side", ""),
                payload.get("order_type", ""),
                payload.get("quote_order_qty"),
                str(response.get("orderId", "")),
                str(response.get("status", "")),
                payload.get("experiment_external_id", ""),
                payload.get("signal_id", ""),
                payload.get("plan_external_id", ""),
                payload.get("checklist_external_id", ""),
                payload.get("review_external_id", ""),
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                json.dumps(response, ensure_ascii=False, sort_keys=True),
            ),
        )

    def _real_trading_status(self) -> dict[str, Any]:
        return {
            "status": "blocked",
            "gate": production_readiness_status(),
            "requires_confirmation": False,
        }

    def _real_dry_run_buy(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/real-dry-run-buy").strip())
        try:
            symbol = fields.get("symbol", "").upper()
            quote = float(fields.get("quote", "0"))
        except ValueError:
            return {
                "status": "invalid",
                "message": "quote must be a number",
                "requires_confirmation": False,
            }
        if not symbol:
            return {
                "status": "invalid",
                "message": "missing fields: symbol",
                "requires_confirmation": False,
            }
        order_path = build_real_order_dry_run(
            RealOrderIntent(symbol=symbol, side="BUY", order_type="MARKET", quote_order_qty=quote)
        )
        return {
            "status": "dry_run",
            "message": "real trading dry-run simulated locally; no order was sent",
            "gate": production_readiness_status(),
            "order_path": order_path,
            "requires_confirmation": False,
        }

    def _kill_switch_status(self) -> dict[str, Any]:
        gate = production_readiness_status()
        return {
            "status": "ok",
            "kill_switch": gate["kill_switch"],
            "real_trading_enabled": gate["real_trading_enabled"],
            "message": gate["kill_switch"]["message"],
            "requires_confirmation": False,
        }

    def _kill_switch_enable(self) -> dict[str, Any]:
        gate = production_readiness_status()
        return {
            "status": "ok",
            "kill_switch": gate["kill_switch"],
            "real_trading_enabled": gate["real_trading_enabled"],
            "message": "Kill switch remains active. Real trading is still disabled.",
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

    def _experiment_link(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/experiment-link "))
        required = {"review", "experiment", "tag"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        review_id = fields["review"]
        experiment_id = fields["experiment"]
        if self._review_row(review_id) is None:
            return {
                "status": "not_found",
                "message": f"review not found: {review_id}",
                "requires_confirmation": False,
            }
        if self._experiment_row(experiment_id) is None:
            return {
                "status": "not_found",
                "message": f"experiment not found: {experiment_id}",
                "requires_confirmation": False,
            }
        self.conn.execute(
            """
            insert into review_experiment_links (
              review_external_id, experiment_external_id, tag, note
            ) values (?, ?, ?, ?)
            on conflict(review_external_id, experiment_external_id, tag) do update set
              note = excluded.note
            """,
            (
                review_id,
                experiment_id,
                fields["tag"],
                self._display_value(fields.get("note", "")),
            ),
        )
        self.conn.commit()
        return {
            "status": "saved",
            "message": "linked review to experiment",
            "requires_confirmation": False,
        }

    def _review_context(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/review-context").strip())
        review_id = fields.get("review", "")
        if not review_id:
            return {
                "status": "invalid",
                "message": "missing fields: review",
                "requires_confirmation": False,
            }
        review_row = self._review_row(review_id)
        if review_row is None:
            return {
                "status": "not_found",
                "message": f"review not found: {review_id}",
                "requires_confirmation": False,
            }
        context = self._review_context_payload(review_id, review_row)
        context.update({"status": "ok", "requires_confirmation": False})
        return context

    def _history_download(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/history-download "))
        required = {"symbol", "interval", "output"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        try:
            limit = int(fields.get("limit", "500"))
            start_time_ms = self._optional_int(fields.get("start_ms"))
            end_time_ms = self._optional_int(fields.get("end_ms"))
        except ValueError:
            return {
                "status": "invalid",
                "message": "limit, start_ms, and end_ms must be integers",
                "requires_confirmation": False,
            }
        symbol = fields["symbol"].upper()
        if symbol not in self.allowed_market_symbols:
            return self._symbol_not_allowed(symbol)
        try:
            output_path = self._safe_data_local_path(fields["output"])
        except ValueError as exc:
            return {
                "status": "invalid",
                "message": str(exc),
                "requires_confirmation": False,
            }
        try:
            candles = self.kline_fetcher(
                symbol=symbol,
                interval=fields["interval"],
                limit=limit,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
            )
            save_klines_csv(candles, output_path)
        except Exception as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }
        return {
            "status": "saved",
            "message": f"downloaded {len(candles)} candles to {output_path}",
            "path": str(output_path),
            "count": len(candles),
            "requires_confirmation": False,
        }

    def _market_refresh(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/market-refresh").strip())
        try:
            limit = int(fields.get("limit", "500"))
        except ValueError:
            return {
                "status": "invalid",
                "message": "limit must be an integer",
                "requires_confirmation": False,
            }
        symbols = tuple(symbol.upper() for symbol in self._csv_values(fields.get("symbols", ""))) or self.allowed_market_symbols
        intervals = tuple(self._csv_values(fields.get("intervals", ""))) or DEFAULT_MARKET_INTERVALS
        try:
            result = refresh_market_data(
                symbols=symbols,
                intervals=intervals,
                allowed_symbols=self.allowed_market_symbols,
                limit=limit,
                fetcher=self.kline_fetcher,
            )
        except ValueError as exc:
            return {
                "status": "invalid",
                "message": str(exc),
                "requires_confirmation": False,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }
        return {
            "status": "saved",
            "message": f"refreshed {len(result['datasets'])} datasets",
            "count": len(result["datasets"]),
            "datasets": result["datasets"],
            "requires_confirmation": False,
        }

    def _market_status(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/market-status").strip())
        symbols = tuple(symbol.upper() for symbol in self._csv_values(fields.get("symbols", ""))) or self.allowed_market_symbols
        intervals = tuple(self._csv_values(fields.get("intervals", ""))) or DEFAULT_MARKET_INTERVALS
        unsupported = [symbol for symbol in symbols if symbol not in self.allowed_market_symbols]
        if unsupported:
            return {
                "status": "invalid",
                "message": f"symbol not allowed: {unsupported[0]}. allowed: {', '.join(self.allowed_market_symbols)}",
                "requires_confirmation": False,
            }
        datasets = inventory_datasets(allowed_symbols=symbols, intervals=intervals)
        cached = [dataset for dataset in datasets if dataset["exists"]]
        missing = [dataset for dataset in datasets if not dataset["exists"]]
        gap_count = sum(int(dataset.get("gap_count", 0)) for dataset in datasets)
        return {
            "status": "ok",
            "cached_count": len(cached),
            "missing_count": len(missing),
            "gap_count": gap_count,
            "datasets": datasets,
            "message": f"Market data cache: cached={len(cached)} missing={len(missing)} gaps={gap_count}",
            "requires_confirmation": False,
        }

    def _backtest_ma(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/backtest-ma "))
        required = {"csv", "symbol", "short", "long"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        try:
            symbol = fields["symbol"].upper()
            short_window = int(fields["short"])
            long_window = int(fields["long"])
            starting_cash = float(fields.get("starting_cash", "1000"))
            quote_amount = float(fields.get("quote_amount", "100"))
            fee_rate = float(fields.get("fee", "0.001"))
            daily_limit = int(fields.get("daily_limit", "5"))
        except ValueError:
            return {
                "status": "invalid",
                "message": "numeric backtest fields are invalid",
                "requires_confirmation": False,
            }
        if symbol not in self.allowed_market_symbols:
            return self._symbol_not_allowed(symbol)

        try:
            csv_path = self._safe_data_local_path(fields["csv"])
            candles = load_candles_csv(csv_path, symbol)
            signals = moving_average_crossover_signals(
                candles,
                short_window=short_window,
                long_window=long_window,
            )
            prices = {candle.opened_at: candle.close for candle in candles}
            result = run_spot_backtest(
                symbol=symbol,
                signals=signals,
                prices_by_timestamp=prices,
                starting_cash=starting_cash,
                quote_amount_per_buy=quote_amount,
                fee_rate=fee_rate,
                daily_trade_limit=daily_limit,
            )
            metrics = summarize_backtest(result)
        except Exception as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }
        external_id = f"experiment-{uuid4()}"
        namespaced_trades = [
            replace(trade, external_id=f"{external_id}-{index}-{trade.side.value.lower()}")
            for index, trade in enumerate(result.trades, start=1)
        ]

        parameters = {
            "short_window": short_window,
            "long_window": long_window,
            "starting_cash": starting_cash,
            "quote_amount": quote_amount,
            "fee_rate": fee_rate,
            "daily_trade_limit": daily_limit,
        }
        metrics_payload = {
            "trade_count": result.trade_count,
            "ending_cash": result.ending_cash,
            "position_quantity": result.position_quantity,
            "round_trips": metrics.round_trips,
            "win_count": metrics.win_count,
            "loss_count": metrics.loss_count,
            "win_rate": metrics.win_rate,
            "realized_pnl": metrics.realized_pnl,
            "total_fees": metrics.total_fees,
        }
        try:
            with self.conn:
                self._insert_trades(namespaced_trades, source=external_id)
                self.conn.execute(
                    """
                    insert into strategy_experiments (
                      external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
                    ) values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        external_id,
                        "moving_average_crossover",
                        symbol,
                        fields.get("interval", ""),
                        str(csv_path),
                        json.dumps(parameters, ensure_ascii=False, sort_keys=True),
                        json.dumps(metrics_payload, ensure_ascii=False, sort_keys=True),
                        self._display_value(fields.get("note", "")),
                    ),
                )
        except sqlite3.Error as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }
        return {
            "status": "saved",
            "message": f"saved experiment {external_id}",
            "external_id": external_id,
            "strategy_name": "moving_average_crossover",
            "symbol": symbol,
            "metrics": metrics_payload,
            "requires_confirmation": False,
        }

    def _queue_backtest_ma(self, command_text: str, user_id: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/queue-backtest-ma "))
        required = {"csv", "symbol", "short", "long"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        symbol = fields["symbol"].upper()
        if symbol not in self.allowed_market_symbols:
            return self._symbol_not_allowed(symbol)
        try:
            payload = {
                "symbol": symbol,
                "interval": fields.get("interval", ""),
                "csv": fields["csv"],
                "short": int(fields["short"]),
                "long": int(fields["long"]),
                "starting_cash": float(fields.get("starting_cash", "1000")),
                "quote_amount": float(fields.get("quote_amount", "100")),
                "fee": float(fields.get("fee", "0.001")),
                "daily_limit": int(fields.get("daily_limit", "5")),
            }
        except ValueError:
            return {
                "status": "invalid",
                "message": "numeric backtest fields are invalid",
                "requires_confirmation": False,
            }
        task = TaskQueue(self.conn).create_task(
            requester_user_id=user_id,
            command_text=command_text,
            task_type="backtest_ma",
            risk_level="backtest",
            payload=payload,
        )
        return {
            "status": "queued",
            "message": f"queued local backtest task {task.external_id}",
            "task": task.to_dict(),
            "requires_confirmation": False,
        }

    def _queue_market_refresh(self, command_text: str, user_id: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/queue-market-refresh").strip())
        try:
            limit = int(fields.get("limit", "500"))
        except ValueError:
            return {
                "status": "invalid",
                "message": "limit must be an integer",
                "requires_confirmation": False,
            }
        symbols = tuple(symbol.upper() for symbol in self._csv_values(fields.get("symbols", ""))) or self.allowed_market_symbols
        intervals = tuple(self._csv_values(fields.get("intervals", ""))) or DEFAULT_MARKET_INTERVALS
        unsupported = [symbol for symbol in symbols if symbol not in self.allowed_market_symbols]
        if unsupported:
            return self._symbol_not_allowed(unsupported[0])
        task = TaskQueue(self.conn).create_task(
            requester_user_id=user_id,
            command_text=command_text,
            task_type="market_refresh",
            risk_level="data",
            payload={"symbols": list(symbols), "intervals": list(intervals), "limit": limit},
        )
        return {
            "status": "queued",
            "message": f"queued local market refresh task {task.external_id}",
            "task": task.to_dict(),
            "requires_confirmation": False,
        }

    def _queue_status(self, command_text: str, user_id: str) -> dict[str, Any]:
        task = TaskQueue(self.conn).create_task(
            requester_user_id=user_id,
            command_text=command_text,
            task_type="local_status",
            risk_level="query",
            payload={},
        )
        return {
            "status": "queued",
            "message": f"queued local status task {task.external_id}",
            "task": task.to_dict(),
            "requires_confirmation": False,
        }

    def _task_status(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/task-status").strip())
        try:
            limit = int(fields.get("limit", "5"))
        except ValueError:
            return {
                "status": "invalid",
                "message": "limit must be an integer",
                "requires_confirmation": False,
            }
        tasks = TaskQueue(self.conn).list_recent(limit=limit)
        message = "\n".join(self._format_task_status_line(task.to_dict()) for task in tasks) or "暂无远程任务"
        return {
            "status": "ok",
            "tasks": [task.to_dict() for task in tasks],
            "message": message,
            "requires_confirmation": False,
        }

    @staticmethod
    def _format_task_status_line(task: dict[str, Any]) -> str:
        parts = [
            f"任务 {task['external_id']}",
            f"type={task['task_type']}",
            f"state={task['state']}",
        ]
        if task.get("runner_id"):
            parts.append(f"runner={task['runner_id']}")
        if task.get("result_summary"):
            parts.append(str(task["result_summary"]))
        if task.get("error_message"):
            parts.append(f"error={task['error_message']}")
        return " | ".join(parts)

    def _experiment_summary(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/experiment-summary").strip())
        try:
            limit = int(fields.get("limit", "5"))
        except ValueError:
            return {
                "status": "invalid",
                "message": "limit must be an integer",
                "requires_confirmation": False,
            }
        rows = self.conn.execute(
            """
            select external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
            from strategy_experiments
            order by id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return {
            "status": "ok",
            "experiments": [
                {
                    "external_id": row["external_id"],
                    "strategy_name": row["strategy_name"],
                    "symbol": row["symbol"],
                    "interval": row["interval"],
                    "source_csv": row["source_csv"],
                    "parameters": json.loads(row["parameters"]),
                    "metrics": json.loads(row["metrics"]),
                    "note": row["note"],
                }
                for row in rows
            ],
            "requires_confirmation": False,
        }

    def _experiment_review(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/experiment-review").strip())
        experiment_id = fields.get("experiment", "").strip()
        if not experiment_id:
            return {
                "status": "invalid",
                "message": "missing fields: experiment",
                "requires_confirmation": False,
            }
        try:
            report = DashboardData(self.conn, allowed_symbols=self.allowed_market_symbols).backtest_report(experiment_id)
        except FileNotFoundError as exc:
            return {
                "status": "not_found",
                "message": str(exc),
                "requires_confirmation": False,
            }
        except ValueError as exc:
            return {
                "status": "invalid",
                "message": str(exc),
                "requires_confirmation": False,
            }
        if report["status"] != "ok":
            return {
                "status": report["status"],
                "message": report.get("message", "experiment report is unavailable"),
                "requires_confirmation": False,
            }
        draft = build_experiment_review_draft(report)
        external_id = self._save_experiment_review_draft(experiment_id, draft)
        return {
            "status": "saved",
            "message": f"saved experiment review {external_id}",
            "external_id": external_id,
            "experiment_external_id": experiment_id,
            "draft": draft,
            "requires_confirmation": False,
        }

    def _save_experiment_review_draft(self, experiment_id: str, draft: dict[str, Any]) -> str:
        external_id = f"experiment-review-{experiment_id}"
        self.conn.execute(
            """
            insert into experiment_review_drafts (
              external_id, experiment_external_id, content, status
            ) values (?, ?, ?, 'draft')
            on conflict(experiment_external_id) do update set
              content = excluded.content,
              status = 'draft',
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                external_id,
                experiment_id,
                json.dumps(draft, ensure_ascii=False, sort_keys=True),
            ),
        )
        self.conn.commit()
        return external_id

    def _experiment_review_commit(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/experiment-review-commit").strip())
        experiment_id = fields.get("experiment", "").strip()
        review_date = fields.get("date", self._today()).strip()
        if not experiment_id:
            return {
                "status": "invalid",
                "message": "missing fields: experiment",
                "requires_confirmation": False,
            }

        if self._experiment_row(experiment_id) is None:
            return {
                "status": "not_found",
                "message": f"experiment not found: {experiment_id}",
                "requires_confirmation": False,
            }
        draft = self._saved_experiment_review_draft(experiment_id)
        if draft is None:
            draft_response = self._experiment_review(f"/experiment-review experiment={experiment_id}")
            if draft_response["status"] != "saved":
                return draft_response
            draft = draft_response["draft"]
        review_id = f"review-{review_date}"
        summary = draft.get("summary", {})
        risk_codes = [str(flag.get("code", "")) for flag in draft.get("risk_flags", []) if flag.get("code")]
        link_tag = risk_codes[0] if risk_codes else "experiment_review"
        self._upsert_experiment_daily_review(review_id, review_date, summary, risk_codes, draft)
        self._upsert_review_experiment_link(review_id, experiment_id, link_tag)
        card_ids = self._upsert_experiment_review_knowledge(review_id, experiment_id, draft, risk_codes)
        report_response = self._daily_report(f"/daily-report date={review_date}")
        if report_response["status"] != "saved":
            return report_response
        return {
            "status": "saved",
            "message": f"committed experiment review {experiment_id} to learning loop",
            "experiment_external_id": experiment_id,
            "review_external_id": review_id,
            "knowledge_card_count": len(card_ids),
            "learning_report_external_id": report_response["external_id"],
            "draft": draft,
            "requires_confirmation": False,
        }

    def _saved_experiment_review_draft(self, experiment_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            select content
            from experiment_review_drafts
            where experiment_external_id = ?
            """,
            (experiment_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["content"])

    def _upsert_experiment_daily_review(
        self,
        review_id: str,
        review_date: str,
        summary: dict[str, Any],
        risk_codes: list[str],
        draft: dict[str, Any],
    ) -> None:
        symbol = str(summary.get("symbol", "") or "")
        task = next(iter(draft.get("learning_tasks", [])), "")
        question = next(iter(draft.get("review_questions", [])), "")
        lesson = task or question or "Review experiment before changing parameters"
        self.conn.execute(
            """
            insert into daily_reviews (
              external_id, review_date, symbols_watched, trade_count, plan_followed,
              pnl, mistake_tags, emotion_note, lesson
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(external_id) do update set
              review_date = excluded.review_date,
              symbols_watched = excluded.symbols_watched,
              trade_count = excluded.trade_count,
              plan_followed = excluded.plan_followed,
              pnl = excluded.pnl,
              mistake_tags = excluded.mistake_tags,
              emotion_note = excluded.emotion_note,
              lesson = excluded.lesson,
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                review_id,
                review_date,
                json.dumps([symbol] if symbol else [], ensure_ascii=False),
                int(summary.get("trade_count", 0) or 0),
                0 if risk_codes else 1,
                float(summary.get("realized_pnl", 0.0) or 0.0),
                json.dumps(risk_codes, ensure_ascii=False),
                "Experiment review committed by Brain",
                lesson,
            ),
        )
        self.conn.commit()

    def _upsert_review_experiment_link(self, review_id: str, experiment_id: str, tag: str) -> None:
        self.conn.execute(
            """
            insert into review_experiment_links (
              review_external_id, experiment_external_id, tag, note
            ) values (?, ?, ?, ?)
            on conflict(review_external_id, experiment_external_id, tag) do update set
              note = excluded.note
            """,
            (review_id, experiment_id, tag, "Committed from experiment review draft"),
        )
        self.conn.commit()

    def _upsert_experiment_review_knowledge(
        self,
        review_id: str,
        experiment_id: str,
        draft: dict[str, Any],
        risk_codes: list[str],
    ) -> list[str]:
        card_ids: list[str] = []
        tags = risk_codes or ["experiment_review"]
        link_tag = tags[0]
        items: list[tuple[str, str, str]] = []
        for index, question in enumerate(draft.get("review_questions", []), start=1):
            items.append((f"question-{index}", f"Experiment review question {index}", str(question)))
        for index, task in enumerate(draft.get("learning_tasks", []), start=1):
            items.append((f"task-{index}", f"Experiment review task {index}", str(task)))

        for suffix, title, content in items:
            card_id = f"knowledge-experiment-review-{experiment_id}-{suffix}"
            self.conn.execute(
                """
                insert into knowledge_cards (
                  external_id, title, category, content, source
                ) values (?, ?, ?, ?, 'experiment_review')
                on conflict(external_id) do update set
                  title = excluded.title,
                  category = excluded.category,
                  content = excluded.content,
                  source = excluded.source,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (card_id, title, "experiment_review", content),
            )
            for tag in tags:
                self.conn.execute(
                    """
                    insert or ignore into knowledge_card_tags (card_external_id, tag)
                    values (?, ?)
                    """,
                    (card_id, tag),
                )
            self.conn.execute(
                """
                insert or ignore into mistake_knowledge_links (review_external_id, card_external_id, tag)
                values (?, ?, ?)
                """,
                (review_id, card_id, link_tag),
            )
            card_ids.append(card_id)
        self.conn.commit()
        return card_ids

    def _experiment_learning(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/experiment-learning").strip())
        experiment_id = fields.get("experiment", "").strip()
        if not experiment_id:
            return {
                "status": "invalid",
                "message": "missing fields: experiment",
                "requires_confirmation": False,
            }
        result = build_failed_experiment_learning(self.conn, experiment_id)
        if result["status"] == "not_found":
            return {**result, "requires_confirmation": False}
        return {
            **result,
            "message": f"saved failed-experiment learning for {experiment_id}",
            "knowledge_card_count": len(result.get("knowledge_cards", [])),
            "requires_confirmation": False,
        }

    def _daily_report(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/daily-report").strip())
        report_date = fields.get("date", self._today())
        review_row = self._review_row_for_date(report_date)
        if review_row is None:
            return {
                "status": "not_found",
                "message": f"review not found for date: {report_date}",
                "requires_confirmation": False,
            }
        review_id = review_row["external_id"]
        context = self._review_context_payload(review_id, review_row)
        plan = self._plan_for_date(report_date)
        checklists = self._checklists_for_date(report_date)
        focus_tags = context["review"]["mistake_tags"]
        report = {
            "date": report_date,
            "plan": plan,
            "checklists": checklists,
            "review": context["review"],
            "experiments": context["experiments"],
            "knowledge_cards": context["knowledge_cards"],
            "experiment_learning_tasks": self._experiment_learning_tasks(context["experiments"]),
            "summary": {
                "trade_count": context["review"]["trade_count"],
                "pnl": context["review"]["pnl"],
                "plan_followed": context["review"]["plan_followed"],
                "linked_experiment_count": len(context["experiments"]),
                "linked_knowledge_count": len(context["knowledge_cards"]),
                "focus_tags": focus_tags,
            },
            "next_actions": self._next_learning_actions(context),
        }
        external_id = self._save_learning_report("daily", report_date, report_date, report)
        return {
            "status": "saved",
            "message": f"saved learning report {external_id}",
            "external_id": external_id,
            "report_type": "daily",
            "period": {"start": report_date, "end": report_date},
            "report": report,
            "requires_confirmation": False,
        }

    def _weekly_report(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/weekly-report").strip())
        if "start" not in fields or "end" not in fields:
            return {
                "status": "invalid",
                "message": "missing fields: start, end",
                "requires_confirmation": False,
            }
        period_start = fields["start"]
        period_end = fields["end"]
        review_rows = self.conn.execute(
            """
            select external_id, review_date, symbols_watched, trade_count, plan_followed,
                   pnl, mistake_tags, emotion_note, lesson
            from daily_reviews
            where review_date >= ? and review_date <= ?
            order by review_date
            """,
            (period_start, period_end),
        ).fetchall()
        review_payloads = [self._review_payload(row) for row in review_rows]
        tag_counts: dict[str, int] = {}
        linked_experiment_count = 0
        experiment_learning_tasks: list[dict[str, Any]] = []
        for review in review_payloads:
            for tag in review["mistake_tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            linked_experiment_count += self._linked_experiment_count(review["external_id"])
            context = self._review_context_payload(review["external_id"], self._review_row(review["external_id"]))
            experiment_learning_tasks.extend(self._experiment_learning_tasks(context["experiments"]))
        review_count = len(review_payloads)
        trade_count = sum(review["trade_count"] for review in review_payloads)
        pnl = sum(float(review["pnl"]) for review in review_payloads)
        followed_count = sum(1 for review in review_payloads if review["plan_followed"])
        focus_tags = [
            {"tag": tag, "count": count}
            for tag, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        report = {
            "period": {"start": period_start, "end": period_end},
            "reviews": review_payloads,
            "summary": {
                "review_count": review_count,
                "trade_count": trade_count,
                "pnl": pnl,
                "plan_follow_rate": followed_count / review_count if review_count else 0.0,
                "linked_experiment_count": linked_experiment_count,
            },
            "focus_tags": focus_tags,
            "experiment_learning_tasks": experiment_learning_tasks,
            "next_actions": self._weekly_next_actions(review_payloads, focus_tags),
        }
        external_id = self._save_learning_report("weekly", period_start, period_end, report)
        return {
            "status": "saved",
            "message": f"saved learning report {external_id}",
            "external_id": external_id,
            "report_type": "weekly",
            "period": {"start": period_start, "end": period_end},
            "report": report,
            "requires_confirmation": False,
        }

    def _learning_next(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/learning-next").strip())
        report_date = fields.get("date", self._today())
        review_row = self._review_row_for_date(report_date)
        if review_row is None:
            return {
                "status": "not_found",
                "message": f"review not found for date: {report_date}",
                "requires_confirmation": False,
            }
        context = self._review_context_payload(review_row["external_id"], review_row)
        return {
            "status": "ok",
            "date": report_date,
            "tasks": self._next_learning_actions(context),
            "requires_confirmation": False,
        }

    def _learning_queue(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/learning-queue").strip())
        limit = int(fields.get("limit", 10) or 10)
        today = fields.get("today") or fields.get("date")
        return {
            "status": "ok",
            "queue": build_review_queue(self.conn, today=today, limit=limit),
            "requires_confirmation": False,
        }

    def _experiment_learning_tasks(self, experiments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for experiment in experiments:
            result = build_failed_experiment_learning(self.conn, experiment["external_id"])
            if result.get("status") in {"saved", "ok"}:
                tasks.extend(result.get("tasks", []))
        return tasks

    def _coach_next(self, command_text: str) -> dict[str, Any]:
        proposal = build_next_experiment_proposal(self.conn)
        if not proposal["source_experiment_external_id"]:
            return {
                "status": "ok",
                "message": "baseline experiment proposal is ready",
                "proposal": proposal,
                "requires_confirmation": False,
            }
        saved = save_experiment_proposal(self.conn, proposal)
        return {
            "status": "saved",
            "message": f"saved experiment proposal {saved['external_id']}",
            "proposal": saved,
            "requires_confirmation": False,
        }

    def _coach_daily(self) -> dict[str, Any]:
        daily_plan = build_daily_coach_plan(self.conn, allowed_symbols=self.allowed_market_symbols)
        return {
            "status": "ok",
            "daily_plan": daily_plan,
            "message": daily_plan["summary"],
            "requires_confirmation": False,
        }

    def _coach_evaluate(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/coach-evaluate "))
        missing = sorted({"proposal", "experiment"} - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        try:
            outcome = evaluate_experiment_proposal(
                self.conn,
                proposal_id=fields["proposal"],
                experiment_id=fields["experiment"],
            )
        except ValueError as exc:
            return {
                "status": "not_found",
                "message": str(exc),
                "requires_confirmation": False,
            }
        return {
            "status": "saved",
            "message": f"evaluated proposal {fields['proposal']}",
            "outcome": outcome,
            "requires_confirmation": False,
        }

    def _strategy_profile_set(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/strategy-profile-set "))
        required = {"name", "symbol", "interval", "csv"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        symbol = fields["symbol"].upper()
        if symbol not in self.allowed_market_symbols:
            return self._symbol_not_allowed(symbol)
        strategy_name = fields.get("strategy", "moving_average_crossover")
        try:
            parameters = self._strategy_parameters(strategy_name, fields)
        except ValueError:
            return {
                "status": "invalid",
                "message": "numeric strategy profile fields are invalid",
                "requires_confirmation": False,
            }
        profile = save_strategy_profile(
            self.conn,
            name=fields["name"],
            symbol=symbol,
            interval=fields["interval"],
            source_csv=fields["csv"],
            parameters=parameters,
            strategy_name=strategy_name,
            description=self._display_value(fields.get("description", "")),
        )
        return {
            "status": "saved",
            "message": f"saved strategy profile {profile['name']}",
            "profile": profile,
            "requires_confirmation": False,
        }

    def _strategy_parameters(self, strategy_name: str, fields: dict[str, str]) -> dict[str, Any]:
        normalized = strategy_name.strip().lower()
        if normalized in {"moving_average_crossover", "ma_cross", "ma"}:
            if "short" not in fields or "long" not in fields:
                raise ValueError("missing moving average windows")
            return {
                "short_window": int(fields["short"]),
                "long_window": int(fields["long"]),
                "quote_amount": float(fields.get("quote_amount", "100")),
            }
        if normalized == "breakout":
            return {
                "lookback": int(fields.get("lookback", "20")),
                "quote_amount": float(fields.get("quote_amount", "100")),
            }
        if normalized == "mean_reversion":
            return {
                "window": int(fields.get("window", "20")),
                "threshold_pct": float(fields.get("threshold_pct", "0.03")),
                "quote_amount": float(fields.get("quote_amount", "100")),
            }
        if normalized == "volatility_filter":
            return {
                "short_window": int(fields.get("short", fields.get("short_window", "20"))),
                "long_window": int(fields.get("long", fields.get("long_window", "60"))),
                "min_range_pct": float(fields.get("min_range_pct", "0.01")),
                "quote_amount": float(fields.get("quote_amount", "100")),
            }
        raise ValueError("unknown strategy")

    def _strategy_profile_list(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/strategy-profile-list").strip())
        try:
            limit = int(fields.get("limit", "20"))
        except ValueError:
            return {
                "status": "invalid",
                "message": "limit must be an integer",
                "requires_confirmation": False,
            }
        return {
            "status": "ok",
            "profiles": list_strategy_profiles(self.conn, limit=limit),
            "requires_confirmation": False,
        }

    def _sweep_ma(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/sweep-ma "))
        required = {"csv", "symbol", "shorts", "longs"}
        missing = sorted(required - fields.keys())
        if missing:
            return {
                "status": "invalid",
                "message": f"missing fields: {', '.join(missing)}",
                "requires_confirmation": False,
            }
        symbol = fields["symbol"].upper()
        if symbol not in self.allowed_market_symbols:
            return self._symbol_not_allowed(symbol)
        try:
            sweep = run_ma_parameter_sweep(
                self.conn,
                symbol=symbol,
                interval=fields.get("interval", ""),
                source_csv=self._safe_data_local_path(fields["csv"]),
                source_csv_text=fields["csv"],
                shorts=[int(value) for value in self._csv_values(fields["shorts"])],
                longs=[int(value) for value in self._csv_values(fields["longs"])],
                starting_cash=float(fields.get("starting_cash", "1000")),
                quote_amount=float(fields.get("quote_amount", "100")),
                fee_rate=float(fields.get("fee", "0.001")),
                daily_limit=int(fields.get("daily_limit", "5")),
            )
        except ValueError as exc:
            return {
                "status": "invalid",
                "message": str(exc),
                "requires_confirmation": False,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "message": str(exc),
                "requires_confirmation": False,
            }
        return {
            "status": "saved",
            "message": f"saved parameter sweep {sweep['external_id']}",
            "sweep": sweep,
            "requires_confirmation": False,
        }

    def _experiment_decision(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/experiment-decision ").strip())
        required = {"experiment", "decision"}
        missing = sorted(required - fields.keys())
        if missing:
            return {"status": "invalid", "message": f"missing fields: {', '.join(missing)}", "requires_confirmation": False}
        try:
            decision = save_experiment_decision(
                self.conn,
                experiment=fields["experiment"],
                decision=fields["decision"],
                reason=self._display_value(fields.get("reason", "")),
            )
        except ValueError as exc:
            return {"status": "invalid", "message": str(exc), "requires_confirmation": False}
        return {
            "status": "saved",
            "message": f"saved decision {decision['decision']} for {decision['experiment_external_id']}",
            "decision": decision,
            "requires_confirmation": False,
        }

    def _hypothesis_create(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/hypothesis-create ").strip())
        try:
            card = HypothesisLog(self.conn).create(
                title=self._display_value(fields.get("title", "Untitled_hypothesis")),
                description=self._display_value(fields.get("description", "")),
                parent_iteration=fields.get("parent_iteration", "baseline"),
                change_summary=self._display_value(fields.get("change_summary", "")),
                predicted=self._json_field(fields.get("predicted", "{}"), "predicted"),
                decision_rule=self._display_value(fields.get("decision_rule", "Keep_only_if_preregistered_rule_passes")),
            )
        except ValueError as exc:
            return {"status": "invalid", "message": str(exc), "requires_confirmation": False}
        return {
            "status": "saved",
            "message": f"saved hypothesis {card.hypothesis_id}",
            "hypothesis": self._hypothesis_payload(card),
            "requires_confirmation": False,
        }

    def _hypothesis_resolve(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/hypothesis-resolve ").strip())
        hypothesis_id = fields.get("hypothesis", fields.get("id", "")).strip()
        if not hypothesis_id:
            return {"status": "invalid", "message": "hypothesis is required", "requires_confirmation": False}
        try:
            card = HypothesisLog(self.conn).resolve(
                hypothesis_id,
                actual=self._json_field(fields.get("actual", "{}"), "actual"),
                decision=fields.get("decision", ""),
                reason=self._display_value(fields.get("reason", "")),
                hindsight_notes=self._display_value(fields.get("hindsight_notes", "")),
                code_commit=fields.get("code_commit", ""),
                backtest_run_id=fields.get("backtest_run_id", ""),
            )
        except ValueError as exc:
            return {"status": "invalid", "message": str(exc), "requires_confirmation": False}
        return {
            "status": "saved",
            "message": f"resolved hypothesis {card.hypothesis_id} as {card.decision}",
            "hypothesis": self._hypothesis_payload(card),
            "requires_confirmation": False,
        }

    def _hypothesis_list(self) -> dict[str, Any]:
        cards = HypothesisLog(self.conn).list()
        return {
            "status": "ok",
            "hypotheses": [self._hypothesis_payload(card) for card in cards],
            "requires_confirmation": False,
        }

    def _research_status(self) -> dict[str, Any]:
        cards = HypothesisLog(self.conn).list()
        decisions = {key: 0 for key in ("kept", "rejected", "inconclusive", "risk_reduction_kept")}
        unresolved = 0
        for card in cards:
            if card.decision in decisions:
                decisions[card.decision] += 1
            else:
                unresolved += 1
        return {
            "status": "ok",
            "total": len(cards),
            "unresolved": unresolved,
            "decisions": decisions,
            "requires_confirmation": False,
        }

    def _research_baseline(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/research-baseline").strip())
        return self._research_run_phase(fields, phase="6.1", hypothesis_id="H-100")

    def _research_test(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/research-test").strip())
        hypothesis_id = fields.get("hypothesis", "H-101")
        phase = fields.get("phase", _phase_for_hypothesis(hypothesis_id))
        return self._research_run_phase(fields, phase=phase, hypothesis_id=hypothesis_id)

    def _research_ablation(self, command_text: str) -> dict[str, Any]:
        fields = self._parse_key_value_args(command_text.removeprefix("/research-ablation").strip())
        runs = []
        for hypothesis_id, phase in (
            ("H-100", "6.1"),
            ("H-101", "6.2"),
            ("H-102", "6.3"),
            ("H-103", "6.4"),
            ("H-104", "6.5"),
            ("H-105", "6.6"),
        ):
            result = self._research_run_phase(fields, phase=phase, hypothesis_id=hypothesis_id)
            if result["status"] != "ok":
                return result
            runs.append(result["run"])
        return {"status": "ok", "runs": runs, "requires_confirmation": False}

    def _research_run_phase(self, fields: dict[str, str], *, phase: str, hypothesis_id: str) -> dict[str, Any]:
        csv_value = fields.get("csv", "data/local/market_data/BTCUSDT/BTCUSDT-1h.csv")
        try:
            csv_path = self._safe_data_local_path(csv_value)
            frame = pd.read_csv(csv_path)
            config = WalkForwardConfig(
                train_window_days=int(fields.get("train_days", "7")),
                test_window_days=int(fields.get("test_days", "5")),
                step_days=int(fields.get("step_days", "5")),
                purge_days=int(fields.get("purge_days", "1")),
            )
            result = run_walk_forward(
                mtf_trend_strategy_factory,
                frame,
                config,
                param_grid={
                    "phase": [phase],
                    "ema_short": [int(fields.get("ema_short", "20"))],
                    "ema_long": [int(fields.get("ema_long", "200"))],
                },
            )
        except (ValueError, FileNotFoundError) as exc:
            return {"status": "invalid", "message": str(exc), "requires_confirmation": False}
        metrics = dict(result.aggregate_metrics)
        metrics["windows"] = len(result.windows)
        metrics["consistency_score"] = result.consistency_score
        return {
            "status": "ok",
            "run": {
                "hypothesis_id": hypothesis_id,
                "phase": phase,
                "source_csv": csv_value,
                "metrics": metrics,
            },
            "requires_confirmation": False,
        }

    @staticmethod
    def _hypothesis_payload(card) -> dict[str, Any]:
        return {
            "hypothesis_id": card.hypothesis_id,
            "title": card.title,
            "predicted": card.predicted,
            "actual": card.actual,
            "decision": card.decision,
            "reason": card.reason,
        }

    @staticmethod
    def _json_field(value: str, label: str) -> dict[str, Any]:
        parsed = json.loads(value)
        if not isinstance(parsed, dict) or not parsed:
            raise ValueError(f"{label} must be a non-empty JSON object")
        return parsed

    def _save_learning_report(
        self,
        report_type: str,
        period_start: str,
        period_end: str,
        content: dict[str, Any],
    ) -> str:
        external_id = f"learning-report-{report_type}-{period_start}"
        if period_end != period_start:
            external_id = f"{external_id}-{period_end}"
        self.conn.execute(
            """
            insert into learning_reports (
              external_id, report_type, period_start, period_end, content
            ) values (?, ?, ?, ?, ?)
            on conflict(report_type, period_start, period_end) do update set
              content = excluded.content,
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                external_id,
                report_type,
                period_start,
                period_end,
                json.dumps(content, ensure_ascii=False, sort_keys=True),
            ),
        )
        self.conn.commit()
        return external_id

    def _next_learning_actions(self, context: dict[str, Any]) -> list[str]:
        actions: list[str] = []
        for card in context["knowledge_cards"]:
            actions.append(f"Review knowledge card: {card['title']}")
        for experiment in context["experiments"]:
            actions.append(f"Replay linked experiment: {experiment['external_id']}")
        for tag in context["review"]["mistake_tags"]:
            actions.append(f"Prepare next plan with focus tag: {tag}")
        if not actions:
            actions.append("Write a short review before the next trading session")
        return actions

    @staticmethod
    def _weekly_next_actions(reviews: list[dict[str, Any]], focus_tags: list[dict[str, Any]]) -> list[str]:
        actions: list[str] = []
        if any(not review["plan_followed"] for review in reviews):
            actions.append("Prioritize plan adherence in the next trading day")
        for item in focus_tags[:3]:
            actions.append(f"Review weekly focus tag: {item['tag']}")
        if not actions:
            actions.append("Keep current process and collect more review samples")
        return actions

    def _linked_experiment_count(self, review_id: str) -> int:
        return int(
            self.conn.execute(
                "select count(*) from review_experiment_links where review_external_id = ?",
                (review_id,),
            ).fetchone()[0]
        )

    def _insert_trades(self, trades: list[Any], source: str) -> None:
        self.conn.executemany(
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
            "/experiment-link ",
            "/experiment-review-commit ",
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
                "/experiment-link",
                "/review-context",
                "/history-download",
                "/market-refresh",
                "/backtest-ma",
                "/experiment-summary",
                "/experiment-review",
                "/experiment-review-commit",
                "/daily-report",
                "/weekly-report",
                "/learning-next",
            ],
        }

    def _execution_block(self, symbol: str) -> dict[str, Any] | None:
        context = self._execution_context(symbol)
        return context.get("block")

    def _execution_context(self, symbol: str) -> dict[str, Any]:
        plan = self._plan_for_date(self._today())
        if plan is None:
            return {"block": {
                    "status": "blocked",
                    "message": "today's trading plan is missing",
                    "requires_confirmation": False,
                }}
        if symbol not in plan["symbols"]:
            return {"block": {
                    "status": "blocked",
                    "message": f"{symbol} is not in today's plan",
                    "requires_confirmation": False,
                }}
        row = self.conn.execute(
            """
            select external_id, plan_ok, setup_ok, risk_ok, emotion_ok
            from pre_trade_checklists
            where checklist_date = ? and symbol = ?
            order by id desc
            limit 1
            """,
            (self._today(), symbol),
        ).fetchone()
        if row is None:
            return {"block": {
                    "status": "blocked",
                    "message": f"pre-trade checklist is missing for {symbol}",
                    "requires_confirmation": False,
                }}
        if not all(bool(row[key]) for key in ("plan_ok", "setup_ok", "risk_ok", "emotion_ok")):
            return {"block": {
                    "status": "blocked",
                    "message": f"pre-trade checklist is not fully approved for {symbol}",
                    "requires_confirmation": False,
                }}
        return {
            "plan_external_id": plan["external_id"],
            "checklist_external_id": row["external_id"],
        }

    def _experiment_decision_value(self, experiment_id: str) -> str:
        row = self.conn.execute(
            "select decision from experiment_decisions where experiment_external_id = ?",
            (experiment_id,),
        ).fetchone()
        return str(row["decision"]) if row is not None else ""

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

    def _review_row(self, external_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            """
            select external_id, review_date, symbols_watched, trade_count, plan_followed,
                   pnl, mistake_tags, emotion_note, lesson
            from daily_reviews
            where external_id = ?
            """,
            (external_id,),
        ).fetchone()

    def _review_row_for_date(self, review_date: str) -> sqlite3.Row | None:
        return self.conn.execute(
            """
            select external_id, review_date, symbols_watched, trade_count, plan_followed,
                   pnl, mistake_tags, emotion_note, lesson
            from daily_reviews
            where review_date = ?
            """,
            (review_date,),
        ).fetchone()

    def _checklists_for_date(self, checklist_date: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            select symbol, plan_ok, setup_ok, risk_ok, emotion, emotion_ok, created_at
            from pre_trade_checklists
            where checklist_date = ?
            order by id
            """,
            (checklist_date,),
        ).fetchall()
        return [
            {
                "symbol": row["symbol"],
                "plan_ok": bool(row["plan_ok"]),
                "setup_ok": bool(row["setup_ok"]),
                "risk_ok": bool(row["risk_ok"]),
                "emotion": row["emotion"],
                "emotion_ok": bool(row["emotion_ok"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _experiment_row(self, external_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            """
            select external_id, strategy_name, symbol, interval
            from strategy_experiments
            where external_id = ?
            """,
            (external_id,),
        ).fetchone()

    def _review_context_payload(self, review_id: str, review_row: sqlite3.Row) -> dict[str, Any]:
        experiment_rows = self.conn.execute(
            """
            select e.external_id, e.strategy_name, e.symbol, e.interval, e.parameters, e.metrics,
                   l.tag as link_tag, l.note as link_note
            from review_experiment_links l
            join strategy_experiments e on e.external_id = l.experiment_external_id
            where l.review_external_id = ?
            order by l.id
            """,
            (review_id,),
        ).fetchall()
        knowledge_rows = self.conn.execute(
            """
            select k.external_id, k.title, k.category, k.content, l.tag as link_tag
            from mistake_knowledge_links l
            join knowledge_cards k on k.external_id = l.card_external_id
            where l.review_external_id = ?
            order by l.id
            """,
            (review_id,),
        ).fetchall()
        return {
            "review": self._review_payload(review_row),
            "experiments": [
                {
                    "external_id": row["external_id"],
                    "strategy_name": row["strategy_name"],
                    "symbol": row["symbol"],
                    "interval": row["interval"],
                    "parameters": json.loads(row["parameters"]),
                    "metrics": json.loads(row["metrics"]),
                    "link_tag": row["link_tag"],
                    "link_note": row["link_note"],
                }
                for row in experiment_rows
            ],
            "knowledge_cards": [
                {
                    "external_id": row["external_id"],
                    "title": row["title"],
                    "category": row["category"],
                    "content": row["content"],
                    "link_tag": row["link_tag"],
                }
                for row in knowledge_rows
            ],
        }

    @staticmethod
    def _review_payload(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "external_id": row["external_id"],
            "review_date": row["review_date"],
            "symbols_watched": json.loads(row["symbols_watched"]),
            "trade_count": row["trade_count"],
            "plan_followed": bool(row["plan_followed"]),
            "pnl": row["pnl"],
            "mistake_tags": json.loads(row["mistake_tags"]),
            "emotion_note": row["emotion_note"],
            "lesson": row["lesson"],
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

    def _symbol_not_allowed(self, symbol: str) -> dict[str, Any]:
        return {
            "status": "invalid",
            "message": f"symbol not allowed: {symbol}. allowed: {', '.join(self.allowed_market_symbols)}",
            "requires_confirmation": False,
        }

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
    def _optional_int(value: str | None) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    @staticmethod
    def _safe_data_local_path(value: str) -> Path:
        path = Path(value.replace("\\", "/"))
        allowed_root = Path("data/local").resolve()
        resolved = path.resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError as exc:
            raise ValueError("path must be under data/local") from exc
        return path

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()


def _phase_for_hypothesis(hypothesis_id: str) -> str:
    return {
        "H-100": "6.1",
        "H-101": "6.2",
        "H-102": "6.3",
        "H-103": "6.4",
        "H-104": "6.5",
        "H-105": "6.6",
    }.get(hypothesis_id, "6.1")
