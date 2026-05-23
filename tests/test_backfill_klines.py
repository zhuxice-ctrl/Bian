from datetime import datetime, timedelta, timezone

import pytest

from trading_learning.market_data.backfill import backfill_symbol
from trading_learning.models import Candle


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


def _candle(symbol: str, opened_at: datetime) -> Candle:
    return Candle(symbol=symbol, opened_at=opened_at, open=1.0, high=2.0, low=0.5, close=1.5, volume=10.0)
