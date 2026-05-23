import json

from trading_learning.learning.curriculum import build_failed_experiment_learning
from trading_learning.learning.curriculum import build_review_queue
from trading_learning.storage.db import connect, initialize_schema


def test_failed_experiment_learning_generates_tasks_and_mistake_cards(tmp_path):
    with connect(tmp_path / "learning.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
            ) values (
              'exp-loss',
              'breakout',
              'BTCUSDT',
              '1h',
              'data/local/BTCUSDT-1h.csv',
              '{"lookback": 20}',
              '{"realized_pnl": -15.5, "win_rate": 0.25, "trade_count": 8}',
              'failed breakout'
            )
            """
        )
        conn.execute(
            """
            insert into experiment_review_drafts (external_id, experiment_external_id, content)
            values (
              'experiment-review-exp-loss',
              'exp-loss',
              ?
            )
            """,
            (
                json.dumps(
                    {
                        "risk_flags": [
                            {"code": "negative_pnl", "severity": "high", "message": "Loss"},
                            {"code": "low_win_rate", "severity": "medium", "message": "Low win rate"},
                        ],
                        "learning_tasks": ["Replay the failed breakout entries."],
                    }
                ),
            ),
        )
        conn.commit()

        result = build_failed_experiment_learning(conn, "exp-loss")
        cards = conn.execute(
            "select external_id, category, source from knowledge_cards order by external_id"
        ).fetchall()

    assert result["status"] == "saved"
    assert result["experiment_external_id"] == "exp-loss"
    assert result["tasks"][0]["title"] == "Replay the failed breakout entries."
    assert result["tasks"][0]["experiment_external_id"] == "exp-loss"
    assert [card["external_id"] for card in cards] == [
        "knowledge-mistake-exp-loss-low_win_rate",
        "knowledge-mistake-exp-loss-negative_pnl",
    ]
    assert {card["category"] for card in cards} == {"mistake_pattern"}
    assert {card["source"] for card in cards} == {"failed_experiment"}


def test_review_queue_ranks_high_severity_recent_lessons_first(tmp_path):
    with connect(tmp_path / "queue.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into knowledge_cards (external_id, title, category, content, source, created_at, updated_at)
            values
              ('old-low', 'Old low', 'mistake_pattern', 'Low priority', 'failed_experiment', '2026-05-20 00:00:00', '2026-05-20 00:00:00'),
              ('new-high', 'New high', 'mistake_pattern', 'High priority', 'failed_experiment', '2026-05-22 00:00:00', '2026-05-22 00:00:00'),
              ('manual', 'Manual', 'psychology', 'Manual note', 'manual', '2026-05-23 00:00:00', '2026-05-23 00:00:00')
            """
        )
        conn.executemany(
            "insert into knowledge_card_tags (card_external_id, tag) values (?, ?)",
            [
                ("old-low", "fee_pressure"),
                ("new-high", "negative_pnl"),
                ("new-high", "low_win_rate"),
                ("manual", "discipline"),
            ],
        )
        conn.commit()

        queue = build_review_queue(conn, today="2026-05-23", limit=3)

    assert [item["card_external_id"] for item in queue] == ["new-high", "old-low", "manual"]
    assert queue[0]["importance"] > queue[1]["importance"]
    assert queue[0]["reason"] == "high-risk mistake pattern"
    assert queue[2]["reason"] == "general review"
