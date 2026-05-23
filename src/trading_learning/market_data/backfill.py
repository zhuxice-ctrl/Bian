from __future__ import annotations

import math
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from trading_learning.market_data.binance_klines import fetch_klines, save_klines_csv
from trading_learning.market_data.catalog import DEFAULT_MARKET_DATA_ROOT, dataset_path
from trading_learning.models import Candle


def backfill_symbol(
    *,
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    fetcher: Callable[..., list[Candle]] = fetch_klines,
    sleep_fn: Callable[[float], None] = time.sleep,
    request_delay_seconds: float = 0.3,
    page_limit: int = 1000,
) -> list[Candle]:
    """Fetch all candles for a symbol and time range by paging Binance klines."""

    normalized_symbol = symbol.upper()
    normalized_start = _to_utc(start)
    normalized_end = _to_utc(end)
    _validate_request(normalized_start, normalized_end, page_limit)
    interval_delta = _interval_delta(interval)

    current_start = normalized_start
    candles_by_open: dict[datetime, Candle] = {}
    while current_start < normalized_end:
        page = fetcher(
            symbol=normalized_symbol,
            interval=interval,
            limit=page_limit,
            start_time_ms=_to_ms(current_start),
            end_time_ms=_to_ms(normalized_end),
        )
        filtered = [
            _normalize_candle(candle, normalized_symbol)
            for candle in page
            if normalized_start <= _to_utc(candle.opened_at) < normalized_end
        ]
        for candle in filtered:
            candles_by_open[candle.opened_at] = candle
        if len(page) < page_limit or not filtered:
            break
        next_start = max(candle.opened_at for candle in filtered) + interval_delta
        if next_start <= current_start:
            break
        current_start = next_start
        if current_start < normalized_end and request_delay_seconds > 0:
            sleep_fn(request_delay_seconds)
    return [candles_by_open[opened_at] for opened_at in sorted(candles_by_open)]


def backfill_symbols_to_csv(
    *,
    symbols: tuple[str, ...],
    interval: str,
    start: datetime,
    end: datetime,
    root: Path = DEFAULT_MARKET_DATA_ROOT,
    fetcher: Callable[..., list[Candle]] = fetch_klines,
    sleep_fn: Callable[[float], None] = time.sleep,
    request_delay_seconds: float = 0.3,
    page_limit: int = 1000,
) -> dict[str, Any]:
    datasets: list[dict[str, Any]] = []
    for symbol in symbols:
        candles = backfill_symbol(
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
            fetcher=fetcher,
            sleep_fn=sleep_fn,
            request_delay_seconds=request_delay_seconds,
            page_limit=page_limit,
        )
        path = dataset_path(symbol, interval, root=root)
        save_klines_csv(candles, path)
        datasets.append(
            {
                "symbol": symbol.upper(),
                "interval": interval,
                "path": str(path),
                "row_count": len(candles),
                "first_opened_at": candles[0].opened_at.isoformat() if candles else None,
                "last_opened_at": candles[-1].opened_at.isoformat() if candles else None,
            }
        )
    return {"status": "saved", "datasets": datasets}


def dry_run_plan(
    *,
    symbols: tuple[str, ...],
    interval: str,
    start: datetime,
    end: datetime,
    root: Path = DEFAULT_MARKET_DATA_ROOT,
    page_limit: int = 1000,
) -> dict[str, Any]:
    normalized_start = _to_utc(start)
    normalized_end = _to_utc(end)
    _validate_request(normalized_start, normalized_end, page_limit)
    interval_delta = _interval_delta(interval)
    expected_bars = max(0, math.ceil((normalized_end - normalized_start) / interval_delta))
    estimated_requests = math.ceil(expected_bars / page_limit) if expected_bars else 0
    return {
        "dry_run": True,
        "interval": interval,
        "start": normalized_start.isoformat(),
        "end": normalized_end.isoformat(),
        "expected_bars_per_symbol": expected_bars,
        "datasets": [
            {
                "symbol": symbol.upper(),
                "path": str(dataset_path(symbol, interval, root=root)),
                "estimated_request_count": estimated_requests,
            }
            for symbol in symbols
        ],
    }


def _validate_request(start: datetime, end: datetime, page_limit: int) -> None:
    if start >= end:
        raise ValueError("start must be before end")
    if page_limit < 1 or page_limit > 1000:
        raise ValueError("page_limit must be between 1 and 1000")


def _normalize_candle(candle: Candle, symbol: str) -> Candle:
    return Candle(
        symbol=symbol,
        opened_at=_to_utc(candle.opened_at),
        open=float(candle.open),
        high=float(candle.high),
        low=float(candle.low),
        close=float(candle.close),
        volume=float(candle.volume),
    )


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_ms(value: datetime) -> int:
    return int(_to_utc(value).timestamp() * 1000)


def _interval_delta(interval: str) -> timedelta:
    unit = interval[-1:]
    try:
        amount = int(interval[:-1])
    except ValueError as exc:
        raise ValueError(f"unsupported interval: {interval}") from exc
    if amount <= 0:
        raise ValueError(f"unsupported interval: {interval}")
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    raise ValueError(f"unsupported interval: {interval}")
