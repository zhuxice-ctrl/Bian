from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_learning.backtest.report import build_backtest_report
from trading_learning.config import DEFAULT_ALLOWED_SYMBOLS
from trading_learning.learning.experiment_review import build_experiment_review_draft
from trading_learning.market_data.catalog import inventory_datasets
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.models import BacktestResult, Side, Trade


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

    def datasets(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "datasets": inventory_datasets(allowed_symbols=self.allowed_symbols),
        }

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
        return {
            "status": "ok",
            "experiment": replay["experiment"],
            "metrics": report["metrics"],
            "trades": replay["trades"],
            "round_trips": report["round_trips"],
            "equity_curve": report["equity_curve"],
        }

    def experiment_review(self, experiment_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """
            select external_id, experiment_external_id, content, status, created_at, updated_at
            from experiment_review_drafts
            where experiment_external_id = ?
            """,
            (experiment_id,),
        ).fetchone()
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

    @staticmethod
    def _safe_data_local_path(value: str) -> Path:
        path = Path(value)
        allowed_root = Path("data/local").resolve()
        resolved = path.resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError as exc:
            raise ValueError("path must be under data/local") from exc
        return path
