from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_learning.market_data.backfill import backfill_symbols_to_csv, dry_run_plan  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Binance kline CSV files into data/local/market_data.")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols, e.g. BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--start", required=True, help="Inclusive ISO datetime, UTC if timezone is omitted")
    parser.add_argument("--end", required=True, help="Exclusive ISO datetime, UTC if timezone is omitted")
    parser.add_argument("--root", default="data/local")
    parser.add_argument("--page-limit", type=int, default=1000)
    parser.add_argument("--request-delay-seconds", type=float, default=0.3)
    parser.add_argument("--execute", action="store_true", help="Actually fetch and write CSV files. Omit for dry-run.")
    args = parser.parse_args()

    symbols = tuple(symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip())
    start = _parse_datetime(args.start)
    end = _parse_datetime(args.end)
    root = Path(args.root)
    if not args.execute:
        result = dry_run_plan(symbols=symbols, interval=args.interval, start=start, end=end, root=root, page_limit=args.page_limit)
    else:
        result = backfill_symbols_to_csv(
            symbols=symbols,
            interval=args.interval,
            start=start,
            end=end,
            root=root,
            page_limit=args.page_limit,
            request_delay_seconds=args.request_delay_seconds,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


if __name__ == "__main__":
    raise SystemExit(main())
