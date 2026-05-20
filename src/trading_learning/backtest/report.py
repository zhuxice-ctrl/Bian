from __future__ import annotations

from dataclasses import dataclass

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
