from __future__ import annotations

import argparse
from http.server import HTTPServer
from pathlib import Path

from trading_learning.backtest.engine import run_spot_backtest
from trading_learning.backtest.report import summarize_backtest
from trading_learning.ai_assistant.local_codex import LocalCodexClient
from trading_learning.ai_assistant.tasks import create_daily_review_draft
from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.brain.feishu import FeishuBotClient
from trading_learning.brain.feishu import FeishuEventAdapter
from trading_learning.brain.natural_language import LocalCodexBrainAssistant
from trading_learning.brain.service import build_handler
from trading_learning.config import load_config
from trading_learning.config import AppConfig
from trading_learning.dashboard.data import DashboardData
from trading_learning.dashboard.service import build_dashboard_handler
from trading_learning.execution.binance_spot_testnet import BinanceSpotTestnetClient
from trading_learning.export_import.exporter import export_zip
from trading_learning.journal.repository import save_daily_review
from trading_learning.journal.repository import save_trades
from trading_learning.market_data.binance_klines import fetch_klines, save_klines_csv
from trading_learning.market_data.catalog import DEFAULT_MARKET_INTERVALS
from trading_learning.market_data.catalog import refresh_market_data
from trading_learning.market_data.csv_loader import load_candles_csv
from trading_learning.risk.execution_guard import ExecutionRiskGuard, OrderIntent, RiskConfig
from trading_learning.storage.db import connect, connect_readonly, initialize_schema
from trading_learning.strategy.moving_average import moving_average_crossover_signals


class MissingBinanceTestnetExecutor:
    def test_order(self, **kwargs):
        raise RuntimeError("BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET are required")


def build_binance_testnet_executor(config: AppConfig):
    if not config.binance_testnet_api_key or not config.binance_testnet_api_secret:
        return MissingBinanceTestnetExecutor()
    return BinanceSpotTestnetClient(
        base_url=config.binance_testnet_base_url,
        api_key=config.binance_testnet_api_key,
        api_secret=config.binance_testnet_api_secret,
    )


def build_natural_language_assistant(config: AppConfig):
    if not config.local_codex_api_key:
        return None
    client = LocalCodexClient(
        base_url=config.local_codex_base_url,
        api_key=config.local_codex_api_key,
        model=config.local_codex_model,
    )
    try:
        client._validate_loopback_base_url()
    except ValueError:
        return None
    return LocalCodexBrainAssistant(client)


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

    refresh_market = subparsers.add_parser("refresh-market-data", help="refresh default local market data CSV files")
    refresh_market.add_argument("--symbols", default="")
    refresh_market.add_argument("--intervals", default="")
    refresh_market.add_argument("--limit", type=int, default=500)

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

    spot_test = subparsers.add_parser("spot-test-order", help="send a Binance Spot Testnet test order")
    spot_test.add_argument("--symbol", required=True)
    spot_test.add_argument("--side", required=True)
    spot_test.add_argument("--type", required=True)
    spot_test.add_argument("--quantity", type=float)
    spot_test.add_argument("--quote-order-qty", type=float)
    spot_test.add_argument("--price", type=float)
    spot_test.add_argument("--time-in-force")
    spot_test.add_argument("--orders-today", type=int, default=0)
    spot_test.add_argument("--daily-order-limit", type=int, default=5)
    spot_test.add_argument("--max-quote-order-qty", type=float, default=100.0)
    spot_test.add_argument("--allowed-symbols")

    brain_serve = subparsers.add_parser("brain-serve", help="start the local command brain HTTP service")
    brain_serve.add_argument("--host", default="127.0.0.1")
    brain_serve.add_argument("--port", type=int, default=8765)
    brain_serve.add_argument("--allowed-user-id", action="append", default=[])

    dashboard_serve = subparsers.add_parser("dashboard-serve", help="start the local read-only dashboard")
    dashboard_serve.add_argument("--host", default="127.0.0.1")
    dashboard_serve.add_argument("--port", type=int, default=8780)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "dashboard-serve":
        if not config.db_path.exists():
            print(f"dashboard database not found: {config.db_path}. Run `trading-learning init-db` first.")
            return 1
        with connect_readonly(config.db_path) as conn:
            server = HTTPServer(
                (args.host, args.port),
                build_dashboard_handler(DashboardData(conn, allowed_symbols=config.allowed_symbols)),
            )
            print(f"dashboard listening on http://{args.host}:{args.port}/")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        return 0

    with connect(config.db_path) as conn:
        initialize_schema(conn)

        if args.command == "init-db":
            print(f"initialized {config.db_path}")
            return 0

        if args.command == "download-klines":
            symbol = args.symbol.upper()
            if symbol not in config.allowed_symbols:
                print(f"symbol not allowed: {symbol}. allowed: {', '.join(config.allowed_symbols)}")
                return 1
            candles = fetch_klines(
                symbol=symbol,
                interval=args.interval,
                limit=args.limit,
                start_time_ms=args.start_time_ms,
                end_time_ms=args.end_time_ms,
            )
            save_klines_csv(candles, Path(args.output))
            print(f"downloaded {len(candles)} candles to {args.output}")
            return 0

        if args.command == "refresh-market-data":
            symbols = tuple(symbol.upper() for symbol in parse_csv_list(args.symbols)) or config.allowed_symbols
            intervals = tuple(parse_csv_list(args.intervals)) or DEFAULT_MARKET_INTERVALS
            unsupported = [symbol for symbol in symbols if symbol not in config.allowed_symbols]
            if unsupported:
                print(f"symbol not allowed: {unsupported[0]}. allowed: {', '.join(config.allowed_symbols)}")
                return 1
            result = refresh_market_data(
                symbols=symbols,
                intervals=intervals,
                allowed_symbols=config.allowed_symbols,
                limit=args.limit,
            )
            print(f"refreshed {len(result['datasets'])} datasets")
            return 0

        if args.command == "backtest-ma":
            symbol = args.symbol.upper()
            if symbol not in config.allowed_symbols:
                print(f"symbol not allowed: {symbol}. allowed: {', '.join(config.allowed_symbols)}")
                return 1
            candles = load_candles_csv(Path(args.csv), symbol)
            signals = moving_average_crossover_signals(
                candles,
                short_window=args.short_window,
                long_window=args.long_window,
            )
            prices = {candle.opened_at: candle.close for candle in candles}
            result = run_spot_backtest(
                symbol=symbol,
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

        if args.command == "spot-test-order":
            if not config.binance_testnet_api_key or not config.binance_testnet_api_secret:
                print("BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET are required")
                return 1
            intent = OrderIntent(
                symbol=args.symbol,
                side=args.side,
                order_type=args.type,
                quantity=args.quantity,
                quote_order_qty=args.quote_order_qty,
            )
            guard = ExecutionRiskGuard(
                RiskConfig(
                    daily_order_limit=args.daily_order_limit,
                    max_quote_order_qty=args.max_quote_order_qty,
                    allowed_symbols=(
                        tuple(parse_csv_list(args.allowed_symbols))
                        if args.allowed_symbols
                        else config.allowed_symbols
                    ),
                )
            )
            decision = guard.check_order(intent, orders_today=args.orders_today)
            if not decision.allowed:
                print(f"risk rejected: {decision.reason}")
                return 1
            client = BinanceSpotTestnetClient(
                base_url=config.binance_testnet_base_url,
                api_key=config.binance_testnet_api_key,
                api_secret=config.binance_testnet_api_secret,
            )
            client.test_order(
                symbol=args.symbol,
                side=args.side,
                order_type=args.type,
                quantity=args.quantity,
                quote_order_qty=args.quote_order_qty,
                price=args.price,
                time_in_force=args.time_in_force,
            )
            print("test order accepted by Binance Spot Testnet")
            return 0

        if args.command == "brain-serve":
            client = build_binance_testnet_executor(config)
            command_handler = BrainCommandHandler(
                conn,
                executor=client,
                allowed_user_ids=tuple(args.allowed_user_id),
                allowed_market_symbols=config.allowed_symbols,
                natural_language=build_natural_language_assistant(config),
            )
            feishu_messenger = None
            if config.feishu_app_id and config.feishu_app_secret:
                feishu_messenger = FeishuBotClient(config.feishu_app_id, config.feishu_app_secret)
            feishu_adapter = FeishuEventAdapter(
                command_handler,
                verification_token=config.feishu_verification_token,
                encrypt_key=config.feishu_encrypt_key,
                user_id_map=parse_key_value_map(config.feishu_user_map),
                messenger=feishu_messenger,
            )
            server = HTTPServer(
                (args.host, args.port),
                build_handler(command_handler, feishu_adapter=feishu_adapter),
            )
            print(f"brain service listening on http://{args.host}:{args.port}/brain/command")
            print(f"feishu event endpoint listening on http://{args.host}:{args.port}/feishu/events")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0

        if args.command == "export":
            export_zip(conn, Path(args.output))
            print(f"exported {args.output}")
            return 0

    parser.error(f"unknown command {args.command}")
    return 2


def parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_key_value_map(value: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for item in parse_csv_list(value):
        key, separator, mapped_value = item.partition(":")
        if separator and key.strip() and mapped_value.strip():
            pairs[key.strip()] = mapped_value.strip()
    return pairs
