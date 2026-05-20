import json
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


def test_dashboard_http_serves_api_and_static_page(tmp_path):
    with connect(tmp_path / "dashboard.sqlite3") as conn:
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
        finally:
            server.shutdown()
            thread.join()

        assert overview["status"] == "ok"
        assert "Trading Learning Dashboard" in html


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
