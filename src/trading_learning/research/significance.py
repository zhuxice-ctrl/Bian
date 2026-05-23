from __future__ import annotations

import math
from typing import Any

import numpy as np


def sharpe_diff_significance(
    returns_a: np.ndarray,
    returns_b: np.ndarray,
    confidence: float = 0.95,
) -> dict[str, Any]:
    a = _clean_returns(returns_a)
    b = _clean_returns(returns_b)
    length = min(len(a), len(b))
    if length < 2:
        raise ValueError("at least two paired returns are required")
    a = a[:length]
    b = b[:length]
    sharpe_a = _sharpe(a)
    sharpe_b = _sharpe(b)
    diff = sharpe_a - sharpe_b
    paired = a - b
    if float(np.std(paired, ddof=1)) == 0:
        p_value = 1.0 if diff == 0 else 0.0
        ci_low = diff
        ci_high = diff
    else:
        se = float(np.std(paired, ddof=1) / math.sqrt(length))
        mean_diff = float(np.mean(paired))
        z = mean_diff / se
        p_value = math.erfc(abs(z) / math.sqrt(2))
        zcrit = _normal_critical(confidence)
        ci_low = diff - zcrit * se
        ci_high = diff + zcrit * se
    return {
        "sharpe_a": sharpe_a,
        "sharpe_b": sharpe_b,
        "diff": diff,
        "p_value": p_value,
        "significant_at_95": p_value < 0.05,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


def bootstrap_sharpe_ci(
    returns: np.ndarray,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> tuple[float, float]:
    values = _clean_returns(returns)
    if len(values) < 2:
        raise ValueError("at least two returns are required")
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n_bootstrap):
        sample = rng.choice(values, size=len(values), replace=True)
        samples.append(_sharpe(sample))
    alpha = 1 - confidence
    return (
        float(np.quantile(samples, alpha / 2)),
        float(np.quantile(samples, 1 - alpha / 2)),
    )


def is_strategy_better_than_baseline(
    candidate_returns: np.ndarray,
    baseline_returns: np.ndarray,
    min_trade_count: int = 50,
    min_sharpe_diff: float = 0.1,
    require_significance: bool = True,
) -> dict[str, Any]:
    candidate = _clean_returns(candidate_returns)
    baseline = _clean_returns(baseline_returns)
    metrics = sharpe_diff_significance(candidate, baseline)
    metrics["candidate_max_drawdown"] = _max_drawdown(candidate)
    metrics["baseline_max_drawdown"] = _max_drawdown(baseline)
    metrics["candidate_volatility"] = float(np.std(candidate, ddof=1)) if len(candidate) > 1 else 0.0
    metrics["baseline_volatility"] = float(np.std(baseline, ddof=1)) if len(baseline) > 1 else 0.0

    reasons: list[str] = []
    if min(len(candidate), len(baseline)) < min_trade_count:
        return {"verdict": "inconclusive", "reasons": ["trade count is below decision threshold"], "metrics": metrics}

    drawdown_improved = metrics["candidate_max_drawdown"] > metrics["baseline_max_drawdown"] * 0.75
    volatility_reduced = metrics["candidate_volatility"] < metrics["baseline_volatility"] * 0.75
    if drawdown_improved and volatility_reduced:
        reasons.append("risk profile improved enough to keep as risk-control variant")
        return {"verdict": "risk_reduction_kept", "reasons": reasons, "metrics": metrics}

    if metrics["diff"] >= min_sharpe_diff and (not require_significance or metrics["p_value"] < 0.05):
        return {"verdict": "kept", "reasons": ["Sharpe improvement passed the decision rule"], "metrics": metrics}
    if metrics["diff"] < 0:
        return {"verdict": "rejected", "reasons": ["candidate Sharpe was worse than baseline"], "metrics": metrics}
    return {"verdict": "inconclusive", "reasons": ["improvement did not clear the decision rule"], "metrics": metrics}


def _clean_returns(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype="float64")
    return array[np.isfinite(array)]


def _sharpe(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    std = float(np.std(values, ddof=1))
    if std == 0:
        return 0.0 if float(np.mean(values)) == 0 else math.copysign(float("inf"), float(np.mean(values)))
    return float(np.mean(values) / std * math.sqrt(252))


def _max_drawdown(values: np.ndarray) -> float:
    equity = np.cumprod(1 + values)
    peaks = np.maximum.accumulate(equity)
    drawdowns = equity / peaks - 1
    return float(np.min(drawdowns)) if len(drawdowns) else 0.0


def _normal_critical(confidence: float) -> float:
    if confidence >= 0.99:
        return 2.575829
    if confidence >= 0.95:
        return 1.959964
    if confidence >= 0.90:
        return 1.644854
    return 1.959964
