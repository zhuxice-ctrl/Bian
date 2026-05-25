import numpy as np
import pandas as pd
import pytest

from trading_learning.signals.forecast_library import (
    breakout_forecast,
    ewmac_forecast,
    mean_reversion_forecast,
    momentum_forecast,
    sig_breakout,
    sig_mean_rev,
    sig_momentum,
    sig_trend_fast,
    sig_trend_slow,
    sig_vol_regime,
    vol_regime_forecast,
)


def test_ewmac_trend_forecasts_are_positive_on_monotonic_uptrend():
    price = _linear_price()

    fast = sig_trend_fast(price)
    slow = sig_trend_slow(price)

    assert fast.index.equals(price.index)
    assert slow.index.equals(price.index)
    assert fast.dropna().iloc[-1] > 0
    assert slow.dropna().iloc[-1] > 0
    assert _finite_values_are_capped(fast)
    assert _finite_values_are_capped(slow)


def test_parameterized_ewmac_forecast_validates_span_order():
    price = _linear_price()

    with pytest.raises(ValueError, match="fast_span"):
        ewmac_forecast(price, fast_span=32, slow_span=8)


def test_breakout_forecast_is_positive_near_rolling_high():
    price = _linear_price()

    forecast = sig_breakout(price)

    assert forecast.dropna().iloc[-1] > 0
    assert _finite_values_are_capped(forecast)


def test_mean_reversion_forecast_is_negative_after_extended_rise():
    price = _linear_price()

    forecast = sig_mean_rev(price)

    assert forecast.dropna().iloc[-1] < 0
    assert _finite_values_are_capped(forecast)


def test_momentum_forecast_is_positive_after_sixty_day_gain():
    price = _linear_price()

    forecast = sig_momentum(price)

    assert forecast.dropna().iloc[-1] > 0
    assert _finite_values_are_capped(forecast)


def test_vol_regime_forecast_is_positive_after_volatility_increases():
    rng = np.random.default_rng(42)
    low_vol_returns = rng.normal(0.0005, 0.001, 520)
    high_vol_returns = rng.normal(0.0005, 0.025, 240)
    price = pd.Series(
        100.0 * np.cumprod(1.0 + np.concatenate([low_vol_returns, high_vol_returns])),
        index=pd.date_range("2024-01-01", periods=760, freq="D", tz="UTC"),
        name="close",
    )

    forecast = sig_vol_regime(price)

    assert forecast.dropna().iloc[-1] > 0
    assert _finite_values_are_capped(forecast)


def test_named_signal_functions_match_parameterized_building_blocks():
    price = _linear_price()

    pd.testing.assert_series_equal(sig_breakout(price), breakout_forecast(price, window=120))
    pd.testing.assert_series_equal(sig_mean_rev(price), mean_reversion_forecast(price, window=20))
    pd.testing.assert_series_equal(sig_momentum(price), momentum_forecast(price, lookback=60))
    pd.testing.assert_series_equal(sig_vol_regime(price), vol_regime_forecast(price, vol_window=60))


def _linear_price() -> pd.Series:
    return pd.Series(
        np.linspace(100.0, 200.0, 720),
        index=pd.date_range("2024-01-01", periods=720, freq="D", tz="UTC"),
        name="close",
    )


def _finite_values_are_capped(series: pd.Series) -> bool:
    finite = series.dropna()
    return bool(((finite >= -1.0) & (finite <= 1.0)).all())
