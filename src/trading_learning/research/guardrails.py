from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ResearchGuardrails:
    MIN_TRADE_COUNT_FOR_DECISION = 30
    MIN_OOS_WINDOWS_FOR_DECISION = 4
    MAX_PARAM_GRID_SIZE = 50
    OOS_DATA_USE_LIMIT = 1

    @classmethod
    def validate_decision(cls, hypothesis_card, wf_result, *, registry_path: Path | str = "data/local/research/oos_usage.json") -> dict[str, Any]:
        reasons: list[str] = []
        if len(wf_result.windows) < cls.MIN_OOS_WINDOWS_FOR_DECISION:
            reasons.append("walk-forward has too few OOS windows for a decision")
        if int(wf_result.aggregate_metrics.get("oos_trade_count", 0)) < cls.MIN_TRADE_COUNT_FOR_DECISION:
            reasons.append("OOS trade count is below the decision threshold")
        fingerprint = _fingerprint_oos_windows(wf_result.windows)
        registry_file = Path(registry_path)
        usage = _read_usage(registry_file)
        count = int(usage.get(fingerprint, 0))
        if count >= cls.OOS_DATA_USE_LIMIT:
            reasons.append("OOS data range was already used for a decision; wait for fresh data")
        allowed = not reasons
        if allowed:
            registry_file.parent.mkdir(parents=True, exist_ok=True)
            usage[fingerprint] = count + 1
            registry_file.write_text(json.dumps(usage, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "allowed": allowed,
            "reasons": reasons,
            "fingerprint": fingerprint,
            "hypothesis_id": getattr(hypothesis_card, "hypothesis_id", ""),
        }

    @classmethod
    def validate_param_grid(cls, param_grid: dict[str, list[Any]] | None) -> dict[str, Any]:
        if not param_grid:
            return {"allowed": True, "size": 1, "reasons": []}
        size = 1
        for values in param_grid.values():
            size *= len(values)
        if size > cls.MAX_PARAM_GRID_SIZE:
            return {"allowed": False, "size": size, "reasons": ["parameter grid is too large"]}
        return {"allowed": True, "size": size, "reasons": []}


class PairsGuardrails:
    MIN_COINTEGRATION_P = 0.05
    MAX_HALF_LIFE_PERIODS = 480
    MIN_TRADES_FOR_DECISION = 30
    MIN_OOS_WINDOWS = 4

    @classmethod
    def validate_training(cls, stats: dict[str, Any]) -> dict[str, Any]:
        reasons: list[str] = []
        coint_p = float(stats.get("coint_p", 1.0))
        half_life = float(stats.get("half_life", float("inf")))
        if coint_p > cls.MIN_COINTEGRATION_P:
            reasons.append("cointegration p-value is above threshold")
        if half_life > cls.MAX_HALF_LIFE_PERIODS:
            reasons.append("half-life exceeds maximum tradable periods")
        if reasons:
            return {"decision": "deferred", "enabled": False, "reasons": reasons}
        return {"decision": "enabled", "enabled": True, "reasons": []}

    @classmethod
    def validate_decision_metrics(cls, *, trade_count: int, oos_windows: int) -> dict[str, Any]:
        reasons: list[str] = []
        if trade_count < cls.MIN_TRADES_FOR_DECISION:
            reasons.append("OOS trade count is below pairs decision threshold")
        if oos_windows < cls.MIN_OOS_WINDOWS:
            reasons.append("OOS window count is below pairs decision threshold")
        return {"allowed": not reasons, "reasons": reasons}


def _fingerprint_oos_windows(windows: list[dict[str, Any]]) -> str:
    ranges = [
        {
            "test_start": window["test_start"].isoformat(),
            "test_end": window["test_end"].isoformat(),
        }
        for window in windows
    ]
    raw = json.dumps(ranges, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_usage(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
