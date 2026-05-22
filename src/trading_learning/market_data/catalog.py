from __future__ import annotations

import csv
from collections.abc import Callable
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
            candles = fetcher(symbol=symbol, interval=interval, limit=limit)
            save_klines_csv(candles, path)
            datasets.append(_dataset_info(symbol=symbol, interval=interval, path=path))
    return {"status": "saved", "datasets": datasets}


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
        }
    rows = _read_candle_rows(path)
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
    }


def _mtime_iso(path: Path) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _read_candle_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({key.strip().removeprefix("\ufeff"): value for key, value in row.items()})
        return rows
