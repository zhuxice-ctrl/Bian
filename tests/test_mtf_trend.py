from datetime import datetime, timedelta, timezone

import pandas as pd

from trading_learning.strategy.mtf_trend import MTFTrendConfig, generate_mtf_trend_signals, mtf_trend_strategy_factory


def test_mtf_trend_builds_variants_one_variable_at_a_time():
    frames = {
        "1h": _frame([100] * 210 + [105, 108, 112, 116, 120]),
        "15m": _frame([100, 99, 98, 97, 101] * 50, minutes=15),
        "5m": _frame([100, 101, 102, 103, 104] * 80, minutes=5),
    }
    config = MTFTrendConfig(ema_long=200, ema_short=20, rsi_oversold=35)

    baseline = generate_mtf_trend_signals(frames, config=config, phase="6.1")
    full = generate_mtf_trend_signals(frames, config=config, phase="6.6")

    assert not baseline.empty
    assert set(full["phase"]) == {"6.6"}
    assert {"stop_loss", "take_profit", "risk_fraction"}.issubset(full.columns)
    assert full["reason"].str.contains("EMA200").any()
    assert full["reason"].str.contains("ATR stop").any()


def test_mtf_trend_ema200_filter_can_suppress_baseline_buy():
    frames = {
        "1h": _frame([200] * 200 + [100, 140, 160, 170, 180]),
        "15m": _frame([90, 89, 88, 87, 91] * 50, minutes=15),
        "5m": _frame([90, 91, 92, 93, 94] * 80, minutes=5),
    }
    config = MTFTrendConfig(ema_long=200, ema_short=3)

    baseline = generate_mtf_trend_signals(frames, config=config, phase="6.1")
    filtered = generate_mtf_trend_signals(frames, config=config, phase="6.2")

    assert not baseline.empty
    assert filtered.empty


def test_mtf_trend_strategy_factory_returns_oos_returns():
    frame = _frame([100, 101, 102, 101, 103, 105, 104, 106, 108, 110] * 30)
    strategy = mtf_trend_strategy_factory({"phase": "6.1", "ema_short": 3, "ema_long": 8})

    returns = strategy(frame)

    assert len(returns.returns) == len(frame)
    assert returns.trade_count > 0
    assert returns.metadata["signal_count"] >= returns.trade_count
    assert returns.metadata["cost_model"]["fee_rate"] == 0.0008
    assert abs(returns.returns).sum() > 0


def test_mtf_trend_uses_real_multitimeframe_frames_and_can_defer_missing_frames():
    frames = {
        "1h": _frame([100] * 210 + [105, 108, 112, 116, 120]),
        "15m": _frame([100, 99, 98, 97, 101] * 55, minutes=15),
        "5m": _frame([100, 101, 102, 103, 104] * 165, minutes=5),
    }
    strategy = mtf_trend_strategy_factory({"phase": "6.4", "ema_short": 20, "ema_long": 200})

    result = strategy(frames)
    missing = strategy({"1h": frames["1h"]})

    assert result.metadata["timeframes_used"] == ["1h", "15m"]
    assert result.metadata["deferred"] is False
    assert missing.metadata["deferred"] is True
    assert missing.trade_count == 0


def test_mtf_trend_cost_model_reduces_returns():
    frame = _frame([100, 101, 102, 101, 103, 105, 104, 106, 108, 110] * 30)
    no_cost = mtf_trend_strategy_factory(
        {"phase": "6.1", "ema_short": 3, "ema_long": 8, "fee_rate": 0, "slippage_rate": 0}
    )(frame)
    with_cost = mtf_trend_strategy_factory({"phase": "6.1", "ema_short": 3, "ema_long": 8})(frame)

    assert no_cost.trade_count == with_cost.trade_count
    assert with_cost.returns.sum() < no_cost.returns.sum()


def _frame(closes, *, minutes=60):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index, close in enumerate(closes):
        rows.append(
            {
                "opened_at": start + timedelta(minutes=minutes * index),
                "open": close - 0.5,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 10,
            }
        )
    return pd.DataFrame(rows)
