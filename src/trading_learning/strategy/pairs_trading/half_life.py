from __future__ import annotations

import math

import numpy as np
import pandas as pd


def estimate_half_life(spread: pd.Series) -> float:
    """Estimate OU mean-reversion half-life in periods."""

    values = pd.to_numeric(spread, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().astype("float64")
    if len(values) < 20:
        return float("inf")
    lagged = values.shift(1)
    delta = values - lagged
    aligned = pd.concat([delta.rename("delta"), lagged.rename("lagged")], axis=1).dropna()
    if len(aligned) < 10:
        return float("inf")
    y = aligned["delta"].to_numpy(dtype="float64")
    x = np.column_stack([np.ones(len(aligned)), aligned["lagged"].to_numpy(dtype="float64")])
    intercept, slope = np.linalg.lstsq(x, y, rcond=None)[0]
    del intercept
    theta = -float(slope)
    if theta <= 0 or not math.isfinite(theta):
        return float("inf")
    return float(math.log(2) / theta)
