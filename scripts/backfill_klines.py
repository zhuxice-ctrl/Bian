from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_learning.market_data.backfill import backfill_symbol, dry_run_plan, write_backfilled_dataset  # noqa: E402
from trading_learning.market_data.catalog import DEFAULT_MARKET_DATA_ROOT, dataset_path  # noqa: E402

DEFAULT_BACKFILL_SYMBOLS = "BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Binance klines into the local market-data catalog.")
    parser.add_argument("--symbols", default=DEFAULT_BACKFILL_SYMBOLS, help="Comma-separated symbols.")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true", help="Print the download plan without sending requests.")
    parser.add_argument("--no-backup", action="store_true", help="Overwrite existing CSV files without creating .bak files.")
    args = parser.parse_args()

    symbols = _parse_symbols(args.symbols)
    end = _floor_to_hour(datetime.now(timezone.utc))
    start = _subtract_years(end, args.years)
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


def _floor_to_hour(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


if __name__ == "__main__":
    raise SystemExit(main())
