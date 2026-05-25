from __future__ import annotations

import numpy as np
import pandas as pd


def pca_explained_variance(returns_df: pd.DataFrame, n_components: int | None = None) -> pd.Series:
    """Return PCA explained variance ratios as PC1, PC2, ..."""

    matrix = _analysis_matrix(returns_df)
    if n_components is not None and (n_components < 1 or n_components > matrix.shape[0]):
        raise ValueError("n_components must be between 1 and the matrix size")

    eigenvalues = np.linalg.eigvalsh(matrix)
    eigenvalues = np.sort(np.clip(eigenvalues, 0.0, None))[::-1]
    total = float(eigenvalues.sum())
    if total <= 0.0 or not np.isfinite(total):
        raise ValueError("matrix must contain positive total variance")

    ratios = eigenvalues / total
    if n_components is not None:
        ratios = ratios[:n_components]
    return pd.Series(ratios, index=[f"PC{index}" for index in range(1, len(ratios) + 1)])


def effective_dimension_threshold(explained_variance: pd.Series, threshold: float = 0.9) -> int:
    """Return first component count whose cumulative explained variance reaches threshold."""

    if threshold <= 0.0 or threshold > 1.0:
        raise ValueError("threshold must be in (0, 1]")
    values = np.asarray(explained_variance, dtype=float)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("explained_variance must be a non-empty one-dimensional series")
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("explained_variance must contain finite non-negative values")

    cumulative = np.cumsum(values)
    for index, value in enumerate(cumulative, start=1):
        if value >= threshold:
            return index
    return len(values)


def absolute_correlation_n_eff(corr_matrix: pd.DataFrame, weights: pd.Series | np.ndarray | None = None) -> float:
    """Return effective N using absolute correlations, ignoring hedge sign."""

    matrix = np.abs(_square_matrix(corr_matrix))
    if weights is None:
        weight_values = np.full(matrix.shape[0], 1.0 / matrix.shape[0])
    else:
        weight_values = _aligned_weights(corr_matrix, weights)

    denominator = float(weight_values.T @ matrix @ weight_values)
    if denominator <= 0.0 or not np.isfinite(denominator):
        return float("nan")
    numerator = float(np.sum(weight_values) ** 2)
    return numerator / denominator


def _analysis_matrix(frame: pd.DataFrame) -> np.ndarray:
    values = np.asarray(frame, dtype=float)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] == 0:
        raise ValueError("returns_df must be a non-empty two-dimensional frame")
    if not np.all(np.isfinite(values)):
        raise ValueError("returns_df must be finite")
    if values.shape[0] == values.shape[1] and np.allclose(values, values.T, equal_nan=False):
        return values
    correlation = frame.astype(float).corr().to_numpy(dtype=float)
    if correlation.size == 0 or not np.all(np.isfinite(correlation)):
        raise ValueError("returns_df correlation matrix must be finite")
    return correlation


def _square_matrix(frame: pd.DataFrame) -> np.ndarray:
    matrix = np.asarray(frame, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("corr_matrix must be a non-empty square matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("corr_matrix must be finite")
    return matrix


def _aligned_weights(corr_matrix: pd.DataFrame, weights: pd.Series | np.ndarray) -> np.ndarray:
    if isinstance(weights, pd.Series):
        weight_values = weights.reindex(corr_matrix.index).to_numpy(dtype=float)
    else:
        weight_values = np.asarray(weights, dtype=float)
    if weight_values.ndim != 1:
        raise ValueError("weights must be one-dimensional")
    if len(weight_values) != len(corr_matrix):
        raise ValueError("weights length must match corr_matrix size")
    if not np.all(np.isfinite(weight_values)):
        raise ValueError("weights must be finite")
    return weight_values
