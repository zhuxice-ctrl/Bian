from __future__ import annotations

import math

import numpy as np
import pandas as pd


def signal_standalone_sharpe(
    forecast: pd.Series,
    next_return: pd.Series,
    periods_per_year: int = 365,
) -> float:
    """Return annualized Sharpe of forecast times next-period return, before costs."""

    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    aligned = pd.concat([forecast.astype(float), next_return.astype(float)], axis=1, join="inner").dropna(how="any")
    if aligned.empty:
        return float("nan")

    pnl = aligned.iloc[:, 0] * aligned.iloc[:, 1]
    mean = float(pnl.mean())
    std = float(pnl.std(ddof=0))
    if std == 0.0 or not np.isfinite(std):
        return 0.0 if mean == 0.0 else math.copysign(float("inf"), mean)
    return mean / std * math.sqrt(periods_per_year)
