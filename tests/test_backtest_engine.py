from datetime import datetime, timezone

import pytest

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.models import Side, Signal, SignalAction


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


def test_backtest_no_op_signals_without_prices_do_not_trade():
    signals = [
        Signal(
            "BTCUSDT",
            datetime(2026, 5, 1, 0, tzinfo=timezone.utc),
            SignalAction.HOLD,
            "hold",
        ),
        Signal(
            "BTCUSDT",
            datetime(2026, 5, 1, 1, tzinfo=timezone.utc),
            SignalAction.SELL,
            "no position",
        ),
        Signal(
            "BTCUSDT",
            datetime(2026, 5, 1, 2, tzinfo=timezone.utc),
            SignalAction.BUY,
            "insufficient cash",
        ),
    ]

    result = run_spot_backtest(
        symbol="BTCUSDT",
        signals=signals,
        prices_by_timestamp={},
        starting_cash=50.0,
        quote_amount_per_buy=100.0,
        fee_rate=0.001,
        daily_trade_limit=5,
    )

    assert result.trade_count == 0
    assert result.trades == ()


def test_backtest_fee_math_and_sell_all_behavior():
    buy_timestamp = datetime(2026, 5, 1, 0, tzinfo=timezone.utc)
    sell_timestamp = datetime(2026, 5, 1, 1, tzinfo=timezone.utc)
    signals = [
        Signal("BTCUSDT", buy_timestamp, SignalAction.BUY, "buy"),
        Signal("BTCUSDT", sell_timestamp, SignalAction.SELL, "sell"),
    ]

    result = run_spot_backtest(
        symbol="BTCUSDT",
        signals=signals,
        prices_by_timestamp={
            buy_timestamp: 100.0,
            sell_timestamp: 110.0,
        },
        starting_cash=1000.0,
        quote_amount_per_buy=100.0,
        fee_rate=0.001,
        daily_trade_limit=5,
    )

    buy_trade, sell_trade = result.trades
    expected_buy_quantity = 0.999
    expected_ending_cash = 1000.0 - 100.0 + (expected_buy_quantity * 110.0 * 0.999)

    assert buy_trade.side == Side.BUY
    assert sell_trade.side == Side.SELL
    assert buy_trade.quantity == pytest.approx(expected_buy_quantity)
    assert sell_trade.quantity == pytest.approx(expected_buy_quantity)
    assert result.ending_cash == pytest.approx(expected_ending_cash)
    assert result.position_quantity == 0.0


def test_backtest_daily_trade_limit_resets_across_dates():
    signals = [
        Signal(
            "BTCUSDT",
            datetime(2026, 5, 1, hour, tzinfo=timezone.utc),
            SignalAction.BUY if hour % 2 == 0 else SignalAction.SELL,
            "day one",
        )
        for hour in range(8)
    ]
    signals.append(
        Signal(
            "BTCUSDT",
            datetime(2026, 5, 2, 0, tzinfo=timezone.utc),
            SignalAction.BUY,
            "day two",
        )
    )
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

    assert result.trade_count == 6
