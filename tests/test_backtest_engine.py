from datetime import datetime, timezone

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.models import Signal, SignalAction


def test_backtest_enforces_daily_trade_limit():
    signals = [
        Signal(
            "BTCUSDT",
            datetime(2026, 5, 1, hour, tzinfo=timezone.utc),
            SignalAction.BUY if hour % 2 == 0 else SignalAction.SELL,
            "test",
        )
        for hour in range(8)
    ]
    prices = {
        signal.timestamp: 100.0 + index
        for index, signal in enumerate(signals)
    }

    result = run_spot_backtest(
        symbol="BTCUSDT",
        signals=signals,
        prices_by_timestamp=prices,
        starting_cash=1000.0,
        quote_amount_per_buy=100.0,
        fee_rate=0.001,
        daily_trade_limit=5,
    )

    assert result.trade_count == 5
