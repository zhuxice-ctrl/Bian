from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def adf_test(series: pd.Series) -> dict[str, Any]:
    """Run a compact ADF stationarity test with a constant term.

    The project deliberately keeps dependencies small, so this uses a local OLS
    implementation and MacKinnon-style critical-value buckets for the p-value.
    It is intended for research gating, not publication-grade econometrics.
    """

    values = _finite_series(series)
    if len(values) < 20:
        return {"p_value": 1.0, "stat": 0.0, "lags": 0}

    lags = _adf_lag_count(len(values))
    dy = values.diff().dropna()
    lagged_level = values.shift(1).dropna()
    aligned = pd.concat([dy.rename("dy"), lagged_level.rename("lagged")], axis=1).dropna()
    for lag in range(1, lags + 1):
        aligned[f"d_lag_{lag}"] = dy.shift(lag)
    aligned = aligned.dropna()
    if len(aligned) < max(10, lags + 3):
        return {"p_value": 1.0, "stat": 0.0, "lags": lags}

    y = aligned["dy"].to_numpy(dtype="float64")
    columns = [np.ones(len(aligned)), aligned["lagged"].to_numpy(dtype="float64")]
    for lag in range(1, lags + 1):
        columns.append(aligned[f"d_lag_{lag}"].to_numpy(dtype="float64"))
    x = np.column_stack(columns)
    beta, standard_errors = _ols_with_se(y, x)
    stat = float(beta[1] / standard_errors[1]) if standard_errors[1] > 0 else 0.0
    return {"p_value": _adf_p_value_bucket(stat), "stat": stat, "lags": lags}


def engle_granger_test(asset_a: pd.Series, asset_b: pd.Series) -> dict[str, Any]:
    """Two-step Engle-Granger cointegration test on log prices."""

    aligned = pd.concat([asset_a.rename("a"), asset_b.rename("b")], axis=1).dropna()
    aligned = aligned[(aligned["a"] > 0) & (aligned["b"] > 0)]
    if len(aligned) < 30:
        residuals = pd.Series(dtype="float64")
        return {"alpha": 0.0, "beta": 0.0, "residuals": residuals, "adf_p_value": 1.0, "is_cointegrated": False}

    log_a = np.log(aligned["a"].to_numpy(dtype="float64"))
    log_b = np.log(aligned["b"].to_numpy(dtype="float64"))
    x = np.column_stack([np.ones(len(log_b)), log_b])
    coefficients, _ = _ols_with_se(log_a, x)
    alpha = float(coefficients[0])
    beta = float(coefficients[1])
    residual_values = log_a - alpha - beta * log_b
    residuals = pd.Series(residual_values, index=aligned.index, name="residual")
    adf = adf_test(residuals)
    p_value = float(adf["p_value"])
    return {
        "alpha": alpha,
        "beta": beta,
        "residuals": residuals,
        "adf_p_value": p_value,
        "is_cointegrated": p_value < 0.05,
    }


def _finite_series(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return values.astype("float64")


def _adf_lag_count(count: int) -> int:
    return int(max(0, min(12, np.floor((count - 1) ** (1 / 3) / 2))))


def _ols_with_se(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    coefficients = np.linalg.lstsq(x, y, rcond=None)[0]
    residuals = y - x @ coefficients
    dof = max(1, len(y) - x.shape[1])
    sigma2 = float((residuals @ residuals) / dof)
    xtx_inv = np.linalg.pinv(x.T @ x)
    standard_errors = np.sqrt(np.maximum(np.diag(xtx_inv) * sigma2, 0.0))
    return coefficients, standard_errors


def _adf_p_value_bucket(stat: float) -> float:
    if stat <= -3.43:
        return 0.01
    if stat <= -2.86:
        return 0.049
    if stat <= -2.57:
        return 0.10
    return 0.50
