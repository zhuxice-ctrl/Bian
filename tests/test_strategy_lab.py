from datetime import datetime

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    pass


def _write_csv(path):
    path.parent.mkdir(parents=True)
    rows = ["opened_at,open,high,low,close,volume"]
    for index in range(90):
        rows.append(f"{datetime(2026, 5, 1, index % 24).isoformat()}+00:00,100,101,99,{100 + index},10")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_strategy_profile_set_and_list(tmp_path):
    with connect(tmp_path / "lab.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        saved = handler.handle(
            "/strategy-profile-set name=ma_baseline symbol=BTCUSDT interval=1h csv=data/local/BTCUSDT-1h.csv short=20 long=60 quote_amount=100",
            user_id="owner",
        )
        listed = handler.handle("/strategy-profile-list", user_id="owner")

    assert saved["status"] == "saved"
    assert saved["profile"]["name"] == "ma_baseline"
    assert listed["profiles"][0]["name"] == "ma_baseline"


def test_sweep_ma_runs_parameter_grid_and_stores_group(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "data" / "local" / "BTCUSDT-1h.csv"
    _write_csv(csv_path)

    with connect(tmp_path / "lab.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/sweep-ma symbol=BTCUSDT interval=1h csv=data/local/BTCUSDT-1h.csv shorts=3,5 longs=8,13 starting_cash=1000 quote_amount=100",
            user_id="owner",
        )
        experiment_count = conn.execute("select count(*) from strategy_experiments").fetchone()[0]
        sweep_row = conn.execute("select * from parameter_sweeps").fetchone()

    assert response["status"] == "saved"
    assert response["sweep"]["run_count"] == 4
    assert experiment_count == 4
    assert sweep_row["external_id"] == response["sweep"]["external_id"]
    assert response["sweep"]["best_experiment"]
    assert response["sweep"]["overfitting_warning"]


def test_sweep_ma_rejects_invalid_grid(tmp_path):
    with connect(tmp_path / "lab.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/sweep-ma symbol=BTCUSDT interval=1h csv=data/local/BTCUSDT-1h.csv shorts=20 longs=10",
            user_id="owner",
        )

    assert response["status"] == "invalid"
    assert "no valid" in response["message"]
