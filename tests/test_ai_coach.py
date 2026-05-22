import json

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    pass


def _insert_experiment(conn, external_id, realized_pnl, win_rate, short=20, long=60):
    conn.execute(
        """
        insert into strategy_experiments (
          external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
        ) values (?, 'moving_average_crossover', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', ?, ?, '')
        """,
        (
            external_id,
            json.dumps({"short_window": short, "long_window": long, "quote_amount": 100}),
            json.dumps({"realized_pnl": realized_pnl, "win_rate": win_rate, "trade_count": 12}),
        ),
    )
    conn.commit()


def test_coach_next_creates_deterministic_experiment_proposal(tmp_path):
    with connect(tmp_path / "coach.sqlite3") as conn:
        initialize_schema(conn)
        _insert_experiment(conn, "experiment-loss", realized_pnl=-12.5, win_rate=0.25)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/coach-next", user_id="owner")
        proposal_row = conn.execute("select * from experiment_proposals").fetchone()
        hypothesis_row = conn.execute("select * from strategy_hypotheses").fetchone()

    assert response["status"] == "saved"
    assert response["proposal"]["source_experiment_external_id"] == "experiment-loss"
    assert response["proposal"]["hypothesis"]["statement"]
    assert response["proposal"]["suggested_parameters"]["short_window"] == 25
    assert response["proposal"]["suggested_parameters"]["long_window"] == 75
    assert proposal_row["status"] == "proposed"
    assert hypothesis_row["external_id"] == response["proposal"]["hypothesis"]["external_id"]


def test_coach_next_without_experiments_returns_baseline_plan(tmp_path):
    with connect(tmp_path / "coach.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/coach-next", user_id="owner")

    assert response["status"] == "ok"
    assert response["proposal"]["source_experiment_external_id"] == ""
    assert response["proposal"]["suggested_command"].startswith("/queue-backtest-ma")


def test_coach_evaluate_updates_proposal_with_outcome(tmp_path):
    with connect(tmp_path / "coach.sqlite3") as conn:
        initialize_schema(conn)
        _insert_experiment(conn, "experiment-loss", realized_pnl=-12.5, win_rate=0.25)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        proposal = handler.handle("/coach-next", user_id="owner")["proposal"]
        _insert_experiment(conn, "experiment-followup", realized_pnl=8.0, win_rate=0.55, short=25, long=75)

        response = handler.handle(
            f"/coach-evaluate proposal={proposal['external_id']} experiment=experiment-followup",
            user_id="owner",
        )
        row = conn.execute(
            "select status, outcome from experiment_proposals where external_id = ?",
            (proposal["external_id"],),
        ).fetchone()

    assert response["status"] == "saved"
    assert response["outcome"]["verdict"] == "improved"
    assert row["status"] == "evaluated"
    assert json.loads(row["outcome"])["comparison"]["realized_pnl_delta"] == 20.5
