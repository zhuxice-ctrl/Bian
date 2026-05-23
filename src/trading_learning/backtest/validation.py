from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from trading_learning.models import Candle


def filter_candles_by_date(candles: list[Candle], *, start: str = "", end: str = "") -> list[Candle]:
    start_dt = _parse_optional_datetime(start)
    end_dt = _parse_optional_datetime(end)
    return [
        candle
        for candle in candles
        if (start_dt is None or candle.opened_at >= start_dt)
        and (end_dt is None or candle.opened_at <= end_dt)
    ]


def split_train_test(candles: list[Candle], *, train_ratio: float) -> tuple[list[Candle], list[Candle]]:
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1")
    if len(candles) < 2:
        return candles, []
    split_index = max(1, min(len(candles) - 1, int(len(candles) * train_ratio)))
    return candles[:split_index], candles[split_index:]


def stress_windows(candles: list[Candle], *, window_size: int = 24, top_n: int = 3) -> list[dict[str, Any]]:
    if window_size < 2 or top_n <= 0 or len(candles) < window_size:
        return []
    ranked: list[dict[str, Any]] = []
    for index in range(0, len(candles) - window_size + 1):
        window = candles[index : index + window_size]
        start_close = window[0].close
        end_close = window[-1].close
        move_pct = (end_close - start_close) / start_close if start_close else 0.0
        max_high = max(candle.high for candle in window)
        min_low = min(candle.low for candle in window)
        range_pct = (max_high - min_low) / start_close if start_close else 0.0
        ranked.append(
            {
                "start": window[0].opened_at.isoformat(),
                "end": window[-1].opened_at.isoformat(),
                "move_pct": move_pct,
                "range_pct": range_pct,
                "max_abs_move_pct": max(abs(move_pct), abs(range_pct)),
            }
        )
    ranked.sort(key=lambda item: item["max_abs_move_pct"], reverse=True)
    return ranked[:top_n]


def validation_warning(*, train_pnl: float, test_pnl: float, stress_window_count: int) -> str:
    if train_pnl > 0 and test_pnl <= 0:
        return "Positive in-sample result failed out-of-sample validation; treat as research-only."
    if stress_window_count == 0:
        return "No stress windows were available; collect more market history before promotion."
    return "Validation summary is research-only; require walk-forward and testnet evidence before promotion."


def _parse_optional_datetime(value: str) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
