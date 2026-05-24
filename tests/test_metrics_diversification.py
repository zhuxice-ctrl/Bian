import numpy as np
import pandas as pd
import pytest

from trading_learning.metrics.diversification import (
    effective_n_bets,
    pairwise_correlation,
    rolling_correlation,
)


def test_effective_n_bets_identity_matrix_equals_number_of_assets():
    corr = pd.DataFrame(np.eye(4), columns=list("ABCD"), index=list("ABCD"))

    result = effective_n_bets(corr)

    assert result == pytest.approx(4.0)


def test_effective_n_bets_all_ones_matrix_equals_one():
    corr = pd.DataFrame(np.ones((4, 4)), columns=list("ABCD"), index=list("ABCD"))

    result = effective_n_bets(corr)

    assert result == pytest.approx(1.0)


def test_effective_n_bets_known_two_by_two_matrix_with_half_correlation():
    corr = pd.DataFrame([[1.0, 0.5], [0.5, 1.0]], columns=["A", "B"], index=["A", "B"])

    result = effective_n_bets(corr)

    assert result == pytest.approx(4.0 / 3.0)


def test_effective_n_bets_uses_supplied_weights():
    corr = pd.DataFrame(np.eye(2), columns=["A", "B"], index=["A", "B"])

    result = effective_n_bets(corr, weights=pd.Series([0.75, 0.25], index=["A", "B"]))

    assert result == pytest.approx(1.0 / (0.75**2 + 0.25**2))


def test_pairwise_correlation_matches_pandas_for_pearson_and_spearman():
    returns = pd.DataFrame(
        {
            "A": [0.01, 0.02, 0.03, 0.04],
            "B": [0.02, 0.04, 0.06, 0.08],
            "C": [0.04, 0.03, 0.02, 0.01],
        }
    )

    pearson = pairwise_correlation(returns, method="pearson")
    spearman = pairwise_correlation(returns, method="spearman")

    pd.testing.assert_frame_equal(pearson, returns.corr(method="pearson"))
    pd.testing.assert_frame_equal(spearman, returns.corr(method="spearman"))


def test_pairwise_correlation_rejects_unknown_method():
    with pytest.raises(ValueError, match="method"):
        pairwise_correlation(pd.DataFrame({"A": [0.01, 0.02]}), method="kendall")


def test_rolling_correlation_matches_pandas_rolling_corr():
    returns_a = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    returns_b = pd.Series([1.0, 4.0, 9.0, 16.0, 25.0])

    result = rolling_correlation(returns_a, returns_b, window=3)

    expected = returns_a.rolling(3).corr(returns_b)
    pd.testing.assert_series_equal(result, expected)


def test_rolling_correlation_rejects_non_positive_window():
    with pytest.raises(ValueError, match="window"):
        rolling_correlation(pd.Series([1.0]), pd.Series([1.0]), window=0)
