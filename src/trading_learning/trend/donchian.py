from __future__ import annotations

import pandas as pd


def donchian_channels(prices: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    Calculate N-bar Donchian channels using only completed prior bars.

    upper[t] = max(high[t-n], ..., high[t-1])
    lower[t] = min(low[t-n], ..., low[t-1])
    """

    _validate_positive_n(n)
    _require_columns(prices, ("high", "low", "close"))
    upper = prices["high"].shift(1).rolling(window=n, min_periods=n).max()
    lower = prices["low"].shift(1).rolling(window=n, min_periods=n).min()
    return pd.DataFrame({"upper": upper, "lower": lower}, index=prices.index)


def donchian_signals(prices: pd.DataFrame, n: int) -> pd.Series:
    """Return +1 for long breakouts, -1 for short breakouts, and 0 otherwise."""

    channels = donchian_channels(prices, n)
    close = prices["close"]
    signal = pd.Series(0, index=prices.index, dtype="int64")
    signal = signal.mask(close > channels["upper"], 1)
    signal = signal.mask(close < channels["lower"], -1)
    return signal


def _validate_positive_n(n: int) -> None:
    if n <= 0:
        raise ValueError("n must be positive")


def _require_columns(prices: pd.DataFrame, required: tuple[str, ...]) -> None:
    missing = [column for column in required if column not in prices.columns]
    if missing:
        raise ValueError(f"prices missing required columns: {', '.join(missing)}")
