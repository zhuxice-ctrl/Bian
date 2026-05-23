import json

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    def test_order(self, **kwargs):
        return {}


def _seed_learning_day(handler, conn, *, review_date="2026-05-21", plan="no", pnl=-12.5, tags="late_entry"):
    handler.handle(
        f"/plan-set date={review_date} symbols=BTCUSDT max_trades=3 bias=neutral conditions=wait_for_close forbidden=fomo",
        user_id="owner",
    )
    handler.handle(
        f"/checklist date={review_date} symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm",
        user_id="owner",
    )
    handler.handle(
        f"/review-add date={review_date} symbols=BTCUSDT trades=2 plan={plan} pnl={pnl} tags={tags} lesson=Wait_for_confirmation note=Anxious",
        user_id="owner",
    )
    experiment_id = f"experiment-{review_date}"
    conn.execute(
        """
        insert into strategy_experiments (
          external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experiment_id,
            "moving_average_crossover",
            "BTCUSDT",
            "1h",
            "data/local/BTCUSDT-1h.csv",
            '{"short_window": 2, "long_window": 3}',
            '{"trade_count": 2, "realized_pnl": -2.5, "win_rate": 0.0}',
            "replay after review",
        ),
    )
    knowledge = handler.handle(
        "/knowledge-add title=Late_entry_control category=psychology content=Wait_for_close_confirmation tags=late_entry,discipline",
        user_id="owner",
    )
    handler.handle(
        f"/mistake-link review=review-{review_date} card={knowledge['external_id']} tag=late_entry",
        user_id="owner",
    )
    handler.handle(
        f"/experiment-link review=review-{review_date} experiment={experiment_id} tag={tags} note=Replay_matches_review",
        user_id="owner",
    )
    return experiment_id


def test_daily_report_persists_plan_review_experiment_and_next_actions(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        _seed_learning_day(handler, conn)

        response = handler.handle("/daily-report date=2026-05-21", user_id="owner")
        row = conn.execute("select * from learning_reports where external_id = ?", (response["external_id"],)).fetchone()
        content = json.loads(row["content"])

    assert response["status"] == "saved"
    assert response["report_type"] == "daily"
    assert response["period"] == {"start": "2026-05-21", "end": "2026-05-21"}
    assert response["report"]["summary"]["trade_count"] == 2
    assert response["report"]["summary"]["pnl"] == -12.5
    assert response["report"]["summary"]["plan_followed"] is False
    assert response["report"]["summary"]["focus_tags"] == ["late_entry"]
    assert response["report"]["experiments"][0]["external_id"] == "experiment-2026-05-21"
    assert "Review knowledge card: Late entry control" in response["report"]["next_actions"]
    assert row["report_type"] == "daily"
    assert content["summary"]["pnl"] == -12.5


def test_weekly_report_aggregates_reviews_and_focus_tags(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        _seed_learning_day(handler, conn, review_date="2026-05-20", plan="yes", pnl=5, tags="calm")
        _seed_learning_day(handler, conn, review_date="2026-05-21", plan="no", pnl=-12.5, tags="late_entry")

        response = handler.handle("/weekly-report start=2026-05-20 end=2026-05-21", user_id="owner")
        row = conn.execute("select * from learning_reports where external_id = ?", (response["external_id"],)).fetchone()

    assert response["status"] == "saved"
    assert response["report_type"] == "weekly"
    assert response["report"]["summary"] == {
        "review_count": 2,
        "trade_count": 4,
        "pnl": -7.5,
        "plan_follow_rate": 0.5,
        "linked_experiment_count": 2,
    }
    assert response["report"]["focus_tags"] == [
        {"tag": "calm", "count": 1},
        {"tag": "late_entry", "count": 1},
    ]
    assert response["report"]["next_actions"][0] == "Prioritize plan adherence in the next trading day"
    assert row["report_type"] == "weekly"


def test_learning_next_returns_tasks_without_persisting_a_report(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        _seed_learning_day(handler, conn)

        response = handler.handle("/learning-next date=2026-05-21", user_id="owner")
        report_count = conn.execute("select count(*) from learning_reports").fetchone()[0]

    assert response == {
        "status": "ok",
        "date": "2026-05-21",
        "tasks": [
            "Review knowledge card: Late entry control",
            "Replay linked experiment: experiment-2026-05-21",
            "Prepare next plan with focus tag: late_entry",
        ],
        "requires_confirmation": False,
    }
    assert report_count == 0


def test_learning_queue_command_returns_ranked_review_items(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        conn.execute(
            """
            insert into knowledge_cards (external_id, title, category, content, source, created_at, updated_at)
            values
              ('card-low', 'Low', 'psychology', 'Stay calm', 'manual', '2026-05-20 00:00:00', '2026-05-20 00:00:00'),
              ('card-high', 'Loss pattern', 'mistake_pattern', 'Review losses', 'failed_experiment', '2026-05-22 00:00:00', '2026-05-22 00:00:00')
            """
        )
        conn.execute("insert into knowledge_card_tags (card_external_id, tag) values ('card-high', 'negative_pnl')")
        conn.commit()

        response = handler.handle("/learning-queue limit=2 today=2026-05-23", user_id="owner")

    assert response["status"] == "ok"
    assert [item["card_external_id"] for item in response["queue"]] == ["card-high", "card-low"]
    assert response["queue"][0]["reason"] == "high-risk mistake pattern"
    assert response["requires_confirmation"] is False


def test_failed_experiment_learning_command_creates_cards_and_daily_report_links_tasks(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())
        experiment_id = _seed_learning_day(handler, conn)

        response = handler.handle(f"/experiment-learning experiment={experiment_id}", user_id="owner")
        report = handler.handle("/daily-report date=2026-05-21", user_id="owner")

    assert response["status"] == "saved"
    assert response["knowledge_card_count"] >= 1
    assert report["report"]["experiment_learning_tasks"][0]["experiment_external_id"] == experiment_id


def test_daily_report_rejects_missing_review(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/daily-report date=2026-05-21", user_id="owner")

    assert response["status"] == "not_found"
    assert "review" in response["message"]
