import numpy as np
import pandas as pd
import pytest

from trading_learning.signals.forecast_library import (
    breakout_forecast,
    ewmac_forecast,
    mean_reversion_forecast,
    momentum_forecast,
    normalize_forecast,
    sig_breakout,
    sig_mean_rev,
    sig_momentum,
    sig_trend_fast,
    sig_trend_slow,
    sig_vol_regime,
    vol_regime_forecast,
)


def test_normalize_forecast_defaults_to_expanding_and_starts_on_sixtieth_day():
    raw = pd.Series(
        np.ones(80),
        index=pd.date_range("2026-01-01", periods=80, freq="D", tz="UTC"),
        name="raw",
    )

    forecast = normalize_forecast(raw)

    assert forecast.first_valid_index() == raw.index[59]
    assert forecast.dropna().iloc[0] == pytest.approx(0.5)
    assert _finite_values_are_capped(forecast)


def test_normalize_forecast_rolling_mode_preserves_252_day_burn_in():
    raw = pd.Series(
        np.ones(300),
        index=pd.date_range("2026-01-01", periods=300, freq="D", tz="UTC"),
        name="raw",
    )

    forecast = normalize_forecast(raw, normalization="rolling")

    assert forecast.first_valid_index() == raw.index[251]
    assert forecast.dropna().iloc[0] == pytest.approx(0.5)


def test_normalize_forecast_rejects_unknown_normalization_mode():
    with pytest.raises(ValueError, match="normalization"):
        normalize_forecast(pd.Series([1.0, 2.0, 3.0]), normalization="forever")


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


def test_ewmac_rolling_mode_preserves_long_slow_span_burn_in():
    price = _linear_price()

    expanding = ewmac_forecast(price, fast_span=64, slow_span=256)
    rolling = ewmac_forecast(price, fast_span=64, slow_span=256, normalization="rolling")

    assert expanding.first_valid_index() == price.index[59]
    assert rolling.first_valid_index() == price.index[506]


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
