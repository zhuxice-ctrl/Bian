from datetime import datetime, timezone

import pandas as pd
import pytest

from trading_learning.backtest.engine import backtest_forecast, buy_and_hold_result, run_spot_backtest
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


def test_backtest_forecast_zero_forecast_has_zero_returns_and_costs():
    price = _price_series([100.0, 101.0, 102.0, 103.0, 104.0])
    forecast = pd.Series(0.0, index=price.index)

    result = backtest_forecast(forecast, price, vol_lookback=2, capital=100_000)

    assert result.equity_curve.iloc[0] == pytest.approx(100_000.0)
    assert result.daily_returns.fillna(0.0).sum() == pytest.approx(0.0)
    assert result.gross_returns.fillna(0.0).sum() == pytest.approx(0.0)
    assert result.positions.fillna(0.0).abs().sum() == pytest.approx(0.0)
    assert result.costs.fillna(0.0).sum() == pytest.approx(0.0)
    assert result.turnover.fillna(0.0).sum() == pytest.approx(0.0)


def test_backtest_forecast_constant_long_forecast_on_rising_price_profits():
    price = _price_series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    forecast = pd.Series(1.0, index=price.index)

    result = backtest_forecast(forecast, price, vol_lookback=2, cost_per_round_trip=0.0, capital=100_000)

    assert result.equity_curve.iloc[-1] > result.equity_curve.iloc[0]
    assert result.gross_returns.sum() > 0.0
    assert result.metrics["total_return"] > 0.0


def test_backtest_forecast_high_turnover_generates_cost_drag():
    price = _price_series([100.0, 100.5, 100.0, 100.5, 100.0, 100.5, 100.0])
    forecast = pd.Series([1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0], index=price.index)

    result = backtest_forecast(forecast, price, vol_lookback=2, cost_per_round_trip=0.01, capital=100_000)

    assert result.turnover.sum() > 0.0
    assert result.costs.sum() > 0.0
    assert result.metrics["total_cost_drag"] > 0.0
    assert result.daily_returns.sum() < result.gross_returns.sum()


def test_buy_and_hold_result_matches_manual_close_to_close_return():
    price = _price_series([100.0, 110.0, 121.0])

    result = buy_and_hold_result(price, capital=100_000, periods_per_year=365)

    assert result.equity_curve.iloc[0] == pytest.approx(100_000.0)
    assert result.equity_curve.iloc[-1] == pytest.approx(121_000.0)
    pd.testing.assert_series_equal(result.daily_returns, price.pct_change().fillna(0.0), check_names=False)
    assert result.metrics["total_return"] == pytest.approx(0.21)


def _price_series(values: list[float]) -> pd.Series:
    return pd.Series(
        values,
        index=pd.date_range("2026-01-01", periods=len(values), freq="D", tz="UTC"),
        name="close",
    )
