import pandas as pd
import pytest

from trading_learning.backtest.engine import combine_forecasts, compute_fdm


def test_compute_fdm_is_one_for_perfectly_correlated_forecasts():
    forecasts = pd.DataFrame(
        {
            "a": [1.0, 2.0, 3.0, 4.0],
            "b": [2.0, 4.0, 6.0, 8.0],
            "c": [3.0, 6.0, 9.0, 12.0],
            "d": [0.5, 1.0, 1.5, 2.0],
        }
    )

    assert compute_fdm(forecasts) == pytest.approx(1.0)


def test_compute_fdm_is_sqrt_n_for_uncorrelated_forecasts():
    forecasts = _orthogonal_forecasts()

    assert compute_fdm(forecasts) == pytest.approx(2.0)


def test_compute_fdm_increases_above_sqrt_n_when_average_correlation_is_negative():
    forecasts = _orthogonal_forecasts()
    forecasts["d"] = -(forecasts["a"] + forecasts["b"] + forecasts["c"]) + 0.25 * forecasts["d"]

    assert compute_fdm(forecasts) > 2.0


def test_combine_forecasts_without_fdm_matches_simple_mean():
    forecasts = pd.DataFrame(
        {
            "a": [1.0, 0.0, -1.0],
            "b": [0.5, 0.0, -0.5],
            "c": [0.0, 0.0, 0.0],
            "d": [-0.5, 0.0, 0.5],
        }
    )

    result = combine_forecasts(forecasts, apply_fdm=False)

    pd.testing.assert_series_equal(result, forecasts.mean(axis=1).rename("combined_forecast"))


def test_combine_forecasts_clips_adjusted_forecast_to_cap():
    forecasts = pd.DataFrame(
        {
            "a": [2.0, -2.0],
            "b": [2.0, -2.0],
            "c": [2.0, -2.0],
            "d": [2.0, -2.0],
        }
    )

    result = combine_forecasts(forecasts, apply_fdm=True, forecast_cap=1.0)

    assert result.max() <= 1.0
    assert result.min() >= -1.0


def _orthogonal_forecasts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "a": [1.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0, -1.0],
            "b": [1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0],
            "c": [1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0],
            "d": [1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0],
        }
    )
