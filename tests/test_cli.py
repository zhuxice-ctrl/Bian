import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from trading_learning.cli import build_parser, main
from trading_learning.storage.db import connect


def test_cli_has_expected_commands():
    parser = build_parser()
    command_names = {
        action.dest
        for action in parser._subparsers._group_actions[0]._choices_actions
    }
    assert {
        "init-db",
        "download-klines",
        "backtest-ma",
        "review-add",
        "ai-review-draft",
        "export",
    }.issubset(command_names)


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


def test_review_add_persists_daily_review(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("TRADING_LEARNING_DB_PATH", str(db_path))

    exit_code = main(
        [
            "review-add",
            "--date",
            "2026-05-20",
            "--symbols",
            "BTCUSDT,ETHUSDT",
            "--trade-count",
            "2",
            "--plan-followed",
            "yes",
            "--pnl",
            "12.5",
            "--mistake-tags",
            "late_entry,追单",
            "--emotion-note",
            "有点焦虑",
            "--lesson",
            "wait for planned entries",
        ]
    )

    with connect(db_path) as conn:
        row = conn.execute("select * from daily_reviews").fetchone()

    assert exit_code == 0
    assert row["review_date"] == "2026-05-20"
    assert row["symbols_watched"] == '["BTCUSDT", "ETHUSDT"]'
    assert row["plan_followed"] == 1
    assert row["mistake_tags"] == '["late_entry", "追单"]'


class DraftHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        assert "never give buy or sell signals" in body["messages"][0]["content"]
        assert body["messages"][1]["content"] == "review body"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps({"choices": [{"message": {"content": "draft summary"}}]}).encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def test_ai_review_draft_persists_draft(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite3"
    server = HTTPServer(("127.0.0.1", 0), DraftHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("TRADING_LEARNING_DB_PATH", str(db_path))
    monkeypatch.setenv("LOCAL_CODEX_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("LOCAL_CODEX_MODEL", "test-model")
    monkeypatch.setenv("LOCAL_CODEX_API_KEY", "local-key")
    try:
        exit_code = main(
            [
                "ai-review-draft",
                "--source-external-id",
                "review-2026-05-20",
                "--review-text",
                "review body",
            ]
        )
    finally:
        server.shutdown()
        thread.join()

    with connect(db_path) as conn:
        row = conn.execute("select * from ai_drafts").fetchone()

    assert exit_code == 0
    assert row["source_external_id"] == "review-2026-05-20"
    assert row["content"] == "draft summary"


def test_ai_review_draft_requires_local_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADING_LEARNING_DB_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.delenv("LOCAL_CODEX_API_KEY", raising=False)

    exit_code = main(
        [
            "ai-review-draft",
            "--source-external-id",
            "review-2026-05-20",
            "--review-text",
            "review body",
        ]
    )

    assert exit_code == 1
