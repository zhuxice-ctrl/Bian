from datetime import datetime
from pathlib import Path
from uuid import uuid4

from trading_learning.brain.commands import BrainCommandHandler
from trading_learning.models import Candle
from trading_learning.storage.db import connect, initialize_schema


class FakeExecutor:
    def test_order(self, **kwargs):
        return {}


def test_history_download_saves_public_klines_without_exchange_keys(tmp_path):
    captured = {}

    def fake_fetcher(**kwargs):
        captured.update(kwargs)
        return [
            Candle(
                symbol="BTCUSDT",
                opened_at=datetime.fromisoformat("2026-05-20T09:00:00+00:00"),
                open=100.0,
                high=105.0,
                low=99.0,
                close=104.0,
                volume=12.5,
            )
        ]

    output = Path("data/local") / f"test-{uuid4().hex}-BTCUSDT-1h.csv"
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), kline_fetcher=fake_fetcher)

        try:
            response = handler.handle(
                f"/history-download symbol=BTCUSDT interval=1h limit=1 output={output}",
                user_id="owner",
            )
            output_lines = output.read_text(encoding="utf-8").splitlines()
        finally:
            if output.exists():
                output.unlink()

    assert response == {
        "status": "saved",
        "message": f"downloaded 1 candles to {output}",
        "path": str(output),
        "count": 1,
        "requires_confirmation": False,
    }
    assert captured == {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "limit": 1,
        "start_time_ms": None,
        "end_time_ms": None,
    }
    assert output_lines == [
        "opened_at,open,high,low,close,volume",
        "2026-05-20T09:00:00+00:00,100.0,105.0,99.0,104.0,12.5",
    ]


def test_history_download_rejects_output_outside_data_local(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            f"/history-download symbol=BTCUSDT interval=1h output={tmp_path / 'outside.csv'}",
            user_id="owner",
        )
        audit_count = conn.execute("select count(*) from brain_audit_logs").fetchone()[0]

    assert response["status"] == "invalid"
    assert "data/local" in response["message"]
    assert audit_count == 1


def test_history_download_rejects_symbols_outside_learning_scope(tmp_path):
    def unexpected_fetcher(**kwargs):
        raise AssertionError("unsupported symbols must be rejected before fetching")

    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), kline_fetcher=unexpected_fetcher)

        response = handler.handle(
            "/history-download symbol=SOLUSDT interval=1h output=data/local/SOLUSDT-1h.csv",
            user_id="owner",
        )
        audit = conn.execute("select status from brain_audit_logs").fetchone()

    assert response["status"] == "invalid"
    assert "symbol not allowed: SOLUSDT" in response["message"]
    assert "BTCUSDT, ETHUSDT" in response["message"]
    assert audit["status"] == "invalid"


def test_history_download_returns_failed_response_when_fetcher_fails(tmp_path):
    def failing_fetcher(**kwargs):
        raise RuntimeError("network unavailable")

    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor(), kline_fetcher=failing_fetcher)

        response = handler.handle(
            "/history-download symbol=BTCUSDT interval=1h output=data/local/fail.csv",
            user_id="owner",
        )
        audit = conn.execute("select status from brain_audit_logs").fetchone()

    assert response["status"] == "failed"
    assert "network unavailable" in response["message"]
    assert audit["status"] == "failed"


def test_backtest_ma_rejects_symbols_outside_learning_scope(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/backtest-ma csv=data/local/SOLUSDT-1h.csv symbol=SOLUSDT short=2 long=3",
            user_id="owner",
        )
        audit = conn.execute("select status from brain_audit_logs").fetchone()

    assert response["status"] == "invalid"
    assert "symbol not allowed: SOLUSDT" in response["message"]
    assert audit["status"] == "invalid"


def test_backtest_ma_persists_trades_and_experiment_summary(tmp_path):
    csv_path = Path("data/local") / f"test-{uuid4().hex}-prices.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "\n".join(
            [
                "opened_at,open,high,low,close,volume",
                "2026-05-20T00:00:00+00:00,3,3,3,3,10",
                "2026-05-20T01:00:00+00:00,2,2,2,2,10",
                "2026-05-20T02:00:00+00:00,1,1,1,1,10",
                "2026-05-20T03:00:00+00:00,4,4,4,4,10",
                "2026-05-20T04:00:00+00:00,5,5,5,5,10",
                "2026-05-20T05:00:00+00:00,1,1,1,1,10",
            ]
        ),
        encoding="utf-8",
    )
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        try:
            response = handler.handle(
                (
                    f"/backtest-ma csv={csv_path} symbol=BTCUSDT interval=1h "
                    "short=2 long=3 starting_cash=1000 quote_amount=100 fee=0.001 "
                    "daily_limit=5 note=first_replay"
                ),
                user_id="owner",
            )
        finally:
            csv_path.unlink(missing_ok=True)
        trade_count = conn.execute("select count(*) from trades").fetchone()[0]
        experiment = conn.execute(
            "select * from strategy_experiments where external_id = ?",
            (response["external_id"],),
        ).fetchone()

    assert response["status"] == "saved"
    assert response["strategy_name"] == "moving_average_crossover"
    assert response["symbol"] == "BTCUSDT"
    assert response["metrics"]["trade_count"] > 0
    assert response["requires_confirmation"] is False
    assert trade_count == response["metrics"]["trade_count"]
    assert experiment["symbol"] == "BTCUSDT"
    assert '"short_window": 2' in experiment["parameters"]
    assert '"trade_count":' in experiment["metrics"]
    assert experiment["note"] == "first replay"


def test_backtest_ma_returns_failed_response_for_missing_csv(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle(
            "/backtest-ma csv=data/local/missing.csv symbol=BTCUSDT short=2 long=3",
            user_id="owner",
        )
        audit = conn.execute("select status from brain_audit_logs").fetchone()

    assert response["status"] == "failed"
    assert "missing.csv" in response["message"]
    assert audit["status"] == "failed"


def test_experiment_summary_returns_recent_experiments(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        conn.execute(
            """
            insert into strategy_experiments (
              external_id, strategy_name, symbol, interval, source_csv, parameters, metrics, note
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "experiment-1",
                "moving_average_crossover",
                "BTCUSDT",
                "1h",
                "prices.csv",
                '{"short_window": 2}',
                '{"trade_count": 2, "realized_pnl": 1.5}',
                "first replay",
            ),
        )
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/experiment-summary limit=1", user_id="owner")

    assert response == {
        "status": "ok",
        "experiments": [
            {
                "external_id": "experiment-1",
                "strategy_name": "moving_average_crossover",
                "symbol": "BTCUSDT",
                "interval": "1h",
                "source_csv": "prices.csv",
                "parameters": {"short_window": 2},
                "metrics": {"trade_count": 2, "realized_pnl": 1.5},
                "note": "first replay",
            }
        ],
        "requires_confirmation": False,
    }


def test_experiment_summary_rejects_invalid_limit_and_audits(tmp_path):
    with connect(tmp_path / "brain.sqlite3") as conn:
        initialize_schema(conn)
        handler = BrainCommandHandler(conn, executor=FakeExecutor())

        response = handler.handle("/experiment-summary limit=abc", user_id="owner")
        audit = conn.execute("select status from brain_audit_logs").fetchone()

    assert response["status"] == "invalid"
    assert "limit must be an integer" in response["message"]
    assert audit["status"] == "invalid"
