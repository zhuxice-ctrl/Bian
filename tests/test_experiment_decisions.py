import pytest

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.storage.db import connect, initialize_schema
from trading_learning.strategy.decisions import list_experiment_decisions, save_experiment_decision


class FakeExecutor:
    pass


def test_save_experiment_decision_marks_testnet_candidate(tmp_path):
    with connect(tmp_path / "decisions.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (external_id, strategy_name, symbol, interval, source_csv, parameters, metrics)
            values ('exp-1', 'breakout', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{}', '{}')
            """
        )

        decision = save_experiment_decision(
            conn,
            experiment="exp-1",
            decision="testnet_candidate",
            reason="stable_out_of_sample",
        )
        listed = list_experiment_decisions(conn)

    assert decision["decision"] == "testnet_candidate"
    assert listed[0]["experiment_external_id"] == "exp-1"
    assert listed[0]["reason"] == "stable_out_of_sample"


def test_save_experiment_decision_rejects_unknown_decision(tmp_path):
    with connect(tmp_path / "decisions.sqlite3") as conn:
        initialize_schema(conn)

        with pytest.raises(ValueError, match="invalid decision"):
            save_experiment_decision(conn, experiment="exp-1", decision="trade_now")


def test_brain_experiment_decision_command_persists_decision(tmp_path):
    with connect(tmp_path / "decisions.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (external_id, strategy_name, symbol, interval, source_csv, parameters, metrics)
            values ('exp-1', 'breakout', 'BTCUSDT', '1h', 'data/local/BTCUSDT-1h.csv', '{}', '{}')
            """
        )
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/experiment-decision experiment=exp-1 decision=continue_research reason=needs_more_out_of_sample",
            user_id="owner",
        )

    assert response["status"] == "saved"
    assert response["decision"]["decision"] == "continue_research"
    assert response["decision"]["reason"] == "needs more out of sample"
