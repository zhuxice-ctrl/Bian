from __future__ import annotations

import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


OKX_API_BASE_URL = "https://www.okx.com"
OKX_FUNDING_RATE_HISTORY_LIMIT = 400
OKX_FUNDING_CSV_COLUMNS = ("exchange", "fundingTime", "fundingRate", "markPrice", "instId", "realizedRate")


class OkxAPIError(RuntimeError):
    pass


def fetch_funding_rate_history(
    symbol: str,
    start_ms: int,
    end_ms: int,
    limit: int = OKX_FUNDING_RATE_HISTORY_LIMIT,
    max_pages: int | None = None,
    base_url: str = OKX_API_BASE_URL,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> list[dict[str, Any]]:
    if start_ms >= end_ms:
        raise ValueError("start_ms must be before end_ms")
    if limit < 1 or limit > OKX_FUNDING_RATE_HISTORY_LIMIT:
        raise ValueError(f"limit must be between 1 and {OKX_FUNDING_RATE_HISTORY_LIMIT}")
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be >= 1")

    inst_id = okx_inst_id_from_symbol(symbol)
    after: int | None = None
    pages_fetched = 0
    rows_by_time: dict[int, dict[str, Any]] = {}

    while True:
        query: dict[str, str | int] = {"instId": inst_id, "limit": limit}
        if after is not None:
            query["after"] = after
        url = f"{base_url.rstrip('/')}/api/v5/public/funding-rate-history?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(url=url, method="GET")
        payload = _read_okx_json(request, urlopen=urlopen)
        page = payload.get("data", [])
        if not isinstance(page, list):
            raise OkxAPIError(f"OKX API returned non-list data: {page!r}")
        if not page:
            break

        normalized_page = [_normalize_funding_rate_row(row, fallback_inst_id=inst_id) for row in page]
        for row in normalized_page:
            funding_time = int(row["fundingTime"])
            if start_ms <= funding_time <= end_ms:
                rows_by_time[funding_time] = row

        pages_fetched += 1
        oldest_funding_time = min(int(row["fundingTime"]) for row in normalized_page)
        if oldest_funding_time <= start_ms or len(page) < limit:
            break
        if max_pages is not None and pages_fetched >= max_pages:
            break
        if after == oldest_funding_time:
            break
        after = oldest_funding_time

    return [rows_by_time[funding_time] for funding_time in sorted(rows_by_time)]


fetch_okx_funding_rate_history = fetch_funding_rate_history


def okx_inst_id_from_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if "-" in normalized:
        return normalized
    for quote in ("USDT", "USDC", "USD"):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return f"{normalized[: -len(quote)]}-{quote}-SWAP"
    raise ValueError(f"cannot derive OKX swap instId from symbol: {symbol}")


def save_funding_rate_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(OKX_FUNDING_CSV_COLUMNS)
        for row in rows:
            writer.writerow([row.get(column, "") for column in OKX_FUNDING_CSV_COLUMNS])


def _read_okx_json(request: urllib.request.Request, *, urlopen: Callable[..., Any]) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise OkxAPIError(f"OKX HTTP error status={exc.code} reason={exc.reason} body={body}") from exc

    if not isinstance(payload, dict):
        raise OkxAPIError(f"OKX API returned non-object payload: {payload!r}")
    code = str(payload.get("code", ""))
    if code != "0":
        msg = str(payload.get("msg", ""))
        raise OkxAPIError(f"OKX API error code={code} msg={msg}")
    return payload


def _normalize_funding_rate_row(row: dict[str, Any], *, fallback_inst_id: str) -> dict[str, Any]:
    return {
        "exchange": "okx",
        "fundingTime": int(row["fundingTime"]),
        "fundingRate": str(row.get("fundingRate", "")),
        "markPrice": str(row.get("markPrice", "")),
        "instId": str(row.get("instId", fallback_inst_id)),
        "realizedRate": str(row.get("realizedRate", "")),
    }
