from datetime import datetime, timezone

from trading_learning.models import Candle, SignalAction
from trading_learning.strategy.moving_average import moving_average_crossover_signals


def candle(index: int, close: float) -> Candle:
    return Candle(
        symbol="BTCUSDT",
        opened_at=datetime(2026, 5, 1, index, tzinfo=timezone.utc),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1.0,
    )


def test_moving_average_crossover_emits_buy_then_sell():
    closes = [10, 10, 10, 11, 12, 13, 12, 11, 10]
    signals = moving_average_crossover_signals(
        [candle(i, value) for i, value in enumerate(closes)],
        short_window=2,
        long_window=3,
    )

    actions = [signal.action for signal in signals]
    assert SignalAction.BUY in actions
    assert SignalAction.SELL in actions
