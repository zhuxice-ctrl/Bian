import json
import os
from importlib.resources import files
from http.server import HTTPServer
from threading import Thread
from urllib.parse import quote
from urllib.request import urlopen

from trading_learning.dashboard.data import DashboardData
from trading_learning.dashboard.service import build_dashboard_handler
from trading_learning.storage.db import connect, initialize_schema


def test_dashboard_overview_summarizes_learning_records(tmp_path):
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into daily_reviews (
              external_id, review_date, symbols_watched, trade_count, plan_followed, pnl, mistake_tags, lesson
            ) values ('review-1', '2026-05-21', '["BTCUSDT"]', 2, 1, 12.5, '["fomo"]', 'Wait')
            """
        )
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
            ) values ('exp-1', 'ma_cross', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{}', '{"trade_count": 4}')
            """
        )
        conn.execute(
            "insert into knowledge_cards (external_id, title, category, content) values ('card-1', 'FOMO', 'psychology', 'Pause')"
        )
        conn.commit()

        overview = DashboardData(conn).overview()

        assert overview["status"] == "ok"
        assert overview["totals"]["review_days"] == 1
        assert overview["totals"]["review_trade_count"] == 2
        assert overview["totals"]["review_pnl"] == 12.5
        assert overview["totals"]["plan_follow_rate"] == 1.0
        assert overview["totals"]["experiment_count"] == 1
        assert overview["totals"]["knowledge_count"] == 1


def test_dashboard_kline_replay_reads_safe_csv_and_experiment_trades(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00,100,110,90,105,10\n"
        "2026-05-21T01:00:00,105,112,101,108,12\n",
        encoding="utf-8",
    )
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
            ) values ('exp-1', 'ma_cross', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{}', '{}')
            """
        )
        conn.execute(
            """
            insert into trades (external_id, symbol, side, quantity, price, fee, timestamp, reason, source)
            values ('trade-1', 'BTCUSDT', 'BUY', 1, 105, 0.1, '2026-05-21T00:00:00', 'signal', 'exp-1')
            """
        )
        conn.commit()

        replay = DashboardData(conn).kline_replay("exp-1")

        assert replay["status"] == "ok"
        assert replay["experiment"]["external_id"] == "exp-1"
        assert replay["candles"][0]["close"] == 105.0
        assert replay["trades"][0]["side"] == "BUY"


def test_dashboard_backtest_report_returns_metrics_and_equity_curve(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,110,90,100,10\n"
        "2026-05-21T01:00:00+00:00,100,112,99,110,12\n"
        "2026-05-21T02:00:00+00:00,110,121,109,120,12\n"
        "2026-05-21T03:00:00+00:00,120,122,115,116,12\n",
        encoding="utf-8",
    )
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
            ) values ('exp-report', 'ma_cross', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{"starting_cash": 1000}', '{}')
            """
        )
        conn.executemany(
            """
            insert into trades (external_id, symbol, side, quantity, price, fee, timestamp, reason, source)
            values (?, 'BTCUSDT', ?, 1, ?, ?, ?, 'signal', 'exp-report')
            """,
            [
                ("trade-buy-1", "BUY", 100, 0.5, "2026-05-21T00:00:00+00:00"),
                ("trade-sell-1", "SELL", 110, 0.5, "2026-05-21T01:00:00+00:00"),
                ("trade-buy-2", "BUY", 120, 0.6, "2026-05-21T02:00:00+00:00"),
                ("trade-sell-2", "SELL", 116, 0.4, "2026-05-21T03:00:00+00:00"),
            ],
        )
        conn.commit()

        report = DashboardData(conn).backtest_report("exp-report")

    assert report["status"] == "ok"
    assert report["experiment"]["external_id"] == "exp-report"
    assert report["metrics"]["trade_count"] == 4
    assert report["metrics"]["round_trips"] == 2
    assert report["metrics"]["max_drawdown"] < 0
    assert report["round_trips"][0]["entry_trade_id"] == "trade-buy-1"
    assert report["equity_curve"][0]["equity"] == 1000.0
    assert report["trades"][0]["external_id"] == "trade-buy-1"


def test_dashboard_backtest_report_returns_filter_metadata_and_trade_results(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,110,90,100,10\n"
        "2026-05-21T01:00:00+00:00,100,112,99,110,12\n"
        "2026-05-21T02:00:00+00:00,110,121,109,120,12\n"
        "2026-05-21T03:00:00+00:00,120,122,115,116,12\n",
        encoding="utf-8",
    )
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
            ) values ('exp-filter', 'ma_cross', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{"starting_cash": 1000}', '{}')
            """
        )
        conn.executemany(
            """
            insert into trades (external_id, symbol, side, quantity, price, fee, timestamp, reason, source)
            values (?, 'BTCUSDT', ?, 1, ?, ?, ?, 'signal', 'exp-filter')
            """,
            [
                ("trade-buy-1", "BUY", 100, 0.5, "2026-05-21T00:00:00+00:00"),
                ("trade-sell-1", "SELL", 110, 0.5, "2026-05-21T01:00:00+00:00"),
                ("trade-buy-2", "BUY", 120, 0.6, "2026-05-21T02:00:00+00:00"),
                ("trade-sell-2", "SELL", 116, 0.4, "2026-05-21T03:00:00+00:00"),
            ],
        )
        conn.execute(
            """
            insert into experiment_review_drafts (external_id, experiment_external_id, content)
            values (
              'experiment-review-exp-filter',
              'exp-filter',
              '{"risk_flags": [{"code": "negative_pnl", "severity": "high", "message": "Loss"}]}'
            )
            """
        )
        conn.commit()

        report = DashboardData(conn).backtest_report("exp-filter")

    assert report["filter_options"] == {
        "sides": ["BUY", "SELL"],
        "results": ["win", "loss"],
        "risk_flags": ["negative_pnl"],
        "start_time": "2026-05-21T00:00:00+00:00",
        "end_time": "2026-05-21T03:00:00+00:00",
    }
    trade_results = {trade["external_id"]: trade["round_trip_result"] for trade in report["trades"]}
    assert trade_results == {
        "trade-buy-1": "win",
        "trade-sell-1": "win",
        "trade-buy-2": "loss",
        "trade-sell-2": "loss",
    }
    assert report["trades"][0]["round_trip_pnl"] == 9.0
    assert report["trades"][2]["round_trip_pnl"] == -5.0


def test_dashboard_experiment_comparison_returns_metrics_and_parameters(tmp_path):
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        conn.executemany(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
            ) values (?, 'ma_cross', ?, '1h', ?, ?, ?, ?)
            """,
            [
                (
                    "exp-a",
                    "BTCUSDT",
                    "data/local/BTCUSDT-1h.csv",
                    '{"short_window": 10, "long_window": 30}',
                    '{"trade_count": 4, "realized_pnl": 12.5, "win_rate": 0.5}',
                    "baseline",
                ),
                (
                    "exp-b",
                    "ETHUSDT",
                    "data/local/ETHUSDT-1h.csv",
                    '{"short_window": 20, "long_window": 60}',
                    '{"trade_count": 6, "realized_pnl": -4.0, "win_rate": 0.33}',
                    "slower",
                ),
            ],
        )
        conn.commit()

        comparison = DashboardData(conn).experiment_comparison(["exp-a", "exp-b"])

    assert comparison["status"] == "ok"
    assert [item["external_id"] for item in comparison["experiments"]] == ["exp-a", "exp-b"]
    assert comparison["experiments"][0]["parameters"] == {"short_window": 10, "long_window": 30}
    assert comparison["experiments"][1]["metrics"]["realized_pnl"] == -4.0
    assert comparison["metric_keys"] == ["realized_pnl", "trade_count", "win_rate"]
    assert comparison["parameter_keys"] == ["long_window", "short_window"]


def test_dashboard_control_console_aggregates_product_state(tmp_path):
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into remote_tasks (
              external_id, requester_user_id, command_text, task_type, risk_level, payload, state
            ) values ('task-1', 'owner', '/queue-status', 'local_status', 'query', '{}', 'queued')
            """
        )
        conn.execute(
            """
            insert into experiment_proposals (
              external_id, hypothesis_external_id, source_experiment_external_id, content
            ) values (
              'proposal-1',
              'hypothesis-1',
              'experiment-1',
              '{"external_id": "proposal-1", "hypothesis": {"title": "Next MA test"}, "suggested_command": "/queue-backtest-ma symbol=BTCUSDT"}'
            )
            """
        )
        conn.execute(
            """
            insert into strategy_profiles (
              external_id, name, strategy_name, symbol, interval, source_csv, parameters
            ) values ('profile-1', 'ma_baseline', 'moving_average_crossover', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{"short_window": 20}')
            """
        )
        conn.execute(
            """
            insert into parameter_sweeps (
              external_id, strategy_name, symbol, interval, source_csv, grid, result
            ) values (
              'sweep-1',
              'moving_average_crossover',
              'BTCUSDT',
              '1h',
              'data/local/BTCUSDT-1h.csv',
              '{"shorts": [10], "longs": [40]}',
              '{"external_id": "sweep-1", "run_count": 1, "best_experiment": "experiment-2", "overfitting_warning": "research only"}'
            )
            """
        )
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
            ) values ('experiment-2', 'moving_average_crossover', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{}', '{}')
            """
        )
        conn.execute(
            """
            insert into experiment_decisions (
              experiment_external_id, decision, reason
            ) values ('experiment-2', 'testnet_candidate', 'stable_out_of_sample')
            """
        )
        conn.execute(
            """
            insert into testnet_order_records (
              external_id, user_id, action, symbol, side, order_type, order_id, status
            ) values ('testnet-order-1', 'owner', 'create_order', 'BTCUSDT', 'BUY', 'MARKET', '123', 'FILLED')
            """
        )
        conn.commit()

        console = DashboardData(conn).control_console()

    assert console["status"] == "ok"
    assert console["health"]["status"] == "ok"
    assert "workspace_state" in console
    assert console["tasks"][0]["external_id"] == "task-1"
    assert "daily_plan" in console["coach"]
    assert console["coach"]["proposals"][0]["external_id"] == "proposal-1"
    assert console["strategy_lab"]["profiles"][0]["name"] == "ma_baseline"
    assert console["strategy_lab"]["sweeps"][0]["best_experiment"] == "experiment-2"
    assert console["strategy_lab"]["decisions"][0]["decision"] == "testnet_candidate"
    assert console["testnet"]["orders"][0]["order_id"] == "123"
    assert console["production_gate"]["real_trading_enabled"] is False
    assert [item["project"] for item in console["references"]] == ["Freqtrade", "Jesse", "vectorbt"]


def test_dashboard_experiment_review_returns_stored_or_generated_draft(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,110,90,100,10\n"
        "2026-05-21T01:00:00+00:00,100,112,94,95,12\n",
        encoding="utf-8",
    )
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
            ) values ('exp-review', 'ma_cross', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{"starting_cash": 1000}', '{}')
            """
        )
        conn.executemany(
            """
            insert into trades (external_id, symbol, side, quantity, price, fee, timestamp, reason, source)
            values (?, 'BTCUSDT', ?, 1, ?, 0.5, ?, 'signal', 'exp-review')
            """,
            [
                ("trade-buy-1", "BUY", 100, "2026-05-21T00:00:00+00:00"),
                ("trade-sell-1", "SELL", 95, "2026-05-21T01:00:00+00:00"),
            ],
        )
        conn.commit()

        generated = DashboardData(conn).experiment_review("exp-review")
        conn.execute(
            """
            insert into experiment_review_drafts (external_id, experiment_external_id, content)
            values ('experiment-review-exp-review', 'exp-review', '{"summary": {"experiment_external_id": "exp-review"}, "risk_flags": []}')
            """
        )
        conn.commit()
        stored = DashboardData(conn).experiment_review("exp-review")

    assert generated["status"] == "generated"
    assert generated["persisted"] is False
    assert generated["draft"]["summary"]["experiment_external_id"] == "exp-review"
    assert generated["draft"]["risk_flags"][0]["code"] == "negative_pnl"
    assert stored["status"] == "ok"
    assert stored["persisted"] is True
    assert stored["external_id"] == "experiment-review-exp-review"


def test_dashboard_experiment_review_generates_preview_when_draft_table_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,110,90,100,10\n"
        "2026-05-21T01:00:00+00:00,100,112,94,95,12\n",
        encoding="utf-8",
    )
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute("drop table experiment_review_drafts")
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
            ) values ('exp-legacy', 'ma_cross', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{"starting_cash": 1000}', '{}')
            """
        )
        conn.executemany(
            """
            insert into trades (external_id, symbol, side, quantity, price, fee, timestamp, reason, source)
            values (?, 'BTCUSDT', ?, 1, ?, 0.5, ?, 'signal', 'exp-legacy')
            """,
            [
                ("trade-buy-1", "BUY", 100, "2026-05-21T00:00:00+00:00"),
                ("trade-sell-1", "SELL", 95, "2026-05-21T01:00:00+00:00"),
            ],
        )
        conn.commit()

        generated = DashboardData(conn).experiment_review("exp-legacy")

    assert generated["status"] == "generated"
    assert generated["persisted"] is False
    assert generated["draft"]["summary"]["experiment_external_id"] == "exp-legacy"


def test_dashboard_dataset_inventory_lists_local_market_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,110,90,105,10\n"
        "2026-05-21T01:00:00+00:00,105,112,101,108,12\n",
        encoding="utf-8",
    )
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)

        datasets = DashboardData(conn).datasets()

    cached = [dataset for dataset in datasets["datasets"] if dataset["exists"]]
    missing = [dataset for dataset in datasets["datasets"] if not dataset["exists"]]

    assert datasets["status"] == "ok"
    assert len(cached) == 1
    assert len(missing) == 11
    assert cached[0]["symbol"] == "BTCUSDT"
    assert cached[0]["interval"] == "1h"
    assert cached[0]["path"] == str(csv_path.relative_to(tmp_path))
    assert cached[0]["row_count"] == 2
    assert cached[0]["first_opened_at"] == "2026-05-21T00:00:00+00:00"
    assert cached[0]["last_opened_at"] == "2026-05-21T01:00:00+00:00"
    assert cached[0]["source"] == "binance_public_cache"
    assert missing[0]["source"] == "missing_local_cache"


def test_dashboard_http_serves_api_and_static_page(tmp_path):
    csv_path = tmp_path / "data" / "local" / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,110,90,105,10\n",
        encoding="utf-8",
    )
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        conn_ctx = connect(tmp_path / "dashboard.sqlite3")
    finally:
        os.chdir(original_cwd)
    with conn_ctx as conn:
        initialize_schema(conn)
        handler_cls = build_dashboard_handler(DashboardData(conn))
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/api/overview", timeout=5) as response:
                overview = json.loads(response.read().decode("utf-8"))
            with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5) as response:
                html = response.read().decode("utf-8")
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/static/vendor/lightweight-charts.standalone.production.js",
                timeout=5,
            ) as response:
                vendor_status = response.status
            original_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/datasets", timeout=5) as response:
                    datasets = json.loads(response.read().decode("utf-8"))
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/backtest-report?experiment=missing", timeout=5) as response:
                    report = json.loads(response.read().decode("utf-8"))
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/experiment-review?experiment=missing", timeout=5) as response:
                    review = json.loads(response.read().decode("utf-8"))
                with urlopen(
                    f"http://127.0.0.1:{server.server_port}/api/experiment-comparison?experiments=missing",
                    timeout=5,
                ) as response:
                    comparison = json.loads(response.read().decode("utf-8"))
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/control-console", timeout=5) as response:
                    console = json.loads(response.read().decode("utf-8"))
            finally:
                os.chdir(original_cwd)
        finally:
            server.shutdown()
            thread.join()

        assert overview["status"] == "ok"
        assert "Bian Local Quant Workstation" in html
        assert "lightweight-charts.standalone.production.js" in html
        assert vendor_status == 200
        assert datasets["status"] == "ok"
        assert datasets["datasets"][0]["symbol"] == "BTCUSDT"
        assert report["status"] == "not_found"
        assert review["status"] == "not_found"
        assert comparison["status"] == "ok"
        assert comparison["experiments"] == []
        assert console["status"] == "ok"


def test_dashboard_http_rejects_kline_paths_outside_data_local(tmp_path):
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        handler_cls = build_dashboard_handler(DashboardData(conn))
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/kline?csv={quote('../secret.csv')}&symbol=BTCUSDT"
            with urlopen(url, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            thread.join()

        assert body["status"] == "invalid"
        assert "data/local" in body["message"]


def test_dashboard_static_page_exposes_interactive_replay_controls():
    html = files("trading_learning.dashboard.static").joinpath("index.html").read_text(encoding="utf-8")

    for marker in [
        'id="playPause"',
        'id="stepBack"',
        'id="stepForward"',
        'id="nextTrade"',
        'id="toggleMa20"',
        'id="toggleMa60"',
        'id="ohlcPanel"',
        'id="tradeDetail"',
        'id="datasetSelect"',
        'id="loadDataset"',
        'id="datasetList"',
        'id="reportMetrics"',
        'id="equityChart"',
        'id="tradeTable"',
        'id="tradeSideFilter"',
        'id="tradeResultFilter"',
        'id="tradeStartFilter"',
        'id="tradeEndFilter"',
        'id="tradeRiskFilter"',
        'id="clearTradeFilters"',
        'id="comparisonSelect"',
        'id="loadComparison"',
        'id="comparisonTable"',
        'id="experimentDecisionList"',
        'id="experimentReviewStatus"',
        'id="reviewSummary"',
        'id="reviewRiskFlags"',
        'id="reviewFocusTrades"',
        'id="reviewQuestions"',
        'id="reviewLearningTasks"',
        'id="consoleMetrics"',
        'id="appNav"',
        'id="emptyStatePanel"',
        'id="workspaceStatus"',
        'id="dailyCoachPlan"',
        'id="backtestForm"',
        'id="backtestStrategy"',
        'id="backtestStart"',
        'id="backtestEnd"',
        'id="backtestTrainRatio"',
        'id="runBacktestAction"',
        'id="backtestActionStatus"',
        'id="saveReviewDraftAction"',
        'id="commitReviewAction"',
        'id="taskQueueList"',
        'id="coachProposalList"',
        'id="strategyProfileList"',
        'id="sweepList"',
        'id="testnetOrderList"',
        'id="productionGatePanel"',
        'id="klineChart"',
        'id="volumeChart"',
        'id="workstationShell"',
        'id="pageToday"',
        'id="pageChart"',
        'id="pageData"',
        'id="pageStrategy"',
        'id="pageBacktests"',
        'id="pageExperiments"',
        'id="pageReview"',
        'id="pageKnowledge"',
        'id="pageTestnet"',
        'id="pageSafety"',
        'id="pageSettings"',
        'id="coachPanel"',
        'id="coachToggle"',
        'id="coachTitle"',
        'id="coachBody"',
        'data-route="chart"',
        'data-page="chart"',
        "lightweight-charts.standalone.production.js",
    ]:
        assert marker in html


def test_dashboard_static_script_uses_lightweight_charts_engine():
    script = files("trading_learning.dashboard.static").joinpath("app.js").read_text(encoding="utf-8")

    for marker in [
        "LightweightCharts.createChart",
        "LightweightCharts.CandlestickSeries",
        "LightweightCharts.HistogramSeries",
        "LightweightCharts.LineSeries",
        "LightweightCharts.createSeriesMarkers",
        "subscribeCrosshairMove",
        "subscribeClick",
        "function startPlayback",
        "function stepReplay",
        "function jumpToNextTrade",
        "function movingAverage",
        "function renderDatasets",
        "function renderEmptyState",
        "function renderControlConsole",
        "function renderWorkspaceStatus",
        "function renderDailyCoachPlan",
        "function renderTaskQueue",
        "function renderCoachProposals",
        "function renderStrategyLab",
        "function renderProductionGate",
        "function loadDataset",
        "function loadBacktestReport",
        "function renderBacktestReport",
        "function filteredReportTrades",
        "function renderTradeFilters",
        "function renderTradeTable",
        "function loadExperimentComparison",
        "function renderExperimentComparison",
        "function loadExperimentReview",
        "function runDashboardBacktest",
        "function saveReviewDraftAction",
        "function commitReviewAction",
        "function postJson",
        "function renderExperimentReview",
        "function renderRiskFlags",
        "function renderFocusTrades",
        "function focusTrade",
        "const routes =",
        "function navigateTo",
        "function setActiveRoute",
        "function renderCoachPanel",
        "function toggleCoach",
        "function renderTopStatus",
        "window.addEventListener(\"hashchange\"",
        "/api/backtest-report",
        "/api/experiment-comparison",
        "/api/experiment-review",
        "/api/datasets",
        "/api/control-console",
        "/api/actions/backtest-ma",
        "/api/actions/experiment-review",
        "/api/actions/experiment-review-commit",
    ]:
        assert marker in script
