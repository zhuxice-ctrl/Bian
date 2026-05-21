from __future__ import annotations

from typing import Any


def build_experiment_review_draft(report: dict[str, Any]) -> dict[str, Any]:
    experiment = report.get("experiment", {})
    metrics = report.get("metrics", {})
    round_trips = list(report.get("round_trips", []))
    realized_pnl = _effective_realized_pnl(metrics, round_trips)
    win_rate = float(metrics.get("win_rate", 0.0) or 0.0)
    max_drawdown = float(metrics.get("max_drawdown", 0.0) or 0.0)
    total_fees = float(metrics.get("total_fees", 0.0) or 0.0)
    trade_count = int(metrics.get("trade_count", 0) or 0)
    round_trip_count = int(metrics.get("round_trips", len(round_trips)) or 0)
    focus_trades = _focus_trades(round_trips)
    risk_flags = _risk_flags(
        realized_pnl=realized_pnl,
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        total_fees=total_fees,
        trade_count=trade_count,
        round_trips=round_trip_count,
        focus_trades=focus_trades,
    )
    return {
        "summary": {
            "experiment_external_id": experiment.get("external_id", ""),
            "strategy_name": experiment.get("strategy_name", ""),
            "symbol": experiment.get("symbol", ""),
            "interval": experiment.get("interval", ""),
            "trade_count": trade_count,
            "round_trips": round_trip_count,
            "realized_pnl": realized_pnl,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "total_fees": total_fees,
        },
        "risk_flags": risk_flags,
        "review_questions": _review_questions(risk_flags),
        "focus_trades": focus_trades,
        "learning_tasks": _learning_tasks(risk_flags),
    }


def _effective_realized_pnl(metrics: dict[str, Any], round_trips: list[dict[str, Any]]) -> float:
    metric_pnl = float(metrics.get("realized_pnl", 0.0) or 0.0)
    if metric_pnl:
        return metric_pnl
    return float(sum(float(trip.get("pnl", 0.0) or 0.0) for trip in round_trips))


def _risk_flags(
    *,
    realized_pnl: float,
    win_rate: float,
    max_drawdown: float,
    total_fees: float,
    trade_count: int,
    round_trips: int,
    focus_trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if realized_pnl < 0:
        flags.append({"code": "negative_pnl", "severity": "high", "message": "Experiment ended with negative realized PnL."})
    if max_drawdown < 0:
        flags.append({"code": "drawdown", "severity": "medium", "message": "Equity curve had drawdown that needs review."})
    if round_trips > 0 and win_rate < 0.5:
        flags.append({"code": "low_win_rate", "severity": "medium", "message": "Win rate is below 50%."})
    if focus_trades:
        flags.append({"code": "losing_trades", "severity": "medium", "message": "One or more closed trades lost money."})
    if total_fees > 0 and trade_count > 0 and realized_pnl <= total_fees:
        flags.append({"code": "fee_pressure", "severity": "low", "message": "Fees are large relative to realized PnL."})
    return flags


def _focus_trades(round_trips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    losing_trips = [trip for trip in round_trips if float(trip.get("pnl", 0.0) or 0.0) < 0]
    losing_trips.sort(key=lambda trip: float(trip.get("pnl", 0.0) or 0.0))
    focus: list[dict[str, Any]] = []
    for trip in losing_trips[:3]:
        focus.append(
            {
                "entry_trade_id": trip.get("entry_trade_id", ""),
                "exit_trade_id": trip.get("exit_trade_id", ""),
                "entry_time": trip.get("entry_time", ""),
                "exit_time": trip.get("exit_time", ""),
                "entry_price": float(trip.get("entry_price", 0.0) or 0.0),
                "exit_price": float(trip.get("exit_price", 0.0) or 0.0),
                "pnl": float(trip.get("pnl", 0.0) or 0.0),
                "pnl_pct": float(trip.get("pnl_pct", 0.0) or 0.0),
            }
        )
    return focus


def _review_questions(risk_flags: list[dict[str, Any]]) -> list[str]:
    codes = {flag["code"] for flag in risk_flags}
    questions: list[str] = []
    if "negative_pnl" in codes:
        questions.append("What was the main loss source: entry timing, exit timing, trend filter, or fee drag?")
    if "drawdown" in codes:
        questions.append("Which sequence created the largest drawdown and what rule would have reduced it?")
    if "low_win_rate" in codes:
        questions.append("Which losing entries should have been filtered out before execution?")
    if "losing_trades" in codes:
        questions.append("What common condition appears before the focused losing trades?")
    if "fee_pressure" in codes:
        questions.append("Would fewer trades or a larger target improve the fee-to-profit ratio?")
    if questions:
        return questions
    return [
        "Which entry conditions were most repeatable in this experiment?",
        "Which rule should be preserved unchanged before the next replay?",
    ]


def _learning_tasks(risk_flags: list[dict[str, Any]]) -> list[str]:
    codes = {flag["code"] for flag in risk_flags}
    tasks: list[str] = []
    if "negative_pnl" in codes:
        tasks.append("Replay every closed trade and label the loss source before changing parameters.")
    if "drawdown" in codes:
        tasks.append("Study drawdown control: daily stop, position sizing, and avoiding repeated entries after a loss.")
    if "low_win_rate" in codes:
        tasks.append("Create an entry-filter checklist and test it on the same BTCUSDT or ETHUSDT dataset.")
    if "fee_pressure" in codes:
        tasks.append("Compare gross PnL versus net PnL so fee impact is visible in the next report.")
    if tasks:
        return tasks
    return ["Document the conditions that worked and compare them against the next BTCUSDT or ETHUSDT replay."]
