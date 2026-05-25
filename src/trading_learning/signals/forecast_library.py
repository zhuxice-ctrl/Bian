from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_NORMALIZATION_WINDOW = 252
DEFAULT_FORECAST_CAP = 2.0


def ewmac_forecast(
    price: pd.Series,
    *,
    fast_span: int,
    slow_span: int,
    normalization_window: int = DEFAULT_NORMALIZATION_WINDOW,
) -> pd.Series:
    """Return a normalized EWMAC forecast."""

    if fast_span <= 0 or slow_span <= 0:
        raise ValueError("spans must be positive")
    if fast_span >= slow_span:
        raise ValueError("fast_span must be smaller than slow_span")
    price = _price_series(price)
    fast = price.ewm(span=fast_span, adjust=False, min_periods=fast_span).mean()
    slow = price.ewm(span=slow_span, adjust=False, min_periods=slow_span).mean()
    raw = fast - slow
    return normalize_forecast(raw, window=normalization_window).rename(f"EWMAC_{fast_span}_{slow_span}")


def breakout_forecast(
    price: pd.Series,
    *,
    window: int = 120,
    normalization_window: int = DEFAULT_NORMALIZATION_WINDOW,
) -> pd.Series:
    """Return a normalized rolling-channel breakout forecast."""

    if window <= 0:
        raise ValueError("window must be positive")
    price = _price_series(price)
    rolling_max = price.rolling(window, min_periods=window).max()
    rolling_min = price.rolling(window, min_periods=window).min()
    rolling_mid = (rolling_max + rolling_min) / 2.0
    channel_width = rolling_max - rolling_min
    raw = (price - rolling_mid) / channel_width.replace(0.0, np.nan)
    return normalize_forecast(raw, window=normalization_window).rename("SIG_BREAKOUT")


def mean_reversion_forecast(
    price: pd.Series,
    *,
    window: int = 20,
    normalization_window: int = DEFAULT_NORMALIZATION_WINDOW,
) -> pd.Series:
    """Return a normalized short-term mean-reversion forecast."""

    if window <= 1:
        raise ValueError("window must be greater than 1")
    price = _price_series(price)
    raw = -1.0 * rolling_zscore(price, window=window)
    return normalize_forecast(raw, window=normalization_window).rename("SIG_MEAN_REV")


def momentum_forecast(
    price: pd.Series,
    *,
    lookback: int = 60,
    normalization_window: int = DEFAULT_NORMALIZATION_WINDOW,
) -> pd.Series:
    """Return a normalized trailing-return momentum forecast."""

    if lookback <= 0:
        raise ValueError("lookback must be positive")
    price = _price_series(price)
    raw = price.pct_change(lookback)
    return normalize_forecast(raw, window=normalization_window).rename("SIG_MOMENTUM")


def vol_regime_forecast(
    price: pd.Series,
    *,
    vol_window: int = 60,
    zscore_window: int = DEFAULT_NORMALIZATION_WINDOW,
    normalization_window: int = DEFAULT_NORMALIZATION_WINDOW,
) -> pd.Series:
    """Return a normalized volatility-regime forecast."""

    if vol_window <= 1:
        raise ValueError("vol_window must be greater than 1")
    if zscore_window <= 1:
        raise ValueError("zscore_window must be greater than 1")
    price = _price_series(price)
    returns = price.pct_change()
    rolling_vol = returns.rolling(vol_window, min_periods=vol_window).std(ddof=0)
    raw = rolling_zscore(rolling_vol, window=zscore_window)
    return normalize_forecast(raw, window=normalization_window).rename("SIG_VOL_REGIME")


def sig_trend_fast(price: pd.Series) -> pd.Series:
    return ewmac_forecast(price, fast_span=8, slow_span=32).rename("SIG_TREND_FAST")


def sig_trend_slow(price: pd.Series) -> pd.Series:
    return ewmac_forecast(price, fast_span=64, slow_span=256).rename("SIG_TREND_SLOW")


def sig_breakout(price: pd.Series) -> pd.Series:
    return breakout_forecast(price, window=120).rename("SIG_BREAKOUT")


def sig_mean_rev(price: pd.Series) -> pd.Series:
    return mean_reversion_forecast(price, window=20).rename("SIG_MEAN_REV")


def sig_momentum(price: pd.Series) -> pd.Series:
    return momentum_forecast(price, lookback=60).rename("SIG_MOMENTUM")


def sig_vol_regime(price: pd.Series) -> pd.Series:
    return vol_regime_forecast(price, vol_window=60).rename("SIG_VOL_REGIME")


def normalize_forecast(
    raw_forecast: pd.Series,
    *,
    window: int = DEFAULT_NORMALIZATION_WINDOW,
    cap: float = DEFAULT_FORECAST_CAP,
) -> pd.Series:
    """Scale by rolling absolute mean, cap to [-2, 2], and rescale to [-1, 1]."""

    if window <= 0:
        raise ValueError("window must be positive")
    if cap <= 0.0:
        raise ValueError("cap must be positive")
    raw = raw_forecast.astype(float)
    scale = raw.abs().rolling(window, min_periods=window).mean()
    scaled = raw / scale.replace(0.0, np.nan)
    return scaled.replace([np.inf, -np.inf], np.nan).clip(lower=-cap, upper=cap) / cap


def rolling_zscore(series: pd.Series, *, window: int) -> pd.Series:
    if window <= 1:
        raise ValueError("window must be greater than 1")
    values = series.astype(float)
    mean = values.rolling(window, min_periods=window).mean()
    std = values.rolling(window, min_periods=window).std(ddof=0)
    return ((values - mean) / std.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)


def _price_series(price: pd.Series) -> pd.Series:
    if not isinstance(price, pd.Series):
        raise TypeError("price must be a pandas Series")
    return price.astype(float)
