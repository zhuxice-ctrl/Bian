import numpy as np
import pandas as pd
import pytest

from trading_learning.metrics.dimension_analysis import (
    absolute_correlation_n_eff,
    effective_dimension_threshold,
    pca_explained_variance,
)


def test_pca_explained_variance_identity_matrix_is_equal_across_components():
    matrix = pd.DataFrame(np.eye(4), columns=list("ABCD"), index=list("ABCD"))

    result = pca_explained_variance(matrix)

    assert list(result.index) == ["PC1", "PC2", "PC3", "PC4"]
    assert result.tolist() == pytest.approx([0.25, 0.25, 0.25, 0.25])


def test_pca_explained_variance_all_ones_matrix_has_one_component():
    matrix = pd.DataFrame(np.ones((4, 4)), columns=list("ABCD"), index=list("ABCD"))

    result = pca_explained_variance(matrix)

    assert result.tolist() == pytest.approx([1.0, 0.0, 0.0, 0.0])


def test_pca_explained_variance_can_limit_component_count():
    matrix = pd.DataFrame(np.eye(4), columns=list("ABCD"), index=list("ABCD"))

    result = pca_explained_variance(matrix, n_components=2)

    assert list(result.index) == ["PC1", "PC2"]
    assert result.tolist() == pytest.approx([0.25, 0.25])


def test_effective_dimension_threshold_returns_first_component_count_above_threshold():
    explained = pd.Series([0.5, 0.3, 0.2], index=["PC1", "PC2", "PC3"])

    assert effective_dimension_threshold(explained, threshold=0.8) == 2
    assert effective_dimension_threshold(explained, threshold=1.0) == 3


def test_effective_dimension_threshold_validates_inputs():
    with pytest.raises(ValueError, match="threshold"):
        effective_dimension_threshold(pd.Series([1.0], index=["PC1"]), threshold=0.0)

    with pytest.raises(ValueError, match="explained_variance"):
        effective_dimension_threshold(pd.Series(dtype=float), threshold=0.9)


def test_absolute_correlation_n_eff_uses_abs_rho_to_ignore_hedge_effect():
    corr = pd.DataFrame([[1.0, -0.5], [-0.5, 1.0]], columns=["A", "B"], index=["A", "B"])

    result = absolute_correlation_n_eff(corr)

    assert result == pytest.approx(4.0 / 3.0)
