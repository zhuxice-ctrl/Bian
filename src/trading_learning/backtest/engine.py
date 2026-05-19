from __future__ import annotations

from collections import defaultdict

from trading_learning.models import BacktestResult, Side, Signal, SignalAction, Trade


def run_spot_backtest(
    symbol: str,
    signals: list[Signal],
    prices_by_timestamp: dict,
    starting_cash: float,
    quote_amount_per_buy: float,
    fee_rate: float,
    daily_trade_limit: int,
) -> BacktestResult:
    cash = starting_cash
    position_quantity = 0.0
    trades: list[Trade] = []
    daily_counts: dict[str, int] = defaultdict(int)

    for signal in signals:
        day_key = signal.timestamp.date().isoformat()
        if daily_counts[day_key] >= daily_trade_limit:
            continue

        if signal.action == SignalAction.BUY and cash >= quote_amount_per_buy:
            price = float(prices_by_timestamp[signal.timestamp])
            fee = quote_amount_per_buy * fee_rate
            quantity = (quote_amount_per_buy - fee) / price
            cash -= quote_amount_per_buy
            position_quantity += quantity
            daily_counts[day_key] += 1
            trades.append(
                Trade(
                    external_id=f"backtest-{symbol}-{signal.timestamp.isoformat()}-buy",
                    symbol=symbol,
                    side=Side.BUY,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    timestamp=signal.timestamp,
                    reason=signal.reason,
                )
            )
        elif signal.action == SignalAction.SELL and position_quantity > 0:
            price = float(prices_by_timestamp[signal.timestamp])
            gross = position_quantity * price
            fee = gross * fee_rate
            cash += gross - fee
            quantity = position_quantity
            position_quantity = 0.0
            daily_counts[day_key] += 1
            trades.append(
                Trade(
                    external_id=f"backtest-{symbol}-{signal.timestamp.isoformat()}-sell",
                    symbol=symbol,
                    side=Side.SELL,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    timestamp=signal.timestamp,
                    reason=signal.reason,
                )
            )

    return BacktestResult(
        symbol=symbol,
        starting_cash=starting_cash,
        ending_cash=cash,
        position_quantity=position_quantity,
        trade_count=len(trades),
        trades=tuple(trades),
    )
