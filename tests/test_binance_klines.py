import json
from datetime import timezone
from io import BytesIO

from trading_learning.market_data.binance_klines import (
    fetch_klines,
    save_klines_csv,
)


class FakeResponse:
    def __init__(self, payload: object):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_fetch_klines_parses_binance_rows_and_query():
    captured_urls = []

    def fake_urlopen(request, timeout):
        captured_urls.append(request.full_url)
        assert timeout == 30
        return FakeResponse(
            [
                [
                    1777593600000,
                    "100.0",
                    "105.0",
                    "99.0",
                    "104.0",
                    "12.5",
                    1777597199999,
                    "0",
                    1,
                    "0",
                    "0",
                    "0",
                ]
            ]
        )

    candles = fetch_klines(
        symbol="BTCUSDT",
        interval="1h",
        start_time_ms=1777593600000,
        end_time_ms=1777597200000,
        limit=1,
        urlopen=fake_urlopen,
    )

    assert "symbol=BTCUSDT" in captured_urls[0]
    assert "interval=1h" in captured_urls[0]
    assert "startTime=1777593600000" in captured_urls[0]
    assert candles[0].symbol == "BTCUSDT"
    assert candles[0].opened_at.tzinfo == timezone.utc
    assert candles[0].open == 100.0
    assert candles[0].close == 104.0
    assert candles[0].volume == 12.5


def test_save_klines_csv_writes_loader_compatible_file(tmp_path):
    candles = fetch_klines(
        symbol="BTCUSDT",
        interval="1h",
        limit=1,
        urlopen=lambda request, timeout: FakeResponse(
            [[1777593600000, "100", "105", "99", "104", "12.5"]]
        ),
    )
    csv_path = tmp_path / "klines.csv"

    save_klines_csv(candles, csv_path)

    assert csv_path.read_text(encoding="utf-8").splitlines() == [
        "opened_at,open,high,low,close,volume",
        "2026-05-01T00:00:00+00:00,100.0,105.0,99.0,104.0,12.5",
    ]
