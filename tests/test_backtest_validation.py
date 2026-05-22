from datetime import datetime, timedelta, timezone

from trading_learning.backtest.validation import filter_candles_by_date
from trading_learning.backtest.validation import split_train_test
from trading_learning.backtest.validation import stress_windows
from trading_learning.backtest.validation import validation_warning
from trading_learning.models import Candle


def _candles(count=10):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    return [
        Candle(
            symbol="BTCUSDT",
            opened_at=start + timedelta(hours=index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100 + index,
            volume=10,
        )
        for index in range(count)
    ]


def test_filter_candles_by_date_keeps_selected_range():
    candles = filter_candles_by_date(
        _candles(5),
        start="2026-05-01T01:00:00+00:00",
        end="2026-05-01T03:00:00+00:00",
    )

    assert [candle.opened_at.hour for candle in candles] == [1, 2, 3]


def test_split_train_test_uses_ratio_boundaries():
    train, test = split_train_test(_candles(10), train_ratio=0.6)

    assert len(train) == 6
    assert len(test) == 4
    assert train[-1].opened_at.hour == 5
    assert test[0].opened_at.hour == 6


def test_stress_windows_rank_large_moves():
    candles = _candles(6)
    candles[3] = Candle("BTCUSDT", candles[3].opened_at, 120, 130, 90, 80, 10)

    windows = stress_windows(candles, window_size=3, top_n=1)

    assert len(windows) == 1
    assert windows[0]["max_abs_move_pct"] > 0.2
    assert windows[0]["start"] in {candles[1].opened_at.isoformat(), candles[2].opened_at.isoformat(), candles[3].opened_at.isoformat()}


def test_validation_warning_flags_weak_out_of_sample():
    warning = validation_warning(train_pnl=10, test_pnl=-2, stress_window_count=1)

    assert "out-of-sample" in warning
