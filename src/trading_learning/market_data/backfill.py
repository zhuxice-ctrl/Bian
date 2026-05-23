from __future__ import annotations

import math
import shutil
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from trading_learning.market_data.binance_klines import fetch_klines, save_klines_csv
from trading_learning.market_data.catalog import DEFAULT_MARKET_DATA_ROOT, dataset_path
from trading_learning.models import Candle

SUPPORTED_BACKFILL_INTERVALS = ("1m", "5m", "15m", "1h", "4h", "1d")


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
    max_pages: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[Candle]:
    """Fetch all candles for a symbol and time range by paging Binance klines."""

    normalized_symbol = symbol.upper()
    normalized_start = _to_utc(start)
    normalized_end = _to_utc(end)
    _validate_request(normalized_start, normalized_end, page_limit, max_pages=max_pages)
    interval_delta = _interval_delta(interval)

    current_start = normalized_start
    candles_by_open: dict[datetime, Candle] = {}
    pages_fetched = 0
    while current_start < normalized_end:
        page = fetcher(
            symbol=normalized_symbol,
            interval=interval,
            limit=page_limit,
            start_time_ms=_to_ms(current_start),
            end_time_ms=_to_ms(normalized_end),
        )
        pages_fetched += 1
        if not page:
            break
        filtered = [
            _normalize_candle(candle, normalized_symbol)
            for candle in page
            if normalized_start <= _to_utc(candle.opened_at) < normalized_end
        ]
        for candle in filtered:
            candles_by_open[candle.opened_at] = candle
        page_last_opened_at = max(_to_utc(candle.opened_at) for candle in page)
        next_start = max(candle.opened_at for candle in filtered) + interval_delta if filtered else current_start
        if progress_callback is not None:
            progress_callback(
                {
                    "symbol": normalized_symbol,
                    "interval": interval,
                    "page": pages_fetched,
                    "rows_collected": len(candles_by_open),
                    "next_start": next_start.isoformat(),
                    "last_opened_at": page_last_opened_at.isoformat(),
                }
            )
        if max_pages is not None and pages_fetched >= max_pages:
            break
        if page_last_opened_at >= normalized_end:
            break
        if not filtered:
            break
        if next_start <= current_start:
            break
        current_start = next_start
        if request_delay_seconds > 0:
            sleep_fn(request_delay_seconds)
    return [candles_by_open[opened_at] for opened_at in sorted(candles_by_open)]


def write_backfilled_dataset(
    *,
    candles: list[Candle],
    symbol: str,
    interval: str,
    root: Path = DEFAULT_MARKET_DATA_ROOT,
    backup_existing: bool = True,
    now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    normalized_symbol = symbol.upper()
    ordered = _dedupe_ordered([_normalize_candle(candle, normalized_symbol) for candle in candles])
    path = dataset_path(normalized_symbol, interval, root=root)
    backup_path = None
    if path.exists() and backup_existing:
        timestamp = _to_utc(now_fn()).strftime("%Y%m%d-%H%M%S")
        backup_path = path.with_name(f"{normalized_symbol}-{interval}.bak-{timestamp}.csv")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
    save_klines_csv(ordered, path)
    return {
        "status": "saved",
        "path": str(path),
        "backup_path": str(backup_path) if backup_path is not None else None,
        "row_count": len(ordered),
        "first_opened_at": ordered[0].opened_at.isoformat() if ordered else None,
        "last_opened_at": ordered[-1].opened_at.isoformat() if ordered else None,
    }


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
    max_pages: int | None = None,
    backup_existing: bool = True,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
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
            max_pages=max_pages,
            progress_callback=progress_callback,
        )
        dataset = write_backfilled_dataset(
            candles=candles,
            symbol=symbol,
            interval=interval,
            root=root,
            backup_existing=backup_existing,
        )
        dataset["symbol"] = symbol.upper()
        dataset["interval"] = interval
        datasets.append(dataset)
    return {"status": "saved", "datasets": datasets}


def dry_run_plan(
    *,
    symbols: tuple[str, ...],
    interval: str,
    start: datetime,
    end: datetime,
    root: Path = DEFAULT_MARKET_DATA_ROOT,
    page_limit: int = 1000,
    max_pages: int | None = None,
) -> dict[str, Any]:
    normalized_start = _to_utc(start)
    normalized_end = _to_utc(end)
    _validate_request(normalized_start, normalized_end, page_limit, max_pages=max_pages)
    interval_delta = _interval_delta(interval)
    expected_bars = max(0, math.ceil((normalized_end - normalized_start) / interval_delta))
    estimated_requests = math.ceil(expected_bars / page_limit) if expected_bars else 0
    planned_requests = min(estimated_requests, max_pages) if max_pages is not None else estimated_requests
    pages = _page_plan(
        start=normalized_start,
        end=normalized_end,
        interval_delta=interval_delta,
        page_limit=page_limit,
        max_pages=max_pages,
    )
    return {
        "dry_run": True,
        "interval": interval,
        "start": normalized_start.isoformat(),
        "end": normalized_end.isoformat(),
        "expected_bars_per_symbol": expected_bars,
        "max_pages": max_pages,
        "datasets": [
            {
                "symbol": symbol.upper(),
                "path": str(dataset_path(symbol, interval, root=root)),
                "estimated_request_count": planned_requests,
                "estimated_request_count_without_max_pages": estimated_requests,
                "truncated_by_max_pages": planned_requests < estimated_requests,
                "pages": pages,
            }
            for symbol in symbols
        ],
    }


def _validate_request(start: datetime, end: datetime, page_limit: int, *, max_pages: int | None = None) -> None:
    if start >= end:
        raise ValueError("start must be before end")
    if page_limit < 1 or page_limit > 1000:
        raise ValueError("page_limit must be between 1 and 1000")
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be >= 1")


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


def _dedupe_ordered(candles: list[Candle]) -> list[Candle]:
    by_opened_at = {candle.opened_at: candle for candle in candles}
    return [by_opened_at[opened_at] for opened_at in sorted(by_opened_at)]


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_ms(value: datetime) -> int:
    return int(_to_utc(value).timestamp() * 1000)


def _interval_delta(interval: str) -> timedelta:
    if interval not in SUPPORTED_BACKFILL_INTERVALS:
        raise ValueError(f"unsupported interval: {interval}")
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


def _page_plan(
    *,
    start: datetime,
    end: datetime,
    interval_delta: timedelta,
    page_limit: int,
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    current_start = start
    page_number = 1
    while current_start < end:
        if max_pages is not None and page_number > max_pages:
            break
        page_end = min(end, current_start + interval_delta * page_limit)
        expected_bars = max(0, math.ceil((page_end - current_start) / interval_delta))
        pages.append(
            {
                "page": page_number,
                "start": current_start.isoformat(),
                "end": page_end.isoformat(),
                "expected_bars": expected_bars,
            }
        )
        current_start = page_end
        page_number += 1
    return pages
