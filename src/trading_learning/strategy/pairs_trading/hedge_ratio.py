from __future__ import annotations

import numpy as np
import pandas as pd


def static_hedge_ratio(asset_a: pd.Series, asset_b: pd.Series) -> float:
    """Full-sample OLS beta for asset_a = alpha + beta * asset_b."""

    aligned = pd.concat([asset_a.rename("a"), asset_b.rename("b")], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    variance = float(aligned["b"].var(ddof=0))
    if variance == 0:
        return 0.0
    covariance = float(aligned["a"].cov(aligned["b"], ddof=0))
    return covariance / variance


def rolling_hedge_ratio(asset_a: pd.Series, asset_b: pd.Series, window: int) -> pd.Series:
    """Rolling-window OLS beta with no lookahead."""

    if window <= 1:
        raise ValueError("window must be greater than 1")
    aligned = pd.concat([asset_a.rename("a"), asset_b.rename("b")], axis=1)
    effective_window = min(len(aligned), max(window, 500))
    covariance = aligned["a"].rolling(window=effective_window, min_periods=window).cov(aligned["b"])
    variance = aligned["b"].rolling(window=effective_window, min_periods=window).var(ddof=1)
    beta = covariance / variance.replace(0, np.nan)
    return beta.rename("hedge_ratio")
