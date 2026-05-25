import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "daily_update.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("daily_update_script", SCRIPT_PATH)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
daily_update = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(daily_update)


def test_main_updates_csv_runs_trade_and_prints_status(tmp_path, monkeypatch, capsys):
    price_csv = tmp_path / "BTCUSDT-1d.csv"
    price_csv.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-02T00:00:00+00:00,110,115,109,114,13.5\n",
        encoding="utf-8",
    )
    calls = []

    def fake_update_csv(csv_path):
        calls.append(("update", Path(csv_path)))
        return 2

    def fake_run_daily(*, price_csv, verbose=True):
        calls.append(("trade", Path(price_csv), verbose))
        return object()

    monkeypatch.setattr(daily_update, "update_csv", fake_update_csv)
    monkeypatch.setattr(daily_update.daily_runner, "run_daily", fake_run_daily)
    monkeypatch.setattr(daily_update.daily_runner, "load_status", lambda: "date=2026-05-02 equity=101000.00")

    exit_code = daily_update.main(["--price-csv", str(price_csv), "--trade", "--status"])

    assert exit_code == 0
    assert calls == [
        ("update", price_csv),
        ("trade", price_csv, True),
    ]
    output = capsys.readouterr().out
    assert "added_rows=2 latest_date=2026-05-02" in output
    assert "date=2026-05-02 equity=101000.00" in output


def test_main_push_flag_sends_optional_feishu_summary(tmp_path, monkeypatch, capsys):
    price_csv = tmp_path / "BTCUSDT-1d.csv"
    price_csv.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-02T00:00:00+00:00,110,115,109,114,13.5\n",
        encoding="utf-8",
    )
    push_calls = []

    monkeypatch.setattr(daily_update, "update_csv", lambda csv_path: 0)
    monkeypatch.setattr(daily_update.daily_runner, "run_daily", lambda **kwargs: object())
    monkeypatch.setattr(daily_update.daily_runner, "load_status", lambda: "date=2026-05-02 equity=101000.00")

    def fake_push(*, state_dir):
        push_calls.append(Path(state_dir))
        return {"status": "sent", "message_id": "msg-1"}

    monkeypatch.setattr(daily_update, "send_paper_summary_if_enabled", fake_push)

    exit_code = daily_update.main(["--price-csv", str(price_csv), "--trade", "--status", "--push"])

    assert exit_code == 0
    assert push_calls == [daily_update.daily_runner.DEFAULT_STATE_DIR]
    assert "feishu_push=sent" in capsys.readouterr().out


@pytest.mark.parametrize(
    "error",
    [
        requests.ConnectionError("network blocked"),
        requests.HTTPError("403 Client Error", response=Mock(status_code=403)),
        requests.HTTPError("451 Client Error", response=Mock(status_code=451)),
    ],
)
def test_main_handles_blocked_binance_without_trade(tmp_path, monkeypatch, capsys, error):
    price_csv = tmp_path / "BTCUSDT-1d.csv"

    def fake_update_csv(csv_path):
        del csv_path
        raise error

    def unexpected_run_daily(**kwargs):
        raise AssertionError(f"trade must not run after blocked update: {kwargs}")

    monkeypatch.setattr(daily_update, "update_csv", fake_update_csv)
    monkeypatch.setattr(daily_update.daily_runner, "run_daily", unexpected_run_daily)

    exit_code = daily_update.main(["--price-csv", str(price_csv), "--trade", "--status"])

    assert exit_code == 1
    assert "Binance API blocked, try VPN" in capsys.readouterr().out
