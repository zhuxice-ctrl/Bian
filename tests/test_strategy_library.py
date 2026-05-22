from datetime import datetime, timedelta, timezone

import pytest

from trading_learning.models import Candle, SignalAction
from trading_learning.strategy.library import generate_strategy_signals


def _candles(closes):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    return [
        Candle(
            symbol="BTCUSDT",
            opened_at=start + timedelta(hours=index),
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
            volume=10,
        )
        for index, close in enumerate(closes)
    ]


def test_generate_strategy_signals_supports_breakout():
    signals = generate_strategy_signals(
        "breakout",
        _candles([100, 101, 102, 105, 104, 103, 99]),
        {"lookback": 3},
    )

    assert [signal.action for signal in signals] == [SignalAction.BUY, SignalAction.SELL]
    assert "breakout" in signals[0].reason


def test_generate_strategy_signals_supports_mean_reversion():
    signals = generate_strategy_signals(
        "mean_reversion",
        _candles([100, 100, 100, 94, 99, 106]),
        {"window": 3, "threshold_pct": 0.03},
    )

    assert [signal.action for signal in signals] == [SignalAction.BUY, SignalAction.SELL]
    assert "mean reversion" in signals[0].reason


def test_generate_strategy_signals_rejects_unknown_strategy():
    with pytest.raises(ValueError, match="unknown strategy"):
        generate_strategy_signals("unknown", _candles([1, 2, 3]), {})
