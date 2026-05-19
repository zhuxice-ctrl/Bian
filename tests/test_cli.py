from trading_learning.cli import build_parser, main
from trading_learning.storage.db import connect


def test_cli_has_expected_commands():
    parser = build_parser()
    command_names = {
        action.dest
        for action in parser._subparsers._group_actions[0]._choices_actions
    }
    assert {"init-db", "backtest-ma", "export"}.issubset(command_names)


def test_backtest_ma_persists_generated_trades(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite3"
    csv_path = tmp_path / "prices.csv"
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
    monkeypatch.setenv("TRADING_LEARNING_DB_PATH", str(db_path))

    exit_code = main(
        [
            "backtest-ma",
            "--csv",
            str(csv_path),
            "--symbol",
            "BTCUSDT",
            "--short-window",
            "2",
            "--long-window",
            "3",
        ]
    )

    with connect(db_path) as conn:
        trade_count = conn.execute("select count(*) from trades").fetchone()[0]

    assert exit_code == 0
    assert trade_count > 0
