from __future__ import annotations

import argparse
import calendar
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_learning.market_data.backfill import (  # noqa: E402
    SUPPORTED_BACKFILL_INTERVALS,
    backfill_symbol,
    dry_run_plan,
    write_backfilled_dataset,
)
from trading_learning.market_data.catalog import DEFAULT_MARKET_DATA_ROOT, dataset_path  # noqa: E402

DEFAULT_BACKFILL_SYMBOLS = "BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Binance klines into the local market-data catalog.")
    parser.add_argument("--symbols", default=DEFAULT_BACKFILL_SYMBOLS, help="Comma-separated symbols.")
    parser.add_argument("--interval", default="1h", choices=SUPPORTED_BACKFILL_INTERVALS)
    parser.add_argument("--years", type=int, default=None)
    parser.add_argument("--months", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print the download plan without sending requests.")
    parser.add_argument("--no-backup", action="store_true", help="Overwrite existing CSV files without creating .bak files.")
    args = parser.parse_args()

    symbols = _parse_symbols(args.symbols)
    end = _floor_to_interval(datetime.now(timezone.utc), args.interval)
    start = _default_start(end, args.interval, years=args.years, months=args.months)
    backup_existing = not args.no_backup

    if args.dry_run:
        result = dry_run_plan(
            symbols=symbols,
            interval=args.interval,
            start=start,
            end=end,
            root=DEFAULT_MARKET_DATA_ROOT,
        )
        result["total_estimated_request_count"] = sum(item["estimated_request_count"] for item in result["datasets"])
        for dataset in result["datasets"]:
            target = Path(dataset["path"])
            dataset["start"] = result["start"]
            dataset["end"] = result["end"]
            dataset["will_backup_existing"] = bool(target.exists() and backup_existing)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    failures = 0
    for symbol in symbols:
        path = dataset_path(symbol, args.interval, root=DEFAULT_MARKET_DATA_ROOT)
        print(f"[{symbol}] backfill {args.interval} {start.isoformat()} -> {end.isoformat()} into {path}", flush=True)
        try:
            candles = backfill_symbol(symbol=symbol, interval=args.interval, start=start, end=end)
            result = write_backfilled_dataset(
                candles=candles,
                symbol=symbol,
                interval=args.interval,
                root=DEFAULT_MARKET_DATA_ROOT,
                backup_existing=backup_existing,
            )
        except Exception as exc:
            failures += 1
            print(f"[{symbol}] ERROR: {exc}", file=sys.stderr, flush=True)
            continue
        print(
            f"[{symbol}] saved rows={result['row_count']} first={result['first_opened_at']} "
            f"last={result['last_opened_at']} backup={result['backup_path']}",
            flush=True,
        )
    return failures


def _parse_symbols(value: str) -> tuple[str, ...]:
    symbols = tuple(symbol.strip().upper() for symbol in value.split(",") if symbol.strip())
    if not symbols:
        raise ValueError("at least one symbol is required")
    return symbols


def _subtract_years(value: datetime, years: int) -> datetime:
    if years < 1:
        raise ValueError("years must be >= 1")
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, day=28)


def _subtract_months(value: datetime, months: int) -> datetime:
    if months < 1:
        raise ValueError("months must be >= 1")
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _default_start(value: datetime, interval: str, *, years: int | None, months: int | None) -> datetime:
    if years is not None and months is not None:
        raise ValueError("use either years or months, not both")
    if months is not None:
        return _subtract_months(value, months)
    if years is not None:
        return _subtract_years(value, years)
    if interval == "1m":
        return _subtract_months(value, 6)
    return _subtract_years(value, 2)


def _floor_to_interval(value: datetime, interval: str) -> datetime:
    utc_value = value.astimezone(timezone.utc).replace(second=0, microsecond=0)
    if interval == "1d":
        return utc_value.replace(hour=0, minute=0)
    if interval == "4h":
        return utc_value.replace(hour=utc_value.hour - (utc_value.hour % 4), minute=0)
    if interval.endswith("h"):
        return utc_value.replace(minute=0)
    if interval.endswith("m"):
        amount = int(interval[:-1])
        return utc_value.replace(minute=utc_value.minute - (utc_value.minute % amount))
    return utc_value


if __name__ == "__main__":
    raise SystemExit(main())
