from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from trading_learning.strategy.pairs_trading.strategy import (
    PairsTradingConfig,
    PairsTradingStrategy,
    pairs_strategy_factory,
)


def test_no_signal_when_zscore_in_band():
    strategy = _fitted_strategy(latest_z=0.8)

    signal = strategy.generate_signal(strategy.training_a, strategy.training_b, {})

    assert signal.direction == "flat"
    assert signal.asset_a_action == "hold"
    assert signal.asset_b_action == "hold"


def test_long_spread_when_zscore_below_neg_threshold():
    strategy = _fitted_strategy(latest_z=-2.2)

    signal = strategy.generate_signal(strategy.training_a, strategy.training_b, {})

    assert signal.direction == "long_spread"
    assert signal.asset_a_action == "buy"
    assert signal.asset_b_action == "sell"
    assert signal.asset_a_qty > 0
    assert signal.asset_b_qty > 0


def test_short_spread_when_zscore_above_threshold():
    strategy = _fitted_strategy(latest_z=2.3)

    signal = strategy.generate_signal(strategy.training_a, strategy.training_b, {})

    assert signal.direction == "short_spread"
    assert signal.asset_a_action == "sell"
    assert signal.asset_b_action == "buy"


def test_stop_loss_triggers():
    strategy = _fitted_strategy(latest_z=3.8)

    signal = strategy.generate_signal(strategy.training_a, strategy.training_b, {"direction": "short_spread"})

    assert signal.direction == "stop"


def test_exit_when_zscore_returns_to_zero():
    strategy = _fitted_strategy(latest_z=0.1)

    signal = strategy.generate_signal(strategy.training_a, strategy.training_b, {"direction": "long_spread"})

    assert signal.direction == "exit"


def test_no_trade_when_cointegration_p_value_high():
    strategy = _fitted_strategy(latest_z=2.5)
    strategy.training_stats["is_enabled"] = False
    strategy.training_stats["coint_p"] = 0.4

    signal = strategy.generate_signal(strategy.training_a, strategy.training_b, {})

    assert signal.direction == "flat"
    assert signal.rationale["skip_reason"] == "cointegration_or_half_life_filter"


def test_no_trade_when_half_life_exceeds_max():
    strategy = _fitted_strategy(latest_z=2.5)
    strategy.training_stats["is_enabled"] = False
    strategy.training_stats["half_life"] = 999

    signal = strategy.generate_signal(strategy.training_a, strategy.training_b, {})

    assert signal.direction == "flat"
    assert signal.rationale["skip_reason"] == "cointegration_or_half_life_filter"


def test_pairs_round_trip_cost_calculation_correct():
    strategy = PairsTradingStrategy(PairsTradingConfig(capital_per_trade=100, fee_rate=0.0008, slippage_rate=0.0005, latency_rate=0.0002))

    cost = strategy.round_trip_cost(asset_a_price=100, asset_b_price=50, asset_a_qty=0.5, asset_b_qty=1.0)

    assert cost == 4 * 50 * (0.0008 + 0.0005 + 0.0002)


def test_pairs_strategy_factory_returns_real_trade_count_not_bar_count():
    df_a, df_b = _paired_frames()
    runner = pairs_strategy_factory({"phase": "H-200", "zscore_window": 30, "entry_threshold": 1.2, "exit_threshold": 0.2})

    result = runner({"BTCUSDT": df_a, "ETHUSDT": df_b})

    assert result.trade_count > 0
    assert result.trade_count < len(result.returns)
    assert result.metadata["pair"] == "BTCUSDT-ETHUSDT"
    assert result.metadata["cost_model"]["fee_rate"] == 0.0008


def _fitted_strategy(latest_z: float):
    df_a, df_b = _paired_frames()
    config = PairsTradingConfig(zscore_window=30, entry_threshold=2.0, exit_threshold=0.3)
    strategy = PairsTradingStrategy(config)
    strategy.fit_on_training(df_a, df_b)
    strategy.training_a = df_a
    strategy.training_b = df_b
    strategy.training_stats["is_enabled"] = True
    strategy.training_stats["latest_zscore"] = latest_z
    return strategy


def _paired_frames(count: int = 520):
    rng = np.random.default_rng(22)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    log_b = np.log(2000) + np.cumsum(rng.normal(0, 0.01, count))
    spread = np.zeros(count)
    for index in range(1, count):
        spread[index] = 0.92 * spread[index - 1] + rng.normal(0, 0.025)
    spread[100:105] -= 0.12
    spread[220:225] += 0.14
    log_a = 0.4 + 1.15 * log_b + spread
    return _frame(np.exp(log_a), start, "BTCUSDT"), _frame(np.exp(log_b), start, "ETHUSDT")


def _frame(values, start, symbol):
    rows = []
    for index, close in enumerate(values):
        rows.append(
            {
                "opened_at": start + timedelta(hours=index),
                "symbol": symbol,
                "open": close * 0.999,
                "high": close * 1.002,
                "low": close * 0.998,
                "close": close,
                "volume": 100,
            }
        )
    return pd.DataFrame(rows)
