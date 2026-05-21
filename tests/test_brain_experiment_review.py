import json

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    def test_order(self, **kwargs):
        return {}


def _seed_experiment(conn):
    csv_path = "data/local/BTCUSDT-1h.csv"
    conn.execute(
        """
        insert into strategy_experiments (
          external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
        ) values ('exp-review', 'moving_average_crossover', 'BTCUSDT', '1h', ?, '{"starting_cash": 1000}', '{}')
        """,
        (csv_path,),
    )
    conn.executemany(
        """
        insert into trades (external_id, symbol, side, quantity, price, fee, timestamp, reason, source)
        values (?, 'BTCUSDT', ?, 1, ?, ?, ?, 'signal', 'exp-review')
        """,
        [
            ("buy-1", "BUY", 100, 0.5, "2026-05-21T00:00:00+00:00"),
            ("sell-1", "SELL", 95, 0.5, "2026-05-21T01:00:00+00:00"),
        ],
    )
    conn.commit()


def _write_csv(tmp_path):
    csv_path = tmp_path / "data" / "local" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,101,99,100,10\n"
        "2026-05-21T01:00:00+00:00,100,101,94,95,12\n",
        encoding="utf-8",
    )


def test_experiment_review_command_persists_draft_and_audits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_csv(tmp_path)
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        _seed_experiment(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/experiment-review experiment=exp-review", user_id="owner")
        row = conn.execute(
            "select * from experiment_review_drafts where experiment_external_id = ?",
            ("exp-review",),
        ).fetchone()
        audit = conn.execute("select status from brain_audit_logs order by id desc limit 1").fetchone()
        content = json.loads(row["content"])

    assert response["status"] == "saved"
    assert response["experiment_external_id"] == "exp-review"
    assert response["external_id"] == "experiment-review-exp-review"
    assert response["draft"]["summary"]["realized_pnl"] < 0
    assert row["external_id"] == "experiment-review-exp-review"
    assert content["summary"]["experiment_external_id"] == "exp-review"
    assert audit["status"] == "saved"


def test_experiment_review_command_rejects_missing_experiment(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/experiment-review experiment=missing", user_id="owner")

    assert response["status"] == "not_found"
    assert "experiment" in response["message"]
