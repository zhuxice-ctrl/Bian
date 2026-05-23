from __future__ import annotations

import numpy as np
import pandas as pd


def compute_spread(asset_a: pd.Series, asset_b: pd.Series, alpha: float, beta: float) -> pd.Series:
    """Compute log(A) - alpha - beta * log(B)."""

    aligned = pd.concat([asset_a.rename("a"), asset_b.rename("b")], axis=1).dropna()
    aligned = aligned[(aligned["a"] > 0) & (aligned["b"] > 0)]
    values = np.log(aligned["a"].astype("float64")) - float(alpha) - float(beta) * np.log(aligned["b"].astype("float64"))
    return pd.Series(values, index=aligned.index, name="spread")


def rolling_zscore(spread: pd.Series, window: int) -> pd.Series:
    """Rolling z-score using only the current and earlier observations."""

    if window <= 1:
        raise ValueError("window must be greater than 1")
    values = pd.to_numeric(spread, errors="coerce").astype("float64")
    rolling = values.rolling(window=window, min_periods=window)
    mean = rolling.mean()
    std = rolling.std(ddof=0)
    zscore = (values - mean) / std.replace(0, np.nan)
    return zscore.rename("z_score")
