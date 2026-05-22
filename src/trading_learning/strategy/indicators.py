from __future__ import annotations

import numpy as np
import pandas as pd


def ema(close: pd.Series, period: int) -> pd.Series:
    _validate_period(period)
    values = close.astype("float64").ewm(span=period, adjust=False, min_periods=period).mean()
    return values.rename(close.name)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    _validate_period(period)
    close = close.astype("float64")
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    result = pd.Series(np.nan, index=close.index, dtype="float64", name=close.name)
    if len(close) <= period:
        return result

    avg_gain = gains.iloc[1 : period + 1].mean()
    avg_loss = losses.iloc[1 : period + 1].mean()
    result.iloc[period] = _rsi_value(avg_gain, avg_loss)
    for index in range(period + 1, len(close)):
        avg_gain = (avg_gain * (period - 1) + gains.iloc[index]) / period
        avg_loss = (avg_loss * (period - 1) + losses.iloc[index]) / period
        result.iloc[index] = _rsi_value(avg_gain, avg_loss)
    return result


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    _validate_period(period)
    high = high.astype("float64")
    low = low.astype("float64")
    close = close.astype("float64")
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result = pd.Series(np.nan, index=close.index, dtype="float64", name=close.name)
    if len(close) < period:
        return result

    previous_atr = true_range.iloc[:period].mean()
    result.iloc[period - 1] = previous_atr
    for index in range(period, len(close)):
        previous_atr = (previous_atr * (period - 1) + true_range.iloc[index]) / period
        result.iloc[index] = previous_atr
    return result


def slope(series: pd.Series, window: int) -> pd.Series:
    _validate_period(window)
    values = series.astype("float64")
    x = np.arange(window, dtype="float64")
    x_mean = x.mean()
    denominator = float(((x - x_mean) ** 2).sum())
    result = pd.Series(np.nan, index=series.index, dtype="float64", name=series.name)
    if len(series) < window:
        return result
    for index in range(window - 1, len(series)):
        y = values.iloc[index - window + 1 : index + 1].to_numpy(dtype="float64")
        y_mean = y.mean()
        result.iloc[index] = float(((x - x_mean) * (y - y_mean)).sum() / denominator)
    return result


def _validate_period(period: int) -> None:
    if period < 1:
        raise ValueError("period must be at least 1")


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return float(100 - (100 / (1 + relative_strength)))
