from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from trading_learning.paper_trading.daily_runner import (  # noqa: E402
    DEFAULT_CAPITAL,
    DEFAULT_FDM,
    DEFAULT_PRICE_CSV,
    DEFAULT_STATE_DIR,
    STATE_FILE,
    load_status,
    run_backfill,
    run_daily,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or inspect Bian v1 paper trading.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--fdm", type=float, default=None)
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL)
    parser.add_argument("--backfill", action="store_true", help="Backfill paper state from the aligned history window.")
    parser.add_argument("--status", action="store_true", help="Print latest paper-trading status.")
    parser.add_argument("--since", default=None, help="Print portfolio records since YYYY-MM-DD.")
    parser.add_argument("--quiet", action="store_true", help="Suppress daily/backfill summary output.")
    args = parser.parse_args()

    if args.backfill:
        fdm = DEFAULT_FDM if args.fdm is None else args.fdm
        portfolio = run_backfill(
            price_csv=args.price_csv,
            state_dir=args.state_dir,
            fdm=fdm,
            capital=args.capital,
            verbose=not args.quiet,
        )
        if args.quiet:
            history = portfolio.get_history()
            print(f"backfilled {len(history)} rows")
        return

    if args.since is not None:
        print_records_since(args.state_dir, args.since)
        return

    if args.status:
        print(load_status(args.state_dir))
        return

    run_daily(
        price_csv=args.price_csv,
        state_dir=args.state_dir,
        fdm=args.fdm,
        capital=args.capital,
        verbose=not args.quiet,
    )


def print_records_since(state_dir: Path, since: str) -> None:
    state_path = state_dir / STATE_FILE
    if not state_path.exists():
        print("No paper trading state found.")
        return
    history = pd.read_csv(state_path)
    if history.empty:
        print("No paper trading state found.")
        return
    filtered = history.loc[history["date"] >= since]
    if filtered.empty:
        print(f"No records since {since}.")
        return
    columns = ["date", "equity", "cum_pnl", "target_pos", "daily_pnl", "price"]
    print(filtered.loc[:, columns].to_string(index=False))


if __name__ == "__main__":
    main()
