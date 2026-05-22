import json
import math
from pathlib import Path

import pandas as pd
import pytest

from trading_learning.strategy.indicators import atr, ema, rsi, slope


def _fixture():
    return json.loads(Path("tests/fixtures/indicators_golden.json").read_text(encoding="utf-8"))


def _assert_series_matches(actual, expected):
    assert len(actual) == len(expected)
    for index, expected_value in enumerate(expected):
        value = actual.iloc[index]
        if expected_value is None:
            assert math.isnan(value)
        else:
            assert value == pytest.approx(expected_value, abs=1e-6)


def test_indicators_match_fixed_golden_fixture():
    data = _fixture()
    close = pd.Series(data["input"]["close"], dtype="float64")
    high = pd.Series(data["input"]["high"], dtype="float64")
    low = pd.Series(data["input"]["low"], dtype="float64")

    _assert_series_matches(ema(close, 20), data["ema_20"])
    _assert_series_matches(rsi(close, 14), data["rsi_14"])
    _assert_series_matches(atr(high, low, close, 14), data["atr_14"])
    _assert_series_matches(slope(close, 5), data["slope_5"])


def test_indicators_do_not_change_past_values_when_future_data_changes():
    data = _fixture()
    close = pd.Series(data["input"]["close"], dtype="float64")
    high = pd.Series(data["input"]["high"], dtype="float64")
    low = pd.Series(data["input"]["low"], dtype="float64")
    close_changed = close.copy()
    high_changed = high.copy()
    low_changed = low.copy()
    close_changed.iloc[-1] = 10000
    high_changed.iloc[-1] = 10001
    low_changed.iloc[-1] = 9999

    cutoff = len(close) - 1
    pd.testing.assert_series_equal(ema(close, 20).iloc[:cutoff], ema(close_changed, 20).iloc[:cutoff])
    pd.testing.assert_series_equal(rsi(close, 14).iloc[:cutoff], rsi(close_changed, 14).iloc[:cutoff])
    pd.testing.assert_series_equal(atr(high, low, close, 14).iloc[:cutoff], atr(high_changed, low_changed, close_changed, 14).iloc[:cutoff])
    pd.testing.assert_series_equal(slope(close, 5).iloc[:cutoff], slope(close_changed, 5).iloc[:cutoff])
