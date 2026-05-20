from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_learning.models import Candle


BINANCE_SPOT_API_BASE_URL = "https://data-api.binance.vision"


def fetch_klines(
    symbol: str,
    interval: str,
    limit: int = 500,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    base_url: str = BINANCE_SPOT_API_BASE_URL,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> list[Candle]:
    query: dict[str, str | int] = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit,
    }
    if start_time_ms is not None:
        query["startTime"] = start_time_ms
    if end_time_ms is not None:
        query["endTime"] = end_time_ms

    url = f"{base_url.rstrip('/')}/api/v3/klines?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url=url, method="GET")
    with urlopen(request, timeout=30) as response:
        rows = json.loads(response.read().decode("utf-8"))

    candles: list[Candle] = []
    for row in rows:
        opened_at = datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc)
        candles.append(
            Candle(
                symbol=symbol.upper(),
                opened_at=opened_at,
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
        )
    return candles


def save_klines_csv(candles: list[Candle], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["opened_at", "open", "high", "low", "close", "volume"])
        for candle in candles:
            writer.writerow(
                [
                    candle.opened_at.isoformat(),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                ]
            )
