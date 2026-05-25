import json
from importlib.resources import files
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

from trading_learning.dashboard.data import DashboardData
from trading_learning.dashboard.service import build_dashboard_handler
from trading_learning.storage.db import connect, initialize_schema


def _write_paper_files(state_dir: Path, price_csv: Path) -> None:
    state_dir.mkdir(parents=True)
    (state_dir / "portfolio_state.csv").write_text(
        "date,price,sig_fast,sig_mom,sig_mr,sig_vol,combined,fdm,inst_vol,target_pos,current_pos,change,cost,daily_pnl,cum_pnl,equity\n"
        "2026-05-23,75000,0.10,-0.20,1.00,-0.70,0.05,2.753598,0.35,0.030,0.020,0.010,0.0001,-0.002,11800,111800\n"
        "2026-05-24,76000,0.11,-0.30,1.10,-0.80,0.04,2.753598,0.35,0.031,0.030,0.001,0.0001,0.001,12000,112000\n"
        "2026-05-25,77728.79,0.12,-0.35,1.20,-0.88,0.02,2.753598,0.346,0.032,0.031,0.001,0.0001,0.0059,12851.89,112851.89\n",
        encoding="utf-8",
    )
    (state_dir / "latest_signals.json").write_text(
        json.dumps(
            {
                "date": "2026-05-25",
                "sig_trend_fast": 0.12,
                "sig_momentum": -0.35,
                "sig_mean_rev": 1.2,
                "sig_vol_regime": -0.88,
                "combined_forecast": 0.02,
                "fdm": 2.753598,
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "config.json").write_text(
        json.dumps({"capital": 100000, "target_vol": 0.2, "cost_per_round_trip": 0.002}),
        encoding="utf-8",
    )
    price_csv.parent.mkdir(parents=True)
    price_csv.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-23T00:00:00+00:00,1,1,1,75000,10\n"
        "2026-05-24T00:00:00+00:00,1,1,1,76000,10\n"
        "2026-05-25T00:00:00+00:00,1,1,1,77728.79,10\n",
        encoding="utf-8",
    )


def test_paper_trading_status_api_shape(tmp_path):
    state_dir = tmp_path / "paper"
    price_csv = tmp_path / "market" / "BTCUSDT-1d.csv"
    _write_paper_files(state_dir, price_csv)
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)

        status = DashboardData(conn, paper_state_dir=state_dir, paper_price_csv=price_csv).paper_trading_status()

    assert status["status"] == "ok"
    assert status["date"] == "2026-05-25"
    assert status["equity"] == 112851.89
    assert status["cumulative_return_pct"] == 12.85
    assert status["daily_pnl"] == 0.59
    assert status["target_position"] == 0.032
    assert status["signals"]["trend_fast"] == 0.12
    assert status["signals"]["combined"] == 0.02
    assert status["fdm"] == 2.753598
    assert status["config"] == {"capital": 100000.0, "vol_target": 0.2, "cost_per_rt": 0.002}


def test_paper_trading_status_without_data_is_not_500(tmp_path):
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)

        status = DashboardData(conn, paper_state_dir=tmp_path / "missing").paper_trading_status()
        history = DashboardData(conn, paper_state_dir=tmp_path / "missing").paper_trading_history(days=30)

    assert status["status"] == "not_found"
    assert status["date"] == ""
    assert history == {"status": "ok", "history": []}


def test_paper_trading_history_filters_days(tmp_path):
    state_dir = tmp_path / "paper"
    price_csv = tmp_path / "market" / "BTCUSDT-1d.csv"
    _write_paper_files(state_dir, price_csv)
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)

        history = DashboardData(conn, paper_state_dir=state_dir).paper_trading_history(days=2)

    assert history["status"] == "ok"
    assert [row["date"] for row in history["history"]] == ["2026-05-24", "2026-05-25"]
    assert history["history"][1]["signals"]["combined"] == 0.02


def test_paper_trading_equity_curve_includes_benchmark(tmp_path):
    state_dir = tmp_path / "paper"
    price_csv = tmp_path / "market" / "BTCUSDT-1d.csv"
    _write_paper_files(state_dir, price_csv)
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)

        curve = DashboardData(conn, paper_state_dir=state_dir, paper_price_csv=price_csv).paper_trading_equity_curve()

    assert curve["status"] == "ok"
    assert len(curve["equity_curve"]) == 3
    assert curve["equity_curve"][0] == {
        "date": "2026-05-23",
        "equity": 111800.0,
        "benchmark_equity": 100000.0,
    }
    assert curve["equity_curve"][-1]["benchmark_equity"] > 103000


def test_paper_trading_http_endpoints(tmp_path):
    state_dir = tmp_path / "paper"
    price_csv = tmp_path / "market" / "BTCUSDT-1d.csv"
    _write_paper_files(state_dir, price_csv)
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)
        handler_cls = build_dashboard_handler(DashboardData(conn, paper_state_dir=state_dir, paper_price_csv=price_csv))
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/api/paper-trading/status", timeout=5) as response:
                status = json.loads(response.read().decode("utf-8"))
            with urlopen(f"http://127.0.0.1:{server.server_port}/api/paper-trading/history?days=2", timeout=5) as response:
                history = json.loads(response.read().decode("utf-8"))
            with urlopen(f"http://127.0.0.1:{server.server_port}/api/paper-trading/equity-curve", timeout=5) as response:
                curve = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            thread.join()

    assert status["status"] == "ok"
    assert len(history["history"]) == 2
    assert len(curve["equity_curve"]) == 3


def test_control_console_includes_paper_trading_summary(tmp_path):
    state_dir = tmp_path / "paper"
    price_csv = tmp_path / "market" / "BTCUSDT-1d.csv"
    _write_paper_files(state_dir, price_csv)
    with connect(tmp_path / "dashboard.sqlite3") as conn:
        initialize_schema(conn)

        console = DashboardData(conn, paper_state_dir=state_dir, paper_price_csv=price_csv).control_console()

    assert console["status"] == "ok"
    assert console["paper_trading"]["status"] == "ok"
    assert console["paper_trading"]["date"] == "2026-05-25"


def test_dashboard_static_page_exposes_paper_trading_panel():
    html = files("trading_learning.dashboard.static").joinpath("index.html").read_text(encoding="utf-8")

    for marker in [
        'data-route="paper"',
        'id="paperConsoleSummary"',
        'id="pagePaper"',
        'id="paperStatusMetrics"',
        'id="paperSignals"',
        'id="paperEquityChart"',
        'id="paperHistoryTable"',
    ]:
        assert marker in html


def test_dashboard_static_script_loads_paper_trading_apis():
    script = files("trading_learning.dashboard.static").joinpath("app.js").read_text(encoding="utf-8")

    for marker in [
        "paperStatus",
        "function renderPaperTrading",
        "function renderPaperStatus",
        "function renderPaperSignals",
        "function renderPaperEquityCurve",
        "function renderPaperHistoryTable",
        "function renderPaperConsoleSummary",
        "/api/paper-trading/status",
        "/api/paper-trading/history?days=30",
        "/api/paper-trading/equity-curve",
    ]:
        assert marker in script
