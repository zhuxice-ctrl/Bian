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
