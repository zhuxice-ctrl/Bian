import math

import numpy as np
import pandas as pd
import pytest

from trading_learning.metrics import (
    cagr,
    calmar_ratio,
    equity_curve,
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    volatility,
    win_rate,
)


def test_sharpe_ratio_matches_known_sample_std_formula():
    result = sharpe_ratio([0.01, 0.02, -0.01, 0.0], periods_per_year=4)

    assert result == pytest.approx(0.7745966692)


def test_sharpe_ratio_returns_nan_for_empty_single_or_zero_variance():
    assert math.isnan(sharpe_ratio([]))
    assert math.isnan(sharpe_ratio([0.01]))
    assert math.isnan(sharpe_ratio([0.0, 0.0, 0.0]))


def test_sharpe_ratio_handles_pandas_and_tiny_variance():
    result = sharpe_ratio(pd.Series([1.0e-9, 2.0e-9, -1.0e-9]), periods_per_year=365)

    assert math.isfinite(result)


def test_sortino_ratio_matches_downside_deviation_formula():
    result = sortino_ratio([0.1, -0.05, 0.02, -0.01], periods_per_year=4)

    assert result == pytest.approx(1.1766968108)


def test_sortino_ratio_returns_nan_without_downside_risk_or_inputs():
    assert math.isnan(sortino_ratio([]))
    assert math.isnan(sortino_ratio([0.02]))
    assert math.isnan(sortino_ratio([0.01, 0.02, 0.03]))


def test_sortino_ratio_handles_extreme_values_without_overflow():
    result = sortino_ratio(np.array([1.0e6, -2.0e5, 3.0e5, -1.0e5]), periods_per_year=12)

    assert math.isfinite(result)


def test_calmar_ratio_matches_cagr_over_absolute_drawdown():
    result = calmar_ratio([100.0, 120.0, 90.0, 130.0], periods_per_year=3)

    assert result == pytest.approx(1.2)


def test_calmar_ratio_returns_nan_for_empty_single_or_no_drawdown():
    assert math.isnan(calmar_ratio([]))
    assert math.isnan(calmar_ratio([100.0]))
    assert math.isnan(calmar_ratio([100.0, 110.0, 120.0]))


def test_calmar_ratio_handles_large_equity_values():
    result = calmar_ratio([1.0e12, 1.1e12, 1.0e12, 1.2e12], periods_per_year=3)

    assert result == pytest.approx(2.2)


def test_max_drawdown_returns_worst_fraction_and_duration():
    drawdown, duration = max_drawdown([100.0, 120.0, 90.0, 80.0, 130.0, 125.0, 140.0])

    assert drawdown == pytest.approx(-1.0 / 3.0)
    assert duration == 2


def test_max_drawdown_handles_empty_single_and_monotonic_curves():
    drawdown, duration = max_drawdown([])
    assert math.isnan(drawdown)
    assert duration == 0
    assert max_drawdown([100.0]) == (0.0, 0)
    assert max_drawdown([100.0, 110.0, 120.0]) == (0.0, 0)


def test_max_drawdown_ignores_nan_and_handles_extreme_values():
    drawdown, duration = max_drawdown([1.0e12, np.nan, 5.0e11, 1.5e12])

    assert drawdown == pytest.approx(-0.5)
    assert duration == 1


def test_cagr_matches_compound_growth_formula():
    result = cagr([100.0, 110.0, 121.0], periods_per_year=1)

    assert result == pytest.approx(0.1)


def test_cagr_returns_nan_for_empty_single_or_non_positive_equity():
    assert math.isnan(cagr([]))
    assert math.isnan(cagr([100.0]))
    assert math.isnan(cagr([0.0, 100.0]))
    assert math.isnan(cagr([100.0, -1.0]))


def test_cagr_handles_large_equity_values():
    result = cagr(np.array([1.0e9, 1.21e9]), periods_per_year=0.5)

    assert result == pytest.approx(0.1)


def test_volatility_matches_annualized_sample_std():
    result = volatility([0.01, 0.02, -0.01, 0.0], periods_per_year=4)

    assert result == pytest.approx(0.02581988897)


def test_volatility_returns_nan_for_empty_or_single_and_zero_for_flat_returns():
    assert math.isnan(volatility([]))
    assert math.isnan(volatility([0.01]))
    assert volatility([0.0, 0.0, 0.0]) == 0.0


def test_volatility_handles_tiny_returns():
    result = volatility(np.array([1.0e-12, 2.0e-12, -1.0e-12]), periods_per_year=525600)

    assert math.isfinite(result)
    assert result > 0.0


def test_win_rate_counts_positive_trades_over_all_trades():
    assert win_rate([10.0, -5.0, 0.0, 2.0]) == pytest.approx(0.5)


def test_win_rate_returns_zero_for_empty_or_no_winners():
    assert win_rate([]) == 0.0
    assert win_rate([-1.0, -2.0, 0.0]) == 0.0


def test_win_rate_handles_large_trade_pnls():
    assert win_rate(np.array([1.0e12, -1.0e12, 1.0])) == pytest.approx(2.0 / 3.0)


def test_profit_factor_divides_gross_profit_by_gross_loss():
    assert profit_factor([10.0, -5.0, 0.0, 2.0]) == pytest.approx(2.4)


def test_profit_factor_handles_empty_zero_and_lossless_cases():
    assert profit_factor([]) == 0.0
    assert profit_factor([0.0, 0.0]) == 0.0
    assert profit_factor([-2.0, -3.0]) == 0.0
    assert math.isinf(profit_factor([1.0, 2.0]))


def test_profit_factor_handles_large_trade_pnls():
    assert profit_factor(np.array([1.0e12, -2.0e11, 3.0e11])) == pytest.approx(6.5)


def test_equity_curve_compounds_returns_from_initial_capital():
    curve = equity_curve([0.1, -0.05, 0.0], initial_capital=100.0)

    assert np.allclose(curve.to_numpy(), np.array([100.0, 110.0, 104.5, 104.5]))


def test_equity_curve_returns_initial_capital_for_empty_input():
    curve = equity_curve([], initial_capital=250.0)

    assert np.allclose(curve.to_numpy(), np.array([250.0]))


def test_equity_curve_handles_pandas_input_and_extreme_returns():
    curve = equity_curve(pd.Series([1.0, -0.5, 0.25]), initial_capital=1.0e9)

    assert np.allclose(curve.to_numpy(), np.array([1.0e9, 2.0e9, 1.0e9, 1.25e9]))


def test_root_package_exposes_public_metric_functions():
    import trading_learning as tl

    assert tl.sharpe_ratio is sharpe_ratio
    assert tl.sortino_ratio is sortino_ratio
    assert tl.calmar_ratio is calmar_ratio
    assert tl.max_drawdown is max_drawdown
    assert tl.cagr is cagr
    assert tl.volatility is volatility
    assert tl.win_rate is win_rate
    assert tl.profit_factor is profit_factor
    assert tl.equity_curve is equity_curve
