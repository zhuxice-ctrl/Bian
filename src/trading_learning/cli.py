from __future__ import annotations

import argparse
from pathlib import Path

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.backtest.report import summarize_backtest
from trading_learning.ai_assistant.local_codex import LocalCodexClient
from trading_learning.ai_assistant.tasks import create_daily_review_draft
from trading_learning.config import load_config
from trading_learning.export_import.exporter import export_zip
from trading_learning.journal.repository import save_daily_review
from trading_learning.journal.repository import save_trades
from trading_learning.market_data.binance_klines import fetch_klines, save_klines_csv
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.storage.db import connect, initialize_schema
from trading_learning.strategy.moving_average import moving_average_crossover_signals


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading-learning")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="initialize the local database")

    download = subparsers.add_parser("download-klines", help="download Binance Spot klines to CSV")
    download.add_argument("--symbol", required=True)
    download.add_argument("--interval", required=True)
    download.add_argument("--output", required=True)
    download.add_argument("--limit", type=int, default=500)
    download.add_argument("--start-time-ms", type=int)
    download.add_argument("--end-time-ms", type=int)

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

    review = subparsers.add_parser("review-add", help="store a daily trading review")
    review.add_argument("--date", required=True)
    review.add_argument("--symbols", required=True)
    review.add_argument("--trade-count", type=int, required=True)
    review.add_argument("--plan-followed", choices=["yes", "no"], required=True)
    review.add_argument("--pnl", type=float, required=True)
    review.add_argument("--mistake-tags", default="")
    review.add_argument("--emotion-note", default="")
    review.add_argument("--lesson", required=True)

    ai_review = subparsers.add_parser("ai-review-draft", help="create a local Codex review draft")
    ai_review.add_argument("--source-external-id", required=True)
    ai_review.add_argument("--review-text", required=True)

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

        if args.command == "download-klines":
            candles = fetch_klines(
                symbol=args.symbol,
                interval=args.interval,
                limit=args.limit,
                start_time_ms=args.start_time_ms,
                end_time_ms=args.end_time_ms,
            )
            save_klines_csv(candles, Path(args.output))
            print(f"downloaded {len(candles)} candles to {args.output}")
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
            metrics = summarize_backtest(result)
            print(
                " ".join(
                    [
                        f"symbol={result.symbol}",
                        f"trades={result.trade_count}",
                        f"ending_cash={result.ending_cash:.2f}",
                        f"round_trips={metrics.round_trips}",
                        f"win_rate={metrics.win_rate:.2%}",
                        f"realized_pnl={metrics.realized_pnl:.2f}",
                        f"fees={metrics.total_fees:.2f}",
                    ]
                )
            )
            return 0

        if args.command == "review-add":
            review_date = args.date
            save_daily_review(
                conn,
                external_id=f"review-{review_date}",
                review_date=review_date,
                symbols_watched=parse_csv_list(args.symbols),
                trade_count=args.trade_count,
                plan_followed=args.plan_followed == "yes",
                pnl=args.pnl,
                mistake_tags=parse_csv_list(args.mistake_tags),
                emotion_note=args.emotion_note,
                lesson=args.lesson,
            )
            print(f"saved review review-{review_date}")
            return 0

        if args.command == "ai-review-draft":
            if not config.local_codex_api_key:
                print("LOCAL_CODEX_API_KEY is required for ai-review-draft")
                return 1
            client = LocalCodexClient(
                base_url=config.local_codex_base_url,
                api_key=config.local_codex_api_key,
                model=config.local_codex_model,
            )
            draft_id = create_daily_review_draft(
                conn,
                client=client,
                source_external_id=args.source_external_id,
                review_text=args.review_text,
            )
            print(f"saved ai draft {draft_id}")
            return 0

        if args.command == "export":
            export_zip(conn, Path(args.output))
            print(f"exported {args.output}")
            return 0

    parser.error(f"unknown command {args.command}")
    return 2


def parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
