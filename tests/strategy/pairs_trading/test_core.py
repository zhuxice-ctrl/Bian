from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trading_learning.strategy.pairs_trading.cointegration import adf_test, engle_granger_test
from trading_learning.strategy.pairs_trading.half_life import estimate_half_life
from trading_learning.strategy.pairs_trading.hedge_ratio import rolling_hedge_ratio, static_hedge_ratio
from trading_learning.strategy.pairs_trading.spread import compute_spread, rolling_zscore


def test_engle_granger_detects_synthetic_cointegration():
    asset_a, asset_b, alpha, beta, _ = _cointegrated_pair()

    result = engle_granger_test(asset_a, asset_b)

    assert result["is_cointegrated"] is True
    assert result["adf_p_value"] < 0.05
    assert result["alpha"] == pytest.approx(alpha, abs=0.08)
    assert result["beta"] == pytest.approx(beta, rel=0.05)
    assert len(result["residuals"]) == len(asset_a)


def test_engle_granger_rejects_non_cointegrated_random_walks():
    rng = np.random.default_rng(11)
    asset_a = pd.Series(100 + np.cumsum(rng.normal(0, 1, 600)))
    asset_b = pd.Series(90 + np.cumsum(rng.normal(0, 1, 600)))

    result = engle_granger_test(asset_a, asset_b)

    assert result["is_cointegrated"] is False
    assert result["adf_p_value"] > 0.05


def test_adf_identifies_stationary_and_unit_root_series():
    rng = np.random.default_rng(12)
    stationary = pd.Series(rng.normal(0, 1, 500))
    unit_root = pd.Series(np.cumsum(rng.normal(0, 1, 500)))

    assert adf_test(stationary)["p_value"] < 0.05
    assert adf_test(unit_root)["p_value"] > 0.05


def test_half_life_estimate_matches_known_ou_process():
    _, _, _, _, spread = _cointegrated_pair(theta=0.08, count=1600)

    half_life = estimate_half_life(spread)

    assert half_life == pytest.approx(np.log(2) / 0.08, rel=0.05)


def test_spread_and_hedge_ratio_recover_synthetic_beta():
    asset_a, asset_b, alpha, beta, _ = _cointegrated_pair()

    estimated_beta = static_hedge_ratio(np.log(asset_a), np.log(asset_b))
    spread = compute_spread(asset_a, asset_b, alpha=alpha, beta=beta)
    rolling_beta = rolling_hedge_ratio(np.log(asset_a), np.log(asset_b), window=120)

    assert estimated_beta == pytest.approx(beta, rel=0.05)
    assert abs(float(spread.mean())) < 0.1
    assert rolling_beta.dropna().iloc[-1] == pytest.approx(beta, rel=0.08)


def test_rolling_zscore_has_no_lookahead():
    spread = pd.Series(np.linspace(-1, 1, 120))
    changed_future = spread.copy()
    changed_future.iloc[-1] = 100

    original = rolling_zscore(spread, window=30)
    changed = rolling_zscore(changed_future, window=30)

    pd.testing.assert_series_equal(original.iloc[:-1], changed.iloc[:-1])


def _cointegrated_pair(*, theta: float = 0.12, count: int = 800):
    rng = np.random.default_rng(7)
    alpha = 0.45
    beta = 1.25
    log_b = np.log(100) + np.cumsum(rng.normal(0, 0.01, count))
    spread = np.zeros(count)
    for index in range(1, count):
        spread[index] = (1 - theta) * spread[index - 1] + rng.normal(0, 0.015)
    log_a = alpha + beta * log_b + spread
    return pd.Series(np.exp(log_a)), pd.Series(np.exp(log_b)), alpha, beta, pd.Series(spread)
