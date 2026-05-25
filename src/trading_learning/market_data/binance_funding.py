from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests


BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"


def fetch_funding_rate(
    symbol: str = "BTCUSDT",
    start_ms: int | None = None,
    end_ms: int | None = None,
    limit: int = 1000,
) -> pd.DataFrame:
    """
    Fetch Binance USD-M perpetual funding-rate history.

    Returns columns: timestamp, funding_rate.
    """
    params: dict[str, str | int] = {"symbol": symbol.upper(), "limit": limit}
    if start_ms is not None:
        params["startTime"] = start_ms
    if end_ms is not None:
        params["endTime"] = end_ms
    resp = requests.get(BINANCE_FUNDING_URL, params=params, timeout=30)
    resp.raise_for_status()
    raw = resp.json()
    if not raw:
        return pd.DataFrame(columns=["timestamp", "funding_rate"])
    df = pd.DataFrame(raw)
    df["timestamp"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["funding_rate"] = df["fundingRate"].astype(float)
    return df[["timestamp", "funding_rate"]]


def backfill_funding_rate(
    symbol: str = "BTCUSDT",
    start_date: str = "2024-09-01",
    end_date: str | None = None,
    save_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Page through Binance funding-rate history and optionally write a CSV.

    Each page is requested with the previous page's final timestamp + 1ms.
    Date-only end_date values are treated as inclusive UTC days.
    """
    start_ms = _start_ms(start_date)
    end_ms = _end_ms(end_date)
    rows: list[pd.DataFrame] = []
    current_start = start_ms
    while True:
        page = fetch_funding_rate(symbol=symbol, start_ms=current_start, end_ms=end_ms, limit=1000)
        if page.empty:
            break
        rows.append(page)
        last_ms = int(page["timestamp"].max().timestamp() * 1000)
        next_start = last_ms + 1
        if end_ms is not None and next_start > end_ms:
            break
        if next_start <= current_start:
            break
        current_start = next_start
        if len(page) < 1000:
            break

    if rows:
        data = pd.concat(rows, ignore_index=True)
        data = data.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        if end_ms is not None:
            end_ts = pd.to_datetime(end_ms, unit="ms", utc=True)
            data = data.loc[data["timestamp"] <= end_ts].reset_index(drop=True)
    else:
        data = pd.DataFrame(columns=["timestamp", "funding_rate"])

    if save_path is not None:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(path, index=False, lineterminator="\n")
    return data


def aggregate_daily_funding(funding: pd.DataFrame) -> pd.Series:
    """Aggregate 8h funding rows to UTC daily funding by summing the day."""
    if funding.empty:
        return pd.Series(dtype=float, name="daily_funding_rate")
    frame = funding.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["funding_rate"] = frame["funding_rate"].astype(float)
    daily = frame.groupby(frame["timestamp"].dt.floor("D"))["funding_rate"].sum()
    daily.index.name = "timestamp"
    return daily.rename("daily_funding_rate")


def calculate_funding_pnl(positions: pd.Series, daily_funding_rate: pd.Series) -> pd.Series:
    """
    Return daily funding PnL as a fraction of capital.

    Positive value helps returns. Negative value hurts returns.
    """
    aligned = pd.concat(
        [
            positions.astype(float).rename("position"),
            daily_funding_rate.astype(float).rename("daily_funding_rate"),
        ],
        axis=1,
        join="inner",
    ).fillna(0.0)
    return (-aligned["position"] * aligned["daily_funding_rate"]).rename("funding_pnl")


def _start_ms(value: str) -> int:
    timestamp = pd.to_datetime(value, utc=True)
    return int(timestamp.timestamp() * 1000)


def _end_ms(value: str | None) -> int | None:
    if value is None:
        return None
    timestamp = pd.to_datetime(value, utc=True)
    if len(value) == 10:
        timestamp = timestamp + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    return int(timestamp.timestamp() * 1000)
