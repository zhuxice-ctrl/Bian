import json
from http.server import HTTPServer
from threading import Thread
from urllib.request import Request, urlopen

from trading_learning.dashboard.data import DashboardData
from trading_learning.dashboard.service import build_dashboard_handler
from trading_learning.storage.db import connect, initialize_schema


def _post(port: int, path: str, body: dict):
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _write_prices(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "opened_at,open,high,low,close,volume",
                "2026-05-20T00:00:00+00:00,3,3,3,3,10",
                "2026-05-20T01:00:00+00:00,2,2,2,2,10",
                "2026-05-20T02:00:00+00:00,1,1,1,1,10",
                "2026-05-20T03:00:00+00:00,4,4,4,4,10",
                "2026-05-20T04:00:00+00:00,5,5,5,5,10",
                "2026-05-20T05:00:00+00:00,1,1,1,1,10",
            ]
        ),
        encoding="utf-8",
    )


def test_dashboard_backtest_action_persists_experiment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"
    _write_prices(csv_path)
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        handler_cls = build_dashboard_handler(DashboardData(conn))
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = _post(
                server.server_port,
                "/api/actions/backtest-ma",
                {
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "csv": "data/local/market_data/BTCUSDT/BTCUSDT-1h.csv",
                    "short": 2,
                    "long": 3,
                },
            )
        finally:
            server.shutdown()
            thread.join()
        experiment_count = conn.execute("select count(*) from strategy_experiments").fetchone()[0]
        trade_count = conn.execute("select count(*) from trades").fetchone()[0]

    assert response["status"] == "saved"
    assert response["external_id"].startswith("experiment-")
    assert response["metrics"]["trade_count"] > 0
    assert experiment_count == 1
    assert trade_count == response["metrics"]["trade_count"]


def test_dashboard_backtest_action_rejects_path_outside_data_local(tmp_path):
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        handler_cls = build_dashboard_handler(DashboardData(conn))
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = _post(
                server.server_port,
                "/api/actions/backtest-ma",
                {"symbol": "BTCUSDT", "interval": "1h", "csv": "../outside.csv", "short": 2, "long": 3},
            )
        finally:
            server.shutdown()
            thread.join()

    assert response["status"] == "invalid"
    assert "data/local" in response["message"]


def test_dashboard_review_actions_persist_and_commit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"
    _write_prices(csv_path)
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        data = DashboardData(conn)
        backtest = data.run_backtest_ma_action(
            {
                "symbol": "BTCUSDT",
                "interval": "1h",
                "csv": "data/local/market_data/BTCUSDT/BTCUSDT-1h.csv",
                "short": 2,
                "long": 3,
            }
        )
        review = data.persist_experiment_review_action({"experiment": backtest["external_id"]})
        commit = data.commit_experiment_review_action({"experiment": backtest["external_id"], "date": "2026-05-22"})

        draft_count = conn.execute("select count(*) from experiment_review_drafts").fetchone()[0]
        review_count = conn.execute("select count(*) from daily_reviews").fetchone()[0]
        card_count = conn.execute("select count(*) from knowledge_cards").fetchone()[0]

    assert review["status"] == "saved"
    assert commit["status"] == "saved"
    assert draft_count == 1
    assert review_count == 1
    assert card_count > 0
