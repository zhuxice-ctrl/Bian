from trading_learning.learning.experiment_review import build_experiment_review_draft


def test_experiment_review_draft_flags_loss_drawdown_and_low_win_rate():
    report = {
        "experiment": {
            "external_id": "exp-loss",
            "strategy_name": "moving_average_crossover",
            "symbol": "BTCUSDT",
            "interval": "1h",
        },
        "metrics": {
            "trade_count": 8,
            "round_trips": 4,
            "win_count": 1,
            "loss_count": 3,
            "win_rate": 0.25,
            "realized_pnl": -25.0,
            "total_fees": 12.0,
            "max_drawdown": -40.0,
            "max_drawdown_pct": -0.04,
        },
        "round_trips": [
            {
                "entry_trade_id": "buy-1",
                "exit_trade_id": "sell-1",
                "entry_time": "2026-05-21T00:00:00+00:00",
                "exit_time": "2026-05-21T01:00:00+00:00",
                "entry_price": 100.0,
                "exit_price": 96.0,
                "fees": 2.0,
                "pnl": -6.0,
                "pnl_pct": -0.06,
            },
            {
                "entry_trade_id": "buy-2",
                "exit_trade_id": "sell-2",
                "entry_time": "2026-05-21T02:00:00+00:00",
                "exit_time": "2026-05-21T03:00:00+00:00",
                "entry_price": 100.0,
                "exit_price": 101.0,
                "fees": 2.0,
                "pnl": -1.0,
                "pnl_pct": -0.01,
            },
        ],
    }

    draft = build_experiment_review_draft(report)

    assert draft["summary"] == {
        "experiment_external_id": "exp-loss",
        "strategy_name": "moving_average_crossover",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "trade_count": 8,
        "round_trips": 4,
        "realized_pnl": -25.0,
        "win_rate": 0.25,
        "max_drawdown": -40.0,
        "total_fees": 12.0,
    }
    assert [flag["code"] for flag in draft["risk_flags"]] == [
        "negative_pnl",
        "drawdown",
        "low_win_rate",
        "losing_trades",
        "fee_pressure",
    ]
    assert draft["focus_trades"][0]["entry_trade_id"] == "buy-1"
    assert draft["focus_trades"][0]["exit_trade_id"] == "sell-1"
    assert any("loss source" in question for question in draft["review_questions"])
    assert any("drawdown" in task for task in draft["learning_tasks"])


def test_experiment_review_draft_returns_maintenance_task_when_no_major_flags():
    report = {
        "experiment": {
            "external_id": "exp-win",
            "strategy_name": "moving_average_crossover",
            "symbol": "ETHUSDT",
            "interval": "15m",
        },
        "metrics": {
            "trade_count": 4,
            "round_trips": 2,
            "win_count": 2,
            "loss_count": 0,
            "win_rate": 1.0,
            "realized_pnl": 18.5,
            "total_fees": 1.2,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
        },
        "round_trips": [],
    }

    draft = build_experiment_review_draft(report)

    assert draft["risk_flags"] == []
    assert draft["focus_trades"] == []
    assert draft["review_questions"] == [
        "Which entry conditions were most repeatable in this experiment?",
        "Which rule should be preserved unchanged before the next replay?",
    ]
    assert draft["learning_tasks"] == [
        "Document the conditions that worked and compare them against the next BTCUSDT or ETHUSDT replay."
    ]
