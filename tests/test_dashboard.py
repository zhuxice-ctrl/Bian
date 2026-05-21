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

    assert datasets == {
        "status": "ok",
        "datasets": [
            {
                "symbol": "BTCUSDT",
                "interval": "1h",
                "path": str(csv_path.relative_to(tmp_path)),
                "row_count": 2,
                "first_opened_at": "2026-05-21T00:00:00+00:00",
                "last_opened_at": "2026-05-21T01:00:00+00:00",
            }
        ],
    }


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
            finally:
                os.chdir(original_cwd)
        finally:
            server.shutdown()
            thread.join()

        assert overview["status"] == "ok"
        assert "Trading Learning Dashboard" in html
        assert "lightweight-charts.standalone.production.js" in html
        assert vendor_status == 200
        assert datasets["status"] == "ok"
        assert datasets["datasets"][0]["symbol"] == "BTCUSDT"
        assert report["status"] == "not_found"


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
        'id="klineChart"',
        'id="volumeChart"',
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
        "function loadDataset",
        "function loadBacktestReport",
        "function renderBacktestReport",
        "function focusTrade",
        "/api/backtest-report",
        "/api/datasets",
    ]:
        assert marker in script
