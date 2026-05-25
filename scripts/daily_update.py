from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from trading_learning.market_data.binance_klines import update_csv  # noqa: E402
from trading_learning.paper_trading import daily_runner  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update BTCUSDT 1d data and optionally run paper trading.")
    parser.add_argument("--price-csv", type=Path, default=daily_runner.DEFAULT_PRICE_CSV)
    parser.add_argument("--trade", action="store_true", help="Run the daily paper-trading cycle after data update.")
    parser.add_argument("--status", action="store_true", help="Print the latest paper-trading status after update.")
    args = parser.parse_args(argv)

    try:
        added_rows = update_csv(args.price_csv)
    except (requests.ConnectionError, requests.HTTPError) as exc:
        if _is_blocked_binance_error(exc):
            print("Binance API blocked, try VPN")
            return 1
        raise

    print(f"added_rows={added_rows} latest_date={_latest_date(args.price_csv)}")

    if args.trade:
        daily_runner.run_daily(price_csv=args.price_csv, verbose=True)
    if args.status:
        print(daily_runner.load_status())
    return 0


def _is_blocked_binance_error(exc: BaseException) -> bool:
    if isinstance(exc, requests.ConnectionError):
        return True
    if isinstance(exc, requests.HTTPError):
        response = getattr(exc, "response", None)
        return getattr(response, "status_code", None) in {403, 451}
    return False


def _latest_date(csv_path: Path) -> str:
    path = Path(csv_path)
    if not path.exists():
        return "missing"
    frame = pd.read_csv(path)
    if frame.empty:
        return "empty"
    timestamp_column = _timestamp_column(frame.columns)
    latest = pd.to_datetime(frame[timestamp_column], utc=True).max()
    return latest.date().isoformat()


def _timestamp_column(columns: pd.Index) -> str:
    if "opened_at" in columns:
        return "opened_at"
    if "timestamp" in columns:
        return "timestamp"
    raise ValueError("CSV must include opened_at or timestamp")


if __name__ == "__main__":
    sys.exit(main())
