from __future__ import annotations

import argparse
from pathlib import Path

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.config import load_config
from trading_learning.export_import.exporter import export_zip
from trading_learning.journal.repository import save_trades
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.storage.db import connect, initialize_schema
from trading_learning.strategy.moving_average import moving_average_crossover_signals


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading-learning")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="initialize the local database")

    backtest = subparsers.add_parser("backtest-ma", help="run a moving-average backtest")
    backtest.add_argument("--csv", required=True)
    backtest.add_argument("--symbol", required=True)
    backtest.add_argument("--short-window", type=int, default=20)
    backtest.add_argument("--long-window", type=int, default=60)
    backtest.add_argument("--starting-cash", type=float, default=1000.0)
    backtest.add_argument("--quote-amount", type=float, default=100.0)
    backtest.add_argument("--fee-rate", type=float, default=0.001)
    backtest.add_argument("--daily-trade-limit", type=int, default=5)

    export = subparsers.add_parser("export", help="export local learning data")
    export.add_argument("--output", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    with connect(config.db_path) as conn:
        initialize_schema(conn)

        if args.command == "init-db":
            print(f"initialized {config.db_path}")
            return 0

        if args.command == "backtest-ma":
            candles = load_candles_csv(Path(args.csv), args.symbol)
            signals = moving_average_crossover_signals(
                candles,
                short_window=args.short_window,
                long_window=args.long_window,
            )
            prices = {candle.opened_at: candle.close for candle in candles}
            result = run_spot_backtest(
                symbol=args.symbol,
                signals=signals,
                prices_by_timestamp=prices,
                starting_cash=args.starting_cash,
                quote_amount_per_buy=args.quote_amount,
                fee_rate=args.fee_rate,
                daily_trade_limit=args.daily_trade_limit,
            )
            save_trades(conn, result.trades, source="backtest")
            print(f"symbol={result.symbol} trades={result.trade_count} ending_cash={result.ending_cash:.2f}")
            return 0

        if args.command == "export":
            export_zip(conn, Path(args.output))
            print(f"exported {args.output}")
            return 0

    parser.error(f"unknown command {args.command}")
    return 2
