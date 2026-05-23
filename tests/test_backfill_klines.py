import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trading_learning.market_data.backfill import backfill_symbol, write_backfilled_dataset
from trading_learning.models import Candle


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backfill_klines.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("backfill_klines_script", SCRIPT_PATH)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
backfill_klines_script = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(backfill_klines_script)


def test_backfill_symbol_paginates_until_end():
    calls = []
    sleeps = []
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=5)

    def fake_fetcher(**kwargs):
        calls.append(kwargs)
        page_start = datetime.fromtimestamp(kwargs["start_time_ms"] / 1000, tz=timezone.utc)
        if len(calls) == 3:
            return [_candle("BTCUSDT", page_start), _candle("BTCUSDT", end)]
        return [_candle("BTCUSDT", page_start), _candle("BTCUSDT", page_start + timedelta(hours=1))]

    candles = backfill_symbol(
        symbol="BTCUSDT",
        interval="1h",
        start=start,
        end=end,
        fetcher=fake_fetcher,
        sleep_fn=sleeps.append,
        request_delay_seconds=0.2,
        page_limit=2,
    )

    assert [candle.opened_at for candle in candles] == [start + timedelta(hours=offset) for offset in range(5)]
    assert [call["start_time_ms"] for call in calls] == [
        int(start.timestamp() * 1000),
        int((start + timedelta(hours=2)).timestamp() * 1000),
        int((start + timedelta(hours=4)).timestamp() * 1000),
    ]
    assert sleeps == [0.2, 0.2]


def test_backfill_symbol_deduplicates_overlapping_pages():
    calls = 0
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=3)

    def fake_fetcher(**kwargs):
        nonlocal calls
        calls += 1
        del kwargs
        if calls == 1:
            return [_candle("ETHUSDT", start), _candle("ETHUSDT", start + timedelta(hours=1))]
        return [
            _candle("ETHUSDT", start + timedelta(hours=1)),
            _candle("ETHUSDT", start + timedelta(hours=2)),
            _candle("ETHUSDT", end),
        ]

    candles = backfill_symbol(
        symbol="ETHUSDT",
        interval="1h",
        start=start,
        end=end,
        fetcher=fake_fetcher,
        sleep_fn=lambda seconds: None,
        page_limit=2,
    )

    assert [candle.opened_at for candle in candles] == [start, start + timedelta(hours=1), start + timedelta(hours=2)]


def test_backfill_symbol_stops_on_empty_page():
    calls = 0
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=5)

    def fake_fetcher(**kwargs):
        nonlocal calls
        calls += 1
        page_start = datetime.fromtimestamp(kwargs["start_time_ms"] / 1000, tz=timezone.utc)
        if calls == 2:
            return []
        return [_candle("BNBUSDT", page_start), _candle("BNBUSDT", page_start + timedelta(hours=1))]

    candles = backfill_symbol(
        symbol="BNBUSDT",
        interval="1h",
        start=start,
        end=end,
        fetcher=fake_fetcher,
        sleep_fn=lambda seconds: None,
        page_limit=2,
    )

    assert [candle.opened_at for candle in candles] == [start, start + timedelta(hours=1)]
    assert calls == 2


def test_backfill_symbol_propagates_fetcher_error():
    calls = 0
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=5)

    def fake_fetcher(**kwargs):
        nonlocal calls
        calls += 1
        page_start = datetime.fromtimestamp(kwargs["start_time_ms"] / 1000, tz=timezone.utc)
        if calls == 2:
            raise RuntimeError("binance unavailable")
        return [_candle("SOLUSDT", page_start), _candle("SOLUSDT", page_start + timedelta(hours=1))]

    with pytest.raises(RuntimeError, match="binance unavailable"):
        backfill_symbol(
            symbol="SOLUSDT",
            interval="1h",
            start=start,
            end=end,
            fetcher=fake_fetcher,
            sleep_fn=lambda seconds: None,
            page_limit=2,
        )

    assert calls == 2


def test_write_backfilled_dataset_creates_backup(tmp_path):
    root = tmp_path / "data" / "local"
    target = root / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"
    target.parent.mkdir(parents=True)
    old_content = (
        "opened_at,open,high,low,close,volume\n"
        "2024-01-01T00:00:00+00:00,10,11,9,10.5,100\n"
    )
    target.write_text(old_content, encoding="utf-8")
    now = datetime(2026, 5, 23, 16, 6, 22, tzinfo=timezone.utc)

    result = write_backfilled_dataset(
        candles=[_candle("BTCUSDT", datetime(2024, 1, 1, 1, tzinfo=timezone.utc))],
        symbol="BTCUSDT",
        interval="1h",
        root=root,
        backup_existing=True,
        now_fn=lambda: now,
    )

    backup = root / "market_data" / "BTCUSDT" / "BTCUSDT-1h.bak-20260523-160622.csv"
    assert result["status"] == "saved"
    assert result["path"] == str(target)
    assert result["backup_path"] == str(backup)
    assert result["row_count"] == 1
    assert backup.read_text(encoding="utf-8") == old_content
    assert "2024-01-01T01:00:00+00:00,1.0,2.0,0.5,1.5,10.0" in target.read_text(encoding="utf-8")


def test_write_backfilled_dataset_skips_backup_when_disabled(tmp_path):
    root = tmp_path / "data" / "local"
    target = root / "market_data" / "ETHUSDT" / "ETHUSDT-1h.csv"
    target.parent.mkdir(parents=True)
    target.write_text("opened_at,open,high,low,close,volume\nold,1,1,1,1,1\n", encoding="utf-8")

    result = write_backfilled_dataset(
        candles=[_candle("ETHUSDT", datetime(2024, 1, 1, tzinfo=timezone.utc))],
        symbol="ETHUSDT",
        interval="1h",
        root=root,
        backup_existing=False,
    )

    assert result["backup_path"] is None
    assert not list(target.parent.glob("*.bak-*.csv"))
    assert "old" not in target.read_text(encoding="utf-8")


def test_write_backfilled_dataset_no_backup_when_target_missing(tmp_path):
    root = tmp_path / "data" / "local"
    target_parent = root / "market_data" / "SOLUSDT"

    result = write_backfilled_dataset(
        candles=[],
        symbol="SOLUSDT",
        interval="1h",
        root=root,
        backup_existing=True,
    )

    assert result == {
        "status": "saved",
        "path": str(target_parent / "SOLUSDT-1h.csv"),
        "backup_path": None,
        "row_count": 0,
        "first_opened_at": None,
        "last_opened_at": None,
    }
    assert not list(target_parent.glob("*.bak-*.csv"))


def test_script_default_range_uses_six_months_for_1m_and_two_years_for_other_intervals():
    end = datetime(2026, 5, 23, 12, tzinfo=timezone.utc)

    assert backfill_klines_script._default_start(end, "1m", years=None, months=None) == datetime(
        2025, 11, 23, 12, tzinfo=timezone.utc
    )
    assert backfill_klines_script._default_start(end, "4h", years=None, months=None) == datetime(
        2024, 5, 23, 12, tzinfo=timezone.utc
    )
    assert backfill_klines_script._default_start(end, "1d", years=None, months=None) == datetime(
        2024, 5, 23, 12, tzinfo=timezone.utc
    )


@pytest.mark.parametrize("interval", ["1m", "4h", "1d"])
def test_script_dry_run_accepts_new_intervals_without_backfill(monkeypatch, capsys, interval):
    calls = []

    def fake_dry_run_plan(**kwargs):
        calls.append(kwargs)
        return {
            "dry_run": True,
            "interval": kwargs["interval"],
            "start": kwargs["start"].isoformat(),
            "end": kwargs["end"].isoformat(),
            "expected_bars_per_symbol": 1,
            "datasets": [
                {
                    "symbol": "BTCUSDT",
                    "path": "data/local/market_data/BTCUSDT/example.csv",
                    "estimated_request_count": 1,
                    "pages": [],
                }
            ],
        }

    def unexpected_backfill(**kwargs):
        raise AssertionError(f"dry-run must not backfill: {kwargs}")

    monkeypatch.setattr(backfill_klines_script, "dry_run_plan", fake_dry_run_plan)
    monkeypatch.setattr(backfill_klines_script, "backfill_symbol", unexpected_backfill)
    monkeypatch.setattr(
        sys,
        "argv",
        ["backfill_klines.py", "--symbols", "BTCUSDT", "--interval", interval, "--dry-run", "--max-pages", "3"],
    )

    assert backfill_klines_script.main() == 0
    output = capsys.readouterr().out

    assert calls[0]["interval"] == interval
    assert calls[0]["max_pages"] == 3
    assert '"total_estimated_request_count": 1' in output


def _candle(symbol: str, opened_at: datetime) -> Candle:
    return Candle(symbol=symbol, opened_at=opened_at, open=1.0, high=2.0, low=0.5, close=1.5, volume=10.0)
