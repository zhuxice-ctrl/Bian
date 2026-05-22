from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from trading_learning.config import DEFAULT_ALLOWED_SYMBOLS
from trading_learning.market_data.binance_klines import fetch_klines, save_klines_csv
from trading_learning.models import Candle

DEFAULT_MARKET_INTERVALS = ("1m", "5m", "15m", "1h", "4h", "1d")
DEFAULT_MARKET_DATA_ROOT = Path("data/local")


def dataset_path(symbol: str, interval: str, *, root: Path = DEFAULT_MARKET_DATA_ROOT) -> Path:
    normalized_symbol = symbol.upper()
    normalized_interval = interval.strip()
    return root / "market_data" / normalized_symbol / f"{normalized_symbol}-{normalized_interval}.csv"


def inventory_datasets(
    *,
    root: Path = DEFAULT_MARKET_DATA_ROOT,
    allowed_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
    intervals: tuple[str, ...] = DEFAULT_MARKET_INTERVALS,
) -> list[dict[str, Any]]:
    datasets: list[dict[str, Any]] = []
    for symbol in allowed_symbols:
        for interval in intervals:
            path = dataset_path(symbol, interval, root=root)
            datasets.append(_dataset_info(symbol=symbol, interval=interval, path=path))
    return datasets


def refresh_market_data(
    *,
    symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
    intervals: tuple[str, ...] = DEFAULT_MARKET_INTERVALS,
    allowed_symbols: tuple[str, ...] = DEFAULT_ALLOWED_SYMBOLS,
    root: Path = DEFAULT_MARKET_DATA_ROOT,
    limit: int = 500,
    fetcher: Callable[..., list[Candle]] = fetch_klines,
) -> dict[str, Any]:
    normalized_symbols = tuple(symbol.upper() for symbol in symbols)
    normalized_allowed = tuple(symbol.upper() for symbol in allowed_symbols)
    for symbol in normalized_symbols:
        if symbol not in normalized_allowed:
            raise ValueError(f"symbol not allowed: {symbol}. allowed: {', '.join(normalized_allowed)}")

    datasets: list[dict[str, Any]] = []
    for symbol in normalized_symbols:
        for interval in intervals:
            path = dataset_path(symbol, interval, root=root)
            existing = _read_candles(path, symbol=symbol) if path.exists() else []
            start_time_ms = _next_start_time_ms(existing, interval)
            candles = fetcher(symbol=symbol, interval=interval, limit=limit, start_time_ms=start_time_ms)
            save_klines_csv(_merge_candles(existing, candles), path)
            datasets.append(_dataset_info(symbol=symbol, interval=interval, path=path))
    return {"status": "saved", "datasets": datasets}


def import_market_csv(
    *,
    source_csv: Path,
    symbol: str,
    interval: str,
    root: Path = DEFAULT_MARKET_DATA_ROOT,
) -> dict[str, Any]:
    normalized_symbol = symbol.upper()
    source_path = Path(source_csv)
    if not source_path.exists():
        raise FileNotFoundError(str(source_path))
    candles = _read_candles(source_path, symbol=normalized_symbol)
    path = dataset_path(normalized_symbol, interval, root=root)
    save_klines_csv(candles, path)
    dataset = _dataset_info(symbol=normalized_symbol, interval=interval, path=path)
    dataset["source"] = "manual_csv"
    return {"status": "saved", "dataset": dataset}


def _dataset_info(*, symbol: str, interval: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "path": str(path),
            "exists": False,
            "source": "missing_local_cache",
            "row_count": 0,
            "first_opened_at": None,
            "last_opened_at": None,
            "updated_at": None,
            "gap_count": 0,
            "has_gaps": False,
            "next_expected_opened_at": None,
        }
    rows = _read_candle_rows(path)
    gap_count = _gap_count(rows, interval)
    next_expected = _next_expected_opened_at(rows, interval)
    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "path": str(path),
        "exists": True,
        "source": "binance_public_cache",
        "row_count": len(rows),
        "first_opened_at": rows[0]["opened_at"] if rows else None,
        "last_opened_at": rows[-1]["opened_at"] if rows else None,
        "updated_at": _mtime_iso(path),
        "gap_count": gap_count,
        "has_gaps": gap_count > 0,
        "next_expected_opened_at": next_expected,
    }


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _read_candle_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({key.strip().removeprefix("\ufeff"): value for key, value in row.items()})
        return rows


def _read_candles(path: Path, *, symbol: str) -> list[Candle]:
    candles: list[Candle] = []
    for row in _read_candle_rows(path):
        candles.append(
            Candle(
                symbol=symbol.upper(),
                opened_at=_parse_datetime(row["opened_at"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    return candles


def _merge_candles(existing: list[Candle], incoming: list[Candle]) -> list[Candle]:
    by_opened_at = {candle.opened_at: candle for candle in existing}
    for candle in incoming:
        by_opened_at[candle.opened_at] = candle
    return [by_opened_at[opened_at] for opened_at in sorted(by_opened_at)]


def _next_start_time_ms(existing: list[Candle], interval: str) -> int | None:
    if not existing:
        return None
    interval_delta = _interval_delta(interval)
    if interval_delta is None:
        return None
    last_opened_at = max(candle.opened_at for candle in existing)
    next_opened_at = last_opened_at + interval_delta
    return int(next_opened_at.timestamp() * 1000)


def _gap_count(rows: list[dict[str, str]], interval: str) -> int:
    interval_delta = _interval_delta(interval)
    if interval_delta is None or len(rows) < 2:
        return 0
    opened_at_values = [_parse_datetime(row["opened_at"]) for row in rows]
    opened_at_values.sort()
    gaps = 0
    for previous, current in zip(opened_at_values, opened_at_values[1:]):
        expected_steps = int((current - previous) / interval_delta)
        if expected_steps > 1:
            gaps += expected_steps - 1
    return gaps


def _next_expected_opened_at(rows: list[dict[str, str]], interval: str) -> str | None:
    interval_delta = _interval_delta(interval)
    if interval_delta is None or not rows:
        return None
    last_opened_at = max(_parse_datetime(row["opened_at"]) for row in rows)
    return (last_opened_at + interval_delta).isoformat()


def _interval_delta(interval: str) -> timedelta | None:
    unit = interval[-1:]
    try:
        amount = int(interval[:-1])
    except ValueError:
        return None
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    return None


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
