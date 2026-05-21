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


def test_experiment_review_command_accepts_windows_style_data_local_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_csv(tmp_path)
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        _seed_experiment(conn)
        conn.execute(
            "update strategy_experiments set source_csv = 'data\\local\\BTCUSDT-1h.csv' where external_id = 'exp-review'"
        )
        conn.commit()
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/experiment-review experiment=exp-review", user_id="owner")

    assert response["status"] == "saved"
    assert response["experiment_external_id"] == "exp-review"


def test_experiment_review_command_rejects_missing_experiment(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/experiment-review experiment=missing", user_id="owner")

    assert response["status"] == "not_found"
    assert "experiment" in response["message"]


def test_experiment_review_commit_writes_learning_loop_records(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_csv(tmp_path)
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        _seed_experiment(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/experiment-review-commit experiment=exp-review date=2026-05-21", user_id="owner")
        review = conn.execute("select * from daily_reviews where external_id = 'review-2026-05-21'").fetchone()
        experiment_link = conn.execute("select * from review_experiment_links").fetchone()
        cards = conn.execute("select * from knowledge_cards where source = 'experiment_review' order by external_id").fetchall()
        card_tags = conn.execute("select tag from knowledge_card_tags order by tag").fetchall()
        mistake_links = conn.execute("select * from mistake_knowledge_links").fetchall()
        report = conn.execute(
            "select * from learning_reports where report_type = 'daily' and period_start = '2026-05-21'"
        ).fetchone()

    expected_card_count = len(response["draft"]["review_questions"]) + len(response["draft"]["learning_tasks"])
    assert response["status"] == "saved"
    assert response["review_external_id"] == "review-2026-05-21"
    assert response["experiment_external_id"] == "exp-review"
    assert response["knowledge_card_count"] == expected_card_count
    assert response["learning_report_external_id"] == "learning-report-daily-2026-05-21"
    assert review["symbols_watched"] == '["BTCUSDT"]'
    assert review["trade_count"] == 2
    assert review["pnl"] < 0
    assert json.loads(review["mistake_tags"]) == [flag["code"] for flag in response["draft"]["risk_flags"]]
    assert experiment_link["review_external_id"] == "review-2026-05-21"
    assert experiment_link["experiment_external_id"] == "exp-review"
    assert len(cards) == expected_card_count
    assert all(card["source"] == "experiment_review" for card in cards)
    assert {row["tag"] for row in card_tags} >= {"negative_pnl", "losing_trades"}
    assert len(mistake_links) == expected_card_count
    assert report["external_id"] == "learning-report-daily-2026-05-21"


def test_experiment_review_commit_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_csv(tmp_path)
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        _seed_experiment(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        first = handler.handle("/experiment-review-commit experiment=exp-review date=2026-05-21", user_id="owner")
        second = handler.handle("/experiment-review-commit experiment=exp-review date=2026-05-21", user_id="owner")
        review_count = conn.execute("select count(*) from daily_reviews").fetchone()[0]
        card_count = conn.execute("select count(*) from knowledge_cards where source = 'experiment_review'").fetchone()[0]
        experiment_link_count = conn.execute("select count(*) from review_experiment_links").fetchone()[0]
        mistake_link_count = conn.execute("select count(*) from mistake_knowledge_links").fetchone()[0]

    expected_card_count = len(first["draft"]["review_questions"]) + len(first["draft"]["learning_tasks"])
    assert second["status"] == "saved"
    assert review_count == 1
    assert card_count == expected_card_count
    assert experiment_link_count == 1
    assert mistake_link_count == expected_card_count


def test_experiment_review_commit_uses_saved_draft_when_source_csv_is_unavailable(tmp_path):
    draft = {
        "summary": {
            "experiment_external_id": "exp-review",
            "strategy_name": "moving_average_crossover",
            "symbol": "BTCUSDT",
            "interval": "1h",
            "trade_count": 2,
            "round_trips": 1,
            "realized_pnl": -5.0,
            "win_rate": 0.0,
            "max_drawdown": -5.0,
            "total_fees": 1.0,
        },
        "risk_flags": [{"code": "negative_pnl", "severity": "high", "message": "Loss"}],
        "review_questions": ["What caused the loss?"],
        "focus_trades": [],
        "learning_tasks": ["Replay the losing trade."],
    }
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics
            ) values ('exp-review', 'moving_average_crossover', 'BTCUSDT', '1h', 'data/local/missing.csv', '{}', '{}')
            """
        )
        conn.execute(
            """
            insert into experiment_review_drafts (external_id, experiment_external_id, content)
            values ('experiment-review-exp-review', 'exp-review', ?)
            """,
            (json.dumps(draft),),
        )
        conn.commit()
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/experiment-review-commit experiment=exp-review date=2026-05-21", user_id="owner")

    assert response["status"] == "saved"
    assert response["draft"] == draft
    assert response["knowledge_card_count"] == 2
