from datetime import datetime, timedelta, timezone

import pytest

from trading_learning.market_data.backfill import backfill_symbol, backfill_symbols_to_csv, dry_run_plan
from trading_learning.models import Candle


def test_backfill_symbol_paginates_until_end_without_allowed_symbol_check():
    calls = []
    sleeps = []
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=5)

    def fake_fetcher(**kwargs):
        calls.append(kwargs)
        page_start = datetime.fromtimestamp(kwargs["start_time_ms"] / 1000, tz=timezone.utc)
        if len(calls) == 1:
            return [_candle("SOLUSDT", page_start), _candle("SOLUSDT", page_start + timedelta(hours=1))]
        return [_candle("SOLUSDT", page_start), _candle("SOLUSDT", page_start + timedelta(hours=1))]

    candles = backfill_symbol(
        symbol="SOLUSDT",
        interval="1h",
        start=start,
        end=end,
        fetcher=fake_fetcher,
        sleep_fn=sleeps.append,
        request_delay_seconds=0.1,
        page_limit=2,
    )

    assert [c.opened_at for c in candles] == [start + timedelta(hours=offset) for offset in range(5)]
    assert [call["symbol"] for call in calls] == ["SOLUSDT", "SOLUSDT", "SOLUSDT"]
    assert calls[0]["limit"] == 2
    assert calls[0]["start_time_ms"] == int(start.timestamp() * 1000)
    assert calls[0]["end_time_ms"] == int(end.timestamp() * 1000)
    assert calls[1]["start_time_ms"] == int((start + timedelta(hours=2)).timestamp() * 1000)
    assert calls[2]["start_time_ms"] == int((start + timedelta(hours=4)).timestamp() * 1000)
    assert sleeps == [0.1, 0.1]


def test_backfill_symbol_deduplicates_and_filters_response_to_requested_range():
    start = datetime(2024, 1, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 3, tzinfo=timezone.utc)

    def fake_fetcher(**kwargs):
        del kwargs
        return [
            _candle("BTCUSDT", datetime(2024, 1, 1, 0, tzinfo=timezone.utc)),
            _candle("BTCUSDT", start),
            _candle("BTCUSDT", start),
            _candle("BTCUSDT", datetime(2024, 1, 1, 2, tzinfo=timezone.utc)),
            _candle("BTCUSDT", datetime(2024, 1, 1, 4, tzinfo=timezone.utc)),
        ]

    candles = backfill_symbol(
        symbol="btcusdt",
        interval="1h",
        start=start,
        end=end,
        fetcher=fake_fetcher,
        sleep_fn=lambda seconds: None,
    )

    assert [(c.symbol, c.opened_at) for c in candles] == [
        ("BTCUSDT", start),
        ("BTCUSDT", datetime(2024, 1, 1, 2, tzinfo=timezone.utc)),
    ]


def test_backfill_symbol_rejects_invalid_ranges_and_page_limits():
    start = datetime(2024, 1, 2, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="start must be before end"):
        backfill_symbol(symbol="BTCUSDT", interval="1h", start=start, end=end)

    with pytest.raises(ValueError, match="page_limit"):
        backfill_symbol(symbol="BTCUSDT", interval="1h", start=end, end=start, page_limit=1001)


def test_dry_run_plan_uses_catalog_paths_without_fetching():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    plan = dry_run_plan(symbols=("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"), interval="1h", start=start, end=end)

    assert [item["symbol"] for item in plan["datasets"]] == ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
    assert plan["datasets"][0]["path"].endswith("data\\local\\market_data\\BTCUSDT\\BTCUSDT-1h.csv") or plan["datasets"][0][
        "path"
    ].endswith("data/local/market_data/BTCUSDT/BTCUSDT-1h.csv")
    assert plan["datasets"][0]["estimated_request_count"] == 18
    assert plan["dry_run"] is True


def test_backfill_symbols_to_csv_writes_requested_symbols_to_catalog_paths(tmp_path):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 3, tzinfo=timezone.utc)

    def fake_fetcher(**kwargs):
        symbol = kwargs["symbol"]
        page_start = datetime.fromtimestamp(kwargs["start_time_ms"] / 1000, tz=timezone.utc)
        return [_candle(symbol, page_start), _candle(symbol, page_start + timedelta(hours=1))]

    result = backfill_symbols_to_csv(
        symbols=("BNBUSDT", "SOLUSDT"),
        interval="1h",
        start=start,
        end=end,
        root=tmp_path / "data" / "local",
        fetcher=fake_fetcher,
        sleep_fn=lambda seconds: None,
        page_limit=1000,
    )

    assert result["status"] == "saved"
    assert [dataset["row_count"] for dataset in result["datasets"]] == [3, 3]
    assert (tmp_path / "data" / "local" / "market_data" / "BNBUSDT" / "BNBUSDT-1h.csv").exists()
    assert (tmp_path / "data" / "local" / "market_data" / "SOLUSDT" / "SOLUSDT-1h.csv").exists()


def _candle(symbol: str, opened_at: datetime) -> Candle:
    return Candle(symbol=symbol.upper(), opened_at=opened_at, open=1.0, high=2.0, low=0.5, close=1.5, volume=10.0)
