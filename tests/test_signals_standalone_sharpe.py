import pandas as pd

from trading_learning.signals.standalone_sharpe import signal_standalone_sharpe


def test_signal_standalone_sharpe_is_positive_for_positive_alpha():
    forecast = pd.Series([1.0, -1.0, 0.5, -0.5], index=pd.date_range("2026-01-01", periods=4, tz="UTC"))
    next_return = pd.Series([0.01, -0.02, 0.015, -0.01], index=forecast.index)

    result = signal_standalone_sharpe(forecast, next_return, periods_per_year=365)

    assert result > 0.0


def test_signal_standalone_sharpe_is_negative_for_negative_alpha():
    forecast = pd.Series([1.0, -1.0, 0.5, -0.5], index=pd.date_range("2026-01-01", periods=4, tz="UTC"))
    next_return = pd.Series([-0.01, 0.02, -0.015, 0.01], index=forecast.index)

    result = signal_standalone_sharpe(forecast, next_return, periods_per_year=365)

    assert result < 0.0


def test_signal_standalone_sharpe_is_zero_for_zero_alpha():
    forecast = pd.Series([1.0, -1.0, 0.5, -0.5], index=pd.date_range("2026-01-01", periods=4, tz="UTC"))
    next_return = pd.Series([0.0, 0.0, 0.0, 0.0], index=forecast.index)

    result = signal_standalone_sharpe(forecast, next_return, periods_per_year=365)

    assert result == 0.0
