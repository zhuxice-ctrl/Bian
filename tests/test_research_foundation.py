from datetime import datetime, timedelta, timezone
import sqlite3

import numpy as np
import pandas as pd
import pytest

from trading_learning.backtest.walk_forward import StrategyRunResult, WalkForwardConfig, run_walk_forward
from trading_learning.research.guardrails import ResearchGuardrails
from trading_learning.research.hypothesis_log import (
    ALLOWED_RESEARCH_DECISIONS,
    HypothesisLog,
)
from trading_learning.research.significance import (
    bootstrap_sharpe_ci,
    is_strategy_better_than_baseline,
    sharpe_diff_significance,
)
from trading_learning.storage.db import initialize_schema


@pytest.fixture
def sqlite_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def test_hypothesis_cards_require_predicted_actual_decision_and_reason(tmp_path, sqlite_conn):
    initialize_schema(sqlite_conn)
    log = HypothesisLog(sqlite_conn, cards_dir=tmp_path)

    card = log.create(
        title="Add EMA200 trend filter",
        description="Only take long signals above EMA200.",
        parent_iteration="H-100",
        change_summary="+EMA200 filter",
        predicted={"sharpe": 0.85, "max_drawdown": -0.18, "trade_count": 80},
        decision_rule="Keep if OOS Sharpe improves by 0.10 or drawdown improves materially without Sharpe collapse.",
    )
    resolved = log.resolve(
        card.hypothesis_id,
        actual={"sharpe": 0.78, "max_drawdown": -0.11, "trade_count": 72},
        decision="risk_reduction_kept",
        reason="Sharpe was inconclusive, but OOS drawdown improved enough to keep as a risk-control variant.",
        backtest_run_id="wf-H-101",
        code_commit="abc1234",
    )

    assert ALLOWED_RESEARCH_DECISIONS == {"kept", "rejected", "inconclusive", "risk_reduction_kept", "deferred"}
    assert resolved.predicted["sharpe"] == 0.85
    assert resolved.actual["max_drawdown"] == -0.11
    assert resolved.decision == "risk_reduction_kept"
    markdown = (tmp_path / "H-001-add-ema200-trend-filter.md").read_text(encoding="utf-8")
    assert "Predicted" in markdown
    assert "Actual" in markdown
    assert "risk_reduction_kept" in markdown
    assert "Reason" in markdown


def test_hypothesis_resolve_rejects_missing_actual_or_reason(tmp_path, sqlite_conn):
    initialize_schema(sqlite_conn)
    log = HypothesisLog(sqlite_conn, cards_dir=tmp_path)
    card = log.create(
        title="Test card",
        description="A valid preregistered idea.",
        parent_iteration="baseline",
        change_summary="+one variable",
        predicted={"sharpe": 0.7},
        decision_rule="Keep if better.",
    )

    with pytest.raises(ValueError, match="actual"):
        log.resolve(card.hypothesis_id, actual={}, decision="kept", reason="missing numbers")
    with pytest.raises(ValueError, match="reason"):
        log.resolve(card.hypothesis_id, actual={"sharpe": 0.8}, decision="kept", reason="")


def test_sharpe_significance_and_four_level_verdicts():
    baseline = np.array([0.01, -0.01] * 60, dtype=float)
    identical = baseline.copy()
    candidate = np.array([0.018, -0.002] * 60, dtype=float)
    risk_control = np.array([0.004, -0.003, 0.004, -0.003] * 30, dtype=float)
    risky_baseline = np.array([0.02, -0.018, 0.02, -0.018] * 30, dtype=float)

    same = sharpe_diff_significance(baseline, identical)
    different = sharpe_diff_significance(candidate, baseline)
    verdict = is_strategy_better_than_baseline(candidate, baseline, require_significance=True)
    risk_verdict = is_strategy_better_than_baseline(risk_control, risky_baseline, require_significance=False)
    low_count = is_strategy_better_than_baseline(candidate[:10], baseline[:10], min_trade_count=50)

    assert same["p_value"] > 0.5
    assert different["p_value"] < 0.05
    assert verdict["verdict"] == "kept"
    assert risk_verdict["verdict"] == "risk_reduction_kept"
    assert low_count["verdict"] == "inconclusive"
    low, high = bootstrap_sharpe_ci(candidate, n_bootstrap=100, seed=7)
    assert low < high


def test_walk_forward_uses_non_overlapping_purged_windows():
    df = _daily_dataframe(900)
    config = WalkForwardConfig(train_window_days=120, test_window_days=60, step_days=60, purge_days=5)

    result = run_walk_forward(_constant_return_strategy, df, config)

    assert len(result.windows) >= 4
    for window in result.windows:
        assert window["train_end"] < window["test_start"]
        assert (window["test_start"] - window["train_end"]).days == 6
        assert window["test_metrics"]["trade_count"] > 0
    assert result.aggregate_metrics["oos_trade_count"] > 0
    assert "oos_sharpe" in result.aggregate_metrics


def test_walk_forward_trade_count_uses_strategy_trade_count_not_bar_count():
    df = _daily_dataframe(260)
    config = WalkForwardConfig(train_window_days=120, test_window_days=60, step_days=60, purge_days=5)

    result = run_walk_forward(_two_trade_strategy, df, config)

    assert result.aggregate_metrics["oos_bar_count"] > result.aggregate_metrics["oos_trade_count"]
    assert result.aggregate_metrics["oos_trade_count"] == 4
    assert all(window["test_metrics"]["trade_count"] == 2 for window in result.windows)


def test_walk_forward_slices_all_timeframes_with_same_window():
    frames = {
        "1h": _hourly_dataframe(24 * 40, minutes=60),
        "15m": _hourly_dataframe(24 * 4 * 40, minutes=15),
        "5m": _hourly_dataframe(24 * 12 * 40, minutes=5),
    }
    config = WalkForwardConfig(train_window_days=14, test_window_days=7, step_days=7, purge_days=1)
    seen = []

    def strategy_factory(params):
        def run(window_frames):
            assert set(window_frames) == {"1h", "15m", "5m"}
            starts = {key: value["opened_at"].min() for key, value in window_frames.items()}
            ends = {key: value["opened_at"].max() for key, value in window_frames.items()}
            seen.append((starts, ends))
            return StrategyRunResult(
                returns=np.zeros(len(window_frames["1h"])),
                trade_count=1,
                metadata={"signal_count": 1},
            )

        return run

    result = run_walk_forward(strategy_factory, frames, config, primary_timeframe="1h")

    assert result.windows
    assert seen
    for starts, ends in seen:
        assert starts["15m"] >= starts["1h"]
        assert starts["5m"] >= starts["1h"]
        assert ends["15m"] <= ends["1h"]
        assert ends["5m"] <= ends["1h"]


def test_guardrails_block_weak_decisions_and_track_oos_reuse(tmp_path):
    df = _daily_dataframe(900)
    config = WalkForwardConfig(train_window_days=120, test_window_days=60, step_days=60, purge_days=5)
    wf_result = run_walk_forward(_constant_return_strategy, df, config)
    card = type("Card", (), {"hypothesis_id": "H-101", "decision": "kept"})()

    accepted = ResearchGuardrails.validate_decision(card, wf_result, registry_path=tmp_path / "oos.json")
    reused = ResearchGuardrails.validate_decision(card, wf_result, registry_path=tmp_path / "oos.json")

    assert accepted["allowed"] is True
    assert reused["allowed"] is False
    assert "OOS" in reused["reasons"][0]


def _daily_dataframe(count):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        close = 100 + index * 0.2
        rows.append(
            {
                "opened_at": start + timedelta(days=index),
                "open": close - 0.1,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 10,
            }
        )
    return pd.DataFrame(rows)


def _hourly_dataframe(count, *, minutes):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        close = 100 + index * 0.01
        rows.append(
            {
                "opened_at": start + timedelta(minutes=minutes * index),
                "open": close - 0.1,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 10,
            }
        )
    return pd.DataFrame(rows)


def _constant_return_strategy(params):
    daily_return = float(params.get("daily_return", 0.001))

    def run(frame):
        return pd.Series([daily_return] * len(frame), index=frame.index)

    return run


def _two_trade_strategy(params):
    def run(frame):
        returns = np.zeros(len(frame))
        if len(frame) >= 20:
            returns[10] = 0.02
            returns[-1] = -0.01
        return StrategyRunResult(returns=returns, trade_count=2, metadata={"signal_count": 4})

    return run
