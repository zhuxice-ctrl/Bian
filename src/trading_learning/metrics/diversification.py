from __future__ import annotations

import numpy as np
import pandas as pd


def pairwise_correlation(returns_df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """Return a pairwise return correlation matrix."""

    if method not in {"pearson", "spearman"}:
        raise ValueError("method must be 'pearson' or 'spearman'")
    return returns_df.corr(method=method)


def effective_n_bets(corr_matrix: pd.DataFrame, weights: pd.Series | np.ndarray | None = None) -> float:
    """Return Effective N of Bets: (sum(w))^2 / (w' corr w)."""

    matrix = np.asarray(corr_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("corr_matrix must be square")
    if matrix.shape[0] == 0:
        raise ValueError("corr_matrix must not be empty")

    if weights is None:
        weight_values = np.full(matrix.shape[0], 1.0 / matrix.shape[0])
    else:
        weight_values = _aligned_weights(corr_matrix, weights)

    denominator = float(weight_values.T @ matrix @ weight_values)
    if denominator <= 0.0 or not np.isfinite(denominator):
        return float("nan")
    numerator = float(np.sum(weight_values) ** 2)
    return numerator / denominator


def rolling_correlation(returns_a: pd.Series, returns_b: pd.Series, window: int = 90) -> pd.Series:
    """Return rolling correlation between two return series."""

    if window <= 0:
        raise ValueError("window must be positive")
    return returns_a.rolling(window).corr(returns_b)


def _aligned_weights(corr_matrix: pd.DataFrame, weights: pd.Series | np.ndarray) -> np.ndarray:
    if isinstance(weights, pd.Series):
        if isinstance(corr_matrix, pd.DataFrame):
            weight_values = weights.reindex(corr_matrix.index).to_numpy(dtype=float)
        else:
            weight_values = weights.to_numpy(dtype=float)
    else:
        weight_values = np.asarray(weights, dtype=float)

    if weight_values.ndim != 1:
        raise ValueError("weights must be one-dimensional")
    if len(weight_values) != len(corr_matrix):
        raise ValueError("weights length must match corr_matrix size")
    if not np.all(np.isfinite(weight_values)):
        raise ValueError("weights must be finite")
    return weight_values
