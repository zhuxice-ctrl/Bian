from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trading_learning.models import BacktestResult, Side


@dataclass(frozen=True)
class BacktestMetrics:
    symbol: str
    trade_count: int
    round_trips: int
    win_count: int
    loss_count: int
    win_rate: float
    realized_pnl: float
    total_fees: float


def summarize_backtest(result: BacktestResult) -> BacktestMetrics:
    total_fees = sum(trade.fee for trade in result.trades)
    realized_pnls: list[float] = []
    open_cost = 0.0
    open_fee = 0.0

    for trade in result.trades:
        if trade.side == Side.BUY:
            open_cost += trade.quantity * trade.price
            open_fee += trade.fee
        elif trade.side == Side.SELL and open_cost > 0:
            proceeds = trade.quantity * trade.price
            realized_pnls.append(proceeds - trade.fee - open_cost - open_fee)
            open_cost = 0.0
            open_fee = 0.0

    win_count = sum(1 for pnl in realized_pnls if pnl > 0)
    loss_count = sum(1 for pnl in realized_pnls if pnl < 0)
    round_trips = len(realized_pnls)
    win_rate = win_count / round_trips if round_trips else 0.0

    return BacktestMetrics(
        symbol=result.symbol,
        trade_count=result.trade_count,
        round_trips=round_trips,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_rate,
        realized_pnl=result.ending_cash - result.starting_cash,
        total_fees=total_fees,
    )


def build_backtest_report(result: BacktestResult) -> dict[str, Any]:
    metrics = summarize_backtest(result)
    round_trips = _round_trips(result)
    equity_curve = _equity_curve(result.starting_cash, round_trips, result.trades)
    drawdown = _max_drawdown(equity_curve)
    return {
        "metrics": {
            "symbol": metrics.symbol,
            "trade_count": metrics.trade_count,
            "round_trips": metrics.round_trips,
            "win_count": metrics.win_count,
            "loss_count": metrics.loss_count,
            "win_rate": metrics.win_rate,
            "realized_pnl": metrics.realized_pnl,
            "total_fees": metrics.total_fees,
            "max_drawdown": drawdown["max_drawdown"],
            "max_drawdown_pct": drawdown["max_drawdown_pct"],
        },
        "round_trips": round_trips,
        "equity_curve": equity_curve,
    }


def _round_trips(result: BacktestResult) -> list[dict[str, Any]]:
    trips: list[dict[str, Any]] = []
    open_trade = None
    for trade in result.trades:
        if trade.side == Side.BUY:
            open_trade = trade
            continue
        if trade.side != Side.SELL or open_trade is None:
            continue
        entry_cost = open_trade.quantity * open_trade.price
        exit_value = trade.quantity * trade.price
        fees = open_trade.fee + trade.fee
        pnl = exit_value - entry_cost - fees
        trips.append(
            {
                "entry_trade_id": open_trade.external_id,
                "exit_trade_id": trade.external_id,
                "entry_time": open_trade.timestamp.isoformat(),
                "exit_time": trade.timestamp.isoformat(),
                "quantity": float(trade.quantity),
                "entry_price": float(open_trade.price),
                "exit_price": float(trade.price),
                "fees": float(fees),
                "pnl": float(pnl),
                "pnl_pct": pnl / entry_cost if entry_cost else 0.0,
            }
        )
        open_trade = None
    return trips


def _equity_curve(starting_cash: float, round_trips: list[dict[str, Any]], trades: tuple[Any, ...]) -> list[dict[str, Any]]:
    if trades:
        first_time = trades[0].timestamp.isoformat()
    else:
        first_time = ""
    curve = [{"time": first_time, "equity": float(starting_cash)}]
    equity = starting_cash
    for trip in round_trips:
        equity += trip["pnl"]
        curve.append({"time": trip["exit_time"], "equity": float(equity)})
    return curve


def _max_drawdown(equity_curve: list[dict[str, Any]]) -> dict[str, float]:
    peak = None
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    for point in equity_curve:
        equity = float(point["equity"])
        if peak is None or equity > peak:
            peak = equity
        if not peak:
            continue
        drawdown = equity - peak
        drawdown_pct = drawdown / peak
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            max_drawdown_pct = drawdown_pct
    return {"max_drawdown": max_drawdown, "max_drawdown_pct": max_drawdown_pct}
