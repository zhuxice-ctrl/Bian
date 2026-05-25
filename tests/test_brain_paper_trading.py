import json
from pathlib import Path

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    pass

def _write_paper_files(state_dir: Path) -> Path:
    state_dir.mkdir(parents=True)
    (state_dir / "portfolio_state.csv").write_text(
        "date,price,sig_fast,sig_mom,sig_mr,sig_vol,combined,fdm,inst_vol,target_pos,current_pos,change,cost,daily_pnl,cum_pnl,equity\n"
        "2026-05-24,76000,0.10,-0.20,1.00,-0.70,0.05,2.753598,0.35,0.030,0.020,0.010,0.0001,0.001,12000,112000\n"
        "2026-05-25,77728.79,0.12,-0.35,1.20,-0.88,0.02,2.753598,0.346,0.032,0.030,0.002,0.0001,0.0059,12851.89,112851.89\n",
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
    return state_dir / "portfolio_state.csv"


def test_paper_status_returns_formatted_summary(tmp_path):
    state_dir = tmp_path / "paper"
    _write_paper_files(state_dir)
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), paper_state_dir=state_dir)

        response = handler.handle("/paper-status", user_id="owner")

    assert response["status"] == "ok"
    assert "Bian v1 Paper Trading" in response["message"]
    assert "日期: 2026-05-25" in response["message"]
    assert "权益: 112,851.89 (+12.85%)" in response["message"]
    assert "今日 PnL: +0.59%" in response["message"]
    assert "目标仓位: 0.032" in response["message"]
    assert "FAST=0.12 MOM=-0.35 MR=1.20 VOL=-0.88" in response["message"]
    assert "Combined: 0.02 (FDM=2.75)" in response["message"]


def test_paper_status_without_data_returns_friendly_message(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), paper_state_dir=tmp_path / "missing")

        response = handler.handle("/paper-status", user_id="owner")

    assert response["status"] == "not_found"
    assert "paper trading" in response["message"].lower()
    assert "backfill" in response["message"].lower()


def test_paper_update_calls_update_csv_and_run_daily(tmp_path):
    state_dir = tmp_path / "paper"
    price_csv = tmp_path / "BTCUSDT-1d.csv"
    _write_paper_files(state_dir)
    calls = []

    def fake_update_csv(csv_path):
        calls.append(("update", Path(csv_path)))
        return 3

    def fake_run_daily(*, price_csv, state_dir, verbose):
        calls.append(("run", Path(price_csv), Path(state_dir), verbose))
        return object()

    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(
            conn,
            executor=FakeExecutor(),
            paper_state_dir=state_dir,
            paper_price_csv=price_csv,
            paper_update_csv=fake_update_csv,
            paper_run_daily=fake_run_daily,
        )

        response = handler.handle("/paper-update", user_id="owner")

    assert calls == [("update", price_csv), ("run", price_csv, state_dir, False)]
    assert response["status"] == "ok"
    assert response["added_rows"] == 3
    assert "新增行数: 3" in response["message"]
    assert "今日 PnL: +0.59%" in response["message"]


def test_paper_history_returns_requested_days(tmp_path):
    state_dir = tmp_path / "paper"
    _write_paper_files(state_dir)
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), paper_state_dir=state_dir)

        response = handler.handle("/paper-history days=1", user_id="owner")

    assert response["status"] == "ok"
    assert len(response["history"]) == 1
    assert response["history"][0]["date"] == "2026-05-25"
    assert "2026-05-25" in response["message"]
    assert "0.032" in response["message"]
