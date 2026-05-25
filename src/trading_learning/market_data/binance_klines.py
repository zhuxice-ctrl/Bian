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
BINANCE_USDM_API_BASE_URL = "https://fapi.binance.com"


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


def fetch_funding_rate_history(
    symbol: str,
    start_ms: int,
    end_ms: int,
    limit: int = 1000,
    base_url: str = BINANCE_USDM_API_BASE_URL,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> list[dict[str, Any]]:
    if start_ms >= end_ms:
        raise ValueError("start_ms must be before end_ms")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")

    current_start_ms = start_ms
    rows_by_time: dict[int, dict[str, Any]] = {}
    while current_start_ms < end_ms:
        query: dict[str, str | int] = {
            "symbol": symbol.upper(),
            "startTime": current_start_ms,
            "endTime": end_ms,
            "limit": limit,
        }
        url = f"{base_url.rstrip('/')}/fapi/v1/fundingRate?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(url=url, method="GET")
        with urlopen(request, timeout=30) as response:
            page = json.loads(response.read().decode("utf-8"))
        if not page:
            break

        normalized_page = [_normalize_funding_rate_row(row) for row in page]
        for row in normalized_page:
            rows_by_time[int(row["fundingTime"])] = row
        last_funding_time = max(int(row["fundingTime"]) for row in normalized_page)
        if len(page) < limit or last_funding_time >= end_ms:
            break
        next_start_ms = last_funding_time + 1
        if next_start_ms <= current_start_ms:
            break
        current_start_ms = next_start_ms

    return [rows_by_time[funding_time] for funding_time in sorted(rows_by_time)]


def _normalize_funding_rate_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "fundingTime": int(row["fundingTime"]),
        "fundingRate": str(row["fundingRate"]),
        "markPrice": str(row["markPrice"]),
    }


def save_funding_rate_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fundingTime", "fundingRate", "markPrice"])
        for row in rows:
            writer.writerow([row["fundingTime"], row["fundingRate"], row["markPrice"]])


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
