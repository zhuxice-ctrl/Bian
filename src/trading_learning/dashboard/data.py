from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_learning.backtest.report import build_backtest_report
from trading_learning.config import DEFAULT_ALLOWED_SYMBOLS
from trading_learning.learning.experiment_review import build_experiment_review_draft
from trading_learning.learning.daily_coach import build_daily_coach_plan
from trading_learning.market_data.catalog import inventory_datasets
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.models import BacktestResult, Side, Trade
from trading_learning.ops import build_local_health
from trading_learning.production_gate import production_readiness_status
from trading_learning.workspace import build_workspace_state


class DashboardData:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        allowed_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
    ) -> None:
        self.conn = conn
        self.allowed_symbols = allowed_symbols

    def overview(self) -> dict[str, Any]:
        review = self.conn.execute(
            """
            select
              count(*) as review_days,
              coalesce(sum(trade_count), 0) as review_trade_count,
              coalesce(sum(pnl), 0) as review_pnl,
              coalesce(avg(plan_followed), 0) as plan_follow_rate
            from daily_reviews
            """
        ).fetchone()
        experiment_count = self.conn.execute("select count(*) from strategy_experiments").fetchone()[0]
        knowledge_count = self.conn.execute("select count(*) from knowledge_cards where status = 'active'").fetchone()[0]
        pending_suggestions = self.conn.execute(
            "select count(*) from brain_suggested_commands where status = 'pending'"
        ).fetchone()[0]
        return {
            "status": "ok",
            "totals": {
                "review_days": int(review["review_days"]),
                "review_trade_count": int(review["review_trade_count"]),
                "review_pnl": float(review["review_pnl"]),
                "plan_follow_rate": float(review["plan_follow_rate"]),
                "experiment_count": int(experiment_count),
                "knowledge_count": int(knowledge_count),
                "pending_suggestions": int(pending_suggestions),
            },
            "workspace_state": build_workspace_state(self.conn),
            "recent_reviews": self.reviews(limit=5)["reviews"],
            "recent_experiments": self.experiments(limit=5)["experiments"],
        }

    def reviews(self, *, limit: int = 20) -> dict[str, Any]:
        rows = self.conn.execute(
            """
            select external_id, review_date, symbols_watched, trade_count, plan_followed,
                   pnl, mistake_tags, emotion_note, lesson
            from daily_reviews
            order by review_date desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return {"status": "ok", "reviews": [self._review(row) for row in rows]}

    def experiments(self, *, limit: int = 20) -> dict[str, Any]:
        rows = self.conn.execute(
            """
            select external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note, created_at
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
                    "parameters": self._json(row["parameters"], {}),
                    "metrics": self._json(row["metrics"], {}),
                    "note": row["note"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ],
        }

    def knowledge(self, *, limit: int = 30) -> dict[str, Any]:
        rows = self.conn.execute(
            """
            select external_id, title, category, content, source, status, created_at
            from knowledge_cards
            order by id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
        return {
            "status": "ok",
            "cards": [
                {
                    "external_id": row["external_id"],
                    "title": row["title"],
                    "category": row["category"],
                    "content": row["content"],
                    "source": row["source"],
                    "status": row["status"],
                    "tags": self._tags_for_card(row["external_id"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ],
        }

    def reports(self, *, report_type: str | None = None, limit: int = 50) -> dict[str, Any]:
        params: tuple[Any, ...]
        where = ""
        if report_type in {"daily", "weekly"}:
            where = "where report_type = ?"
            params = (report_type, limit)
        else:
            params = (limit,)
        rows = self.conn.execute(
            f"""
            select external_id, report_type, period_start, period_end, content, created_at, updated_at
            from learning_reports
            {where}
            order by period_end desc, id desc
            limit ?
            """,
            params,
        ).fetchall()
        return {
            "status": "ok",
            "reports": [
                {
                    "external_id": row["external_id"],
                    "report_type": row["report_type"],
                    "period_start": row["period_start"],
                    "period_end": row["period_end"],
                    "content": self._json(row["content"], {}),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ],
        }

    def control_console(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "health": build_local_health(self._database_path()),
            "workspace_state": build_workspace_state(self.conn),
            "tasks": self._recent_remote_tasks(limit=8),
            "coach": {
                "daily_plan": build_daily_coach_plan(self.conn, allowed_symbols=self.allowed_symbols),
                "proposals": self._recent_experiment_proposals(limit=5),
                "next_review_actions": self._next_review_actions(limit=5),
            },
            "strategy_lab": {
                "profiles": self._strategy_profiles(limit=5),
                "sweeps": self._parameter_sweeps(limit=5),
                "decisions": self._experiment_decisions(limit=8),
            },
            "testnet": {
                "orders": self._testnet_orders(limit=5),
            },
            "production_gate": production_readiness_status(),
            "references": [
                {
                    "project": "Freqtrade",
                    "lesson": "Use explicit REST-like status, task, and control surfaces instead of hiding state in logs.",
                },
                {
                    "project": "Jesse",
                    "lesson": "Keep strategy research, backtesting, and execution workflows separated.",
                },
                {
                    "project": "vectorbt",
                    "lesson": "Treat parameter sweeps as research data and surface overfitting warnings.",
                },
            ],
        }

    def datasets(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "datasets": inventory_datasets(allowed_symbols=self.allowed_symbols),
        }

    def run_backtest_ma_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        from trading_learning.actions import run_local_ma_backtest_action

        return run_local_ma_backtest_action(self.conn, payload, allowed_symbols=self.allowed_symbols)

    def persist_experiment_review_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        from trading_learning.actions import persist_experiment_review_action

        return persist_experiment_review_action(self.conn, payload, allowed_symbols=self.allowed_symbols)

    def commit_experiment_review_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        from trading_learning.actions import commit_experiment_review_action

        return commit_experiment_review_action(self.conn, payload, allowed_symbols=self.allowed_symbols)

    def _recent_remote_tasks(self, *, limit: int) -> list[dict[str, Any]]:
        try:
            rows = self.conn.execute(
                """
                select external_id, requester_user_id, command_text, task_type, risk_level,
                       state, runner_id, result_summary, error_message, created_at, updated_at
                from remote_tasks
                order by id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [dict(row) for row in rows]

    def _recent_experiment_proposals(self, *, limit: int) -> list[dict[str, Any]]:
        try:
            rows = self.conn.execute(
                """
                select external_id, source_experiment_external_id, content, status, outcome, created_at, updated_at
                from experiment_proposals
                order by id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        proposals = []
        for row in rows:
            content = self._json(row["content"], {})
            proposals.append(
                {
                    "external_id": row["external_id"],
                    "source_experiment_external_id": row["source_experiment_external_id"],
                    "status": row["status"],
                    "hypothesis": content.get("hypothesis", {}),
                    "suggested_command": content.get("suggested_command", ""),
                    "outcome": self._json(row["outcome"], {}),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return proposals

    def _next_review_actions(self, *, limit: int) -> list[dict[str, str]]:
        try:
            rows = self.conn.execute(
                """
                select e.external_id, e.symbol, e.interval, e.created_at
                from strategy_experiments e
                left join experiment_review_drafts d on d.experiment_external_id = e.external_id
                where d.external_id is null
                order by e.id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [
            {
                "experiment_external_id": row["external_id"],
                "title": f"Review {row['symbol']} {row['interval']} experiment",
                "command": f"/experiment-review experiment={row['external_id']}",
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _strategy_profiles(self, *, limit: int) -> list[dict[str, Any]]:
        try:
            rows = self.conn.execute(
                """
                select external_id, name, strategy_name, symbol, interval, source_csv, parameters, description, updated_at
                from strategy_profiles
                order by id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [
            {
                "external_id": row["external_id"],
                "name": row["name"],
                "strategy_name": row["strategy_name"],
                "symbol": row["symbol"],
                "interval": row["interval"],
                "source_csv": row["source_csv"],
                "parameters": self._json(row["parameters"], {}),
                "description": row["description"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def _parameter_sweeps(self, *, limit: int) -> list[dict[str, Any]]:
        try:
            rows = self.conn.execute(
                """
                select external_id, strategy_name, symbol, interval, source_csv, grid, result, created_at
                from parameter_sweeps
                order by id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        sweeps = []
        for row in rows:
            result = self._json(row["result"], {})
            sweeps.append(
                {
                    "external_id": row["external_id"],
                    "strategy_name": row["strategy_name"],
                    "symbol": row["symbol"],
                    "interval": row["interval"],
                    "source_csv": row["source_csv"],
                    "grid": self._json(row["grid"], {}),
                    "run_count": result.get("run_count", 0),
                    "best_experiment": result.get("best_experiment", ""),
                    "overfitting_warning": result.get("overfitting_warning", ""),
                    "created_at": row["created_at"],
                }
            )
        return sweeps

    def _experiment_decisions(self, *, limit: int) -> list[dict[str, Any]]:
        try:
            rows = self.conn.execute(
                """
                select experiment_external_id, decision, reason, created_at, updated_at
                from experiment_decisions
                order by updated_at desc, id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [dict(row) for row in rows]

    def _testnet_orders(self, *, limit: int) -> list[dict[str, Any]]:
        try:
            rows = self.conn.execute(
                """
                select external_id, user_id, action, symbol, side, order_type, order_id, status, created_at
                from testnet_order_records
                order by id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [dict(row) for row in rows]

    def backtest_report(self, experiment_id: str) -> dict[str, Any]:
        replay = self.kline_replay(experiment_id, limit=5000)
        if replay["status"] != "ok":
            return replay
        trades = tuple(self._trade_model(trade) for trade in replay["trades"])
        metrics = replay["experiment"].get("metrics", {})
        parameters = replay["experiment"].get("parameters", {})
        starting_cash = float(parameters.get("starting_cash", 0.0))
        ending_cash = float(metrics.get("ending_cash", starting_cash + float(metrics.get("realized_pnl", 0.0))))
        position_quantity = float(metrics.get("position_quantity", 0.0))
        result = BacktestResult(
            symbol=replay["experiment"]["symbol"],
            starting_cash=starting_cash,
            ending_cash=ending_cash,
            position_quantity=position_quantity,
            trade_count=len(trades),
            trades=trades,
        )
        report = build_backtest_report(result)
        enriched_trades = self._annotated_trades(replay["trades"], report["round_trips"])
        return {
            "status": "ok",
            "experiment": replay["experiment"],
            "metrics": report["metrics"],
            "trades": enriched_trades,
            "round_trips": report["round_trips"],
            "equity_curve": report["equity_curve"],
            "filter_options": self._filter_options(enriched_trades, report["round_trips"], experiment_id),
        }

    def experiment_comparison(self, experiment_ids: list[str]) -> dict[str, Any]:
        clean_ids = [experiment_id for experiment_id in experiment_ids if experiment_id]
        if not clean_ids:
            return {"status": "ok", "experiments": [], "metric_keys": [], "parameter_keys": []}
        placeholders = ",".join("?" for _ in clean_ids)
        rows = self.conn.execute(
            f"""
            select external_id, strategy_name, symbol, interval, parameters, metrics, note, created_at
            from strategy_experiments
            where external_id in ({placeholders})
            """,
            tuple(clean_ids),
        ).fetchall()
        rows_by_id = {row["external_id"]: row for row in rows}
        experiments = []
        metric_keys: set[str] = set()
        parameter_keys: set[str] = set()
        for experiment_id in clean_ids:
            row = rows_by_id.get(experiment_id)
            if row is None:
                continue
            parameters = self._json(row["parameters"], {})
            metrics = self._json(row["metrics"], {})
            parameter_keys.update(parameters.keys())
            metric_keys.update(metrics.keys())
            experiments.append(
                {
                    "external_id": row["external_id"],
                    "strategy_name": row["strategy_name"],
                    "symbol": row["symbol"],
                    "interval": row["interval"],
                    "parameters": parameters,
                    "metrics": metrics,
                    "note": row["note"],
                    "created_at": row["created_at"],
                }
            )
        preferred_metric_order = ["realized_pnl", "trade_count", "win_rate", "max_drawdown", "total_fees"]
        ordered_metrics = [key for key in preferred_metric_order if key in metric_keys]
        ordered_metrics.extend(sorted(metric_keys - set(ordered_metrics)))
        return {
            "status": "ok",
            "experiments": experiments,
            "metric_keys": ordered_metrics,
            "parameter_keys": sorted(parameter_keys),
        }

    def experiment_review(self, experiment_id: str) -> dict[str, Any]:
        try:
            row = self.conn.execute(
                """
                select external_id, experiment_external_id, content, status, created_at, updated_at
                from experiment_review_drafts
                where experiment_external_id = ?
                """,
                (experiment_id,),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            if "experiment_review_drafts" not in str(exc):
                raise
            row = None
        if row is not None:
            return {
                "status": "ok",
                "persisted": True,
                "external_id": row["external_id"],
                "experiment_external_id": row["experiment_external_id"],
                "draft_status": row["status"],
                "draft": self._json(row["content"], {}),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

        report = self.backtest_report(experiment_id)
        if report["status"] != "ok":
            return report
        return {
            "status": "generated",
            "persisted": False,
            "external_id": f"experiment-review-{experiment_id}",
            "experiment_external_id": experiment_id,
            "draft_status": "draft",
            "draft": build_experiment_review_draft(report),
        }

    def kline(self, *, csv_path: str, symbol: str, limit: int = 300) -> dict[str, Any]:
        path = self._safe_data_local_path(csv_path)
        candles = load_candles_csv(path, symbol.upper())
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "source_csv": csv_path,
            "candles": [self._candle(candle) for candle in candles[-limit:]],
            "trades": [],
        }

    def kline_replay(self, experiment_id: str, *, limit: int = 300) -> dict[str, Any]:
        row = self.conn.execute(
            """
            select external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
            from strategy_experiments
            where external_id = ?
            """,
            (experiment_id,),
        ).fetchone()
        if row is None:
            return {"status": "not_found", "message": f"experiment not found: {experiment_id}"}
        kline = self.kline(csv_path=row["source_csv"], symbol=row["symbol"], limit=limit)
        if kline["status"] != "ok":
            return kline
        trades = self.conn.execute(
            """
            select external_id, symbol, side, quantity, price, fee, timestamp, reason
            from trades
            where source = ?
            order by timestamp
            """,
            (experiment_id,),
        ).fetchall()
        kline["experiment"] = {
            "external_id": row["external_id"],
            "strategy_name": row["strategy_name"],
            "symbol": row["symbol"],
            "interval": row["interval"],
            "source_csv": row["source_csv"],
            "parameters": self._json(row["parameters"], {}),
            "metrics": self._json(row["metrics"], {}),
            "note": row["note"],
        }
        kline["trades"] = [
            {
                "external_id": trade["external_id"],
                "symbol": trade["symbol"],
                "side": trade["side"],
                "quantity": float(trade["quantity"]),
                "price": float(trade["price"]),
                "fee": float(trade["fee"]),
                "timestamp": trade["timestamp"],
                "reason": trade["reason"],
            }
            for trade in trades
        ]
        return kline

    def _annotated_trades(self, trades: list[dict[str, Any]], round_trips: list[dict[str, Any]]) -> list[dict[str, Any]]:
        trip_by_trade_id: dict[str, dict[str, Any]] = {}
        for trip in round_trips:
            result = "win" if float(trip.get("pnl", 0.0) or 0.0) >= 0 else "loss"
            for key in ("entry_trade_id", "exit_trade_id"):
                trade_id = str(trip.get(key, "") or "")
                if trade_id:
                    trip_by_trade_id[trade_id] = {
                        "round_trip_result": result,
                        "round_trip_pnl": float(trip.get("pnl", 0.0) or 0.0),
                        "round_trip_pnl_pct": float(trip.get("pnl_pct", 0.0) or 0.0),
                    }
        annotated = []
        for trade in trades:
            extra = trip_by_trade_id.get(
                trade["external_id"],
                {"round_trip_result": "open", "round_trip_pnl": 0.0, "round_trip_pnl_pct": 0.0},
            )
            annotated.append({**trade, **extra})
        return annotated

    def _filter_options(
        self,
        trades: list[dict[str, Any]],
        round_trips: list[dict[str, Any]],
        experiment_id: str,
    ) -> dict[str, Any]:
        timestamps = [trade["timestamp"] for trade in trades]
        return {
            "sides": [side for side in ("BUY", "SELL") if any(trade["side"] == side for trade in trades)],
            "results": [
                result
                for result in ("win", "loss", "open")
                if any(trade["round_trip_result"] == result for trade in trades)
            ],
            "risk_flags": self._experiment_risk_flags(experiment_id),
            "start_time": min(timestamps) if timestamps else "",
            "end_time": max(timestamps) if timestamps else "",
        }

    def _experiment_risk_flags(self, experiment_id: str) -> list[str]:
        try:
            row = self.conn.execute(
                "select content from experiment_review_drafts where experiment_external_id = ?",
                (experiment_id,),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            if "experiment_review_drafts" not in str(exc):
                raise
            return []
        if row is None:
            return []
        content = self._json(row["content"], {})
        return sorted(
            str(flag.get("code", ""))
            for flag in content.get("risk_flags", [])
            if isinstance(flag, dict) and flag.get("code")
        )

    def _tags_for_card(self, card_external_id: str) -> list[str]:
        rows = self.conn.execute(
            "select tag from knowledge_card_tags where card_external_id = ? order by tag",
            (card_external_id,),
        ).fetchall()
        return [row["tag"] for row in rows]

    @staticmethod
    def _review(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "external_id": row["external_id"],
            "review_date": row["review_date"],
            "symbols_watched": DashboardData._json(row["symbols_watched"], []),
            "trade_count": int(row["trade_count"]),
            "plan_followed": bool(row["plan_followed"]),
            "pnl": float(row["pnl"]),
            "mistake_tags": DashboardData._json(row["mistake_tags"], []),
            "emotion_note": row["emotion_note"],
            "lesson": row["lesson"],
        }

    @staticmethod
    def _candle(candle: Any) -> dict[str, Any]:
        return {
            "opened_at": candle.opened_at.isoformat(),
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": float(candle.volume),
        }

    @staticmethod
    def _trade_model(trade: dict[str, Any]) -> Trade:
        return Trade(
            external_id=trade["external_id"],
            symbol=trade["symbol"],
            side=Side(trade["side"]),
            quantity=float(trade["quantity"]),
            price=float(trade["price"]),
            fee=float(trade["fee"]),
            timestamp=datetime.fromisoformat(trade["timestamp"]),
            reason=trade["reason"],
        )

    @staticmethod
    def _json(value: str, fallback: Any) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback

    def _database_path(self) -> Path:
        row = self.conn.execute("pragma database_list").fetchone()
        if row is None or not row["file"]:
            return Path(":memory:")
        return Path(row["file"])

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
