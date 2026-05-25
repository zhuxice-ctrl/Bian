from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from trading_learning.models import Candle


BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_SPOT_API_BASE_URL = "https://data-api.binance.vision"
BINANCE_USDM_API_BASE_URL = "https://fapi.binance.com"
PROJECT_KLINE_COLUMNS = ["opened_at", "open", "high", "low", "close", "volume"]
KLINE_VALUE_COLUMNS = ["open", "high", "low", "close", "volume"]
TIMESTAMP_COLUMNS = ("timestamp", "opened_at")
_UNSET = object()


def fetch_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    start_ms: int | None = None,
    limit: int = 1000,
    *,
    start_time_ms: int | None | object = _UNSET,
    end_time_ms: int | None | object = _UNSET,
    base_url: str | object = _UNSET,
    urlopen: Callable[..., Any] | object = _UNSET,
) -> pd.DataFrame | list[Candle]:
    """
    Fetch Binance klines.

    The default path returns a DataFrame with columns:
    timestamp, open, high, low, close, volume.

    Existing project callers pass legacy-only kwargs such as start_time_ms or
    urlopen; those calls keep receiving list[Candle] for backward compatibility.
    """
    if (
        start_time_ms is not _UNSET
        or end_time_ms is not _UNSET
        or base_url is not _UNSET
        or urlopen is not _UNSET
    ):
        return _fetch_klines_as_candles(
            symbol=symbol,
            interval=interval,
            limit=limit,
            start_time_ms=None if start_time_ms is _UNSET else start_time_ms,
            end_time_ms=None if end_time_ms is _UNSET else end_time_ms,
            base_url=BINANCE_SPOT_API_BASE_URL if base_url is _UNSET else base_url,
            urlopen=urllib.request.urlopen if urlopen is _UNSET else urlopen,
        )
    return _fetch_klines_as_frame(symbol=symbol, interval=interval, start_ms=start_ms, limit=limit)


def _fetch_klines_as_frame(
    *,
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    start_ms: int | None = None,
    limit: int = 1000,
) -> pd.DataFrame:
    params: dict[str, str | int] = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    if start_ms is not None:
        params["startTime"] = start_ms
    resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=30)
    resp.raise_for_status()
    raw = resp.json()
    df = pd.DataFrame(
        raw,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )
    if df.empty:
        return pd.DataFrame(columns=["timestamp", *KLINE_VALUE_COLUMNS])
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for col in KLINE_VALUE_COLUMNS:
        df[col] = df[col].astype(float)
    return df[["timestamp", *KLINE_VALUE_COLUMNS]]


def _fetch_klines_as_candles(
    *,
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


def update_csv(
    csv_path: str | Path,
    symbol: str = "BTCUSDT",
    interval: str = "1d",
) -> int:
    """
    Incrementally update a local kline CSV from Binance.

    Existing CSV column names are preserved. The project BTCUSDT 1d file uses
    opened_at, so new files are created with that loader-compatible schema.
    """
    csv_path = Path(csv_path)
    if csv_path.exists():
        existing = pd.read_csv(csv_path)
        timestamp_column = _detect_timestamp_column(existing.columns)
        existing_timestamps = pd.to_datetime(existing[timestamp_column], utc=True)
        start_ms = None
        if not existing_timestamps.dropna().empty:
            last_ts = existing_timestamps.max()
            start_ms = int(last_ts.timestamp() * 1000) + 1
        new_data = fetch_klines(symbol=symbol, interval=interval, start_ms=start_ms)
        if new_data.empty:
            return 0
        new_data = _dedupe_new_klines(new_data, existing_timestamps)
        if new_data.empty:
            return 0
        append_rows = _map_klines_to_csv_columns(new_data, existing.columns, timestamp_column)
        _append_rows(csv_path, append_rows)
        return len(append_rows)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    data = fetch_klines(symbol=symbol, interval=interval, limit=1000)
    rows = _map_klines_to_csv_columns(data, PROJECT_KLINE_COLUMNS, "opened_at")
    rows.to_csv(csv_path, index=False, lineterminator="\n")
    return len(rows)


def _detect_timestamp_column(columns: pd.Index) -> str:
    for column in TIMESTAMP_COLUMNS:
        if column in columns:
            return column
    raise ValueError(f"CSV must include one of: {', '.join(TIMESTAMP_COLUMNS)}")


def _dedupe_new_klines(new_data: pd.DataFrame, existing_timestamps: pd.Series) -> pd.DataFrame:
    if existing_timestamps.dropna().empty:
        return new_data
    existing_ns = set(existing_timestamps.dropna().astype("int64"))
    new_timestamps = pd.to_datetime(new_data["timestamp"], utc=True)
    keep = ~new_timestamps.astype("int64").isin(existing_ns)
    return new_data.loc[keep].copy()


def _map_klines_to_csv_columns(
    klines: pd.DataFrame,
    columns: pd.Index | list[str],
    timestamp_column: str,
) -> pd.DataFrame:
    rows = pd.DataFrame(index=klines.index, columns=list(columns))
    for column in rows.columns:
        if column == timestamp_column:
            rows[column] = pd.to_datetime(klines["timestamp"], utc=True).map(_format_timestamp)
        elif column in KLINE_VALUE_COLUMNS:
            rows[column] = klines[column].astype(float)
        else:
            rows[column] = ""
    return rows.reset_index(drop=True)


def _append_rows(csv_path: Path, rows: pd.DataFrame) -> None:
    if _needs_leading_newline(csv_path):
        with csv_path.open("a", encoding="utf-8", newline="") as handle:
            handle.write("\n")
    rows.to_csv(csv_path, mode="a", header=False, index=False, lineterminator="\n")


def _needs_leading_newline(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("rb") as handle:
        handle.seek(-1, 2)
        return handle.read(1) not in {b"\n", b"\r"}


def _format_timestamp(value: pd.Timestamp) -> str:
    return value.to_pydatetime().isoformat()


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
