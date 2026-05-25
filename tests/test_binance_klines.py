import json
from datetime import timezone
from unittest.mock import Mock, patch

import pytest
import requests

from trading_learning.market_data.binance_klines import (
    fetch_klines,
    save_klines_csv,
    update_csv,
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


def _kline(open_time_ms: int, open_price: str = "100.0") -> list[object]:
    return [
        open_time_ms,
        open_price,
        "105.0",
        "99.0",
        "104.0",
        "12.5",
        open_time_ms + 86_399_999,
        "0",
        1,
        "0",
        "0",
        "0",
    ]


def _mock_response(payload: object) -> Mock:
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_fetch_klines_returns_dataframe_from_public_api():
    response = _mock_response([_kline(1777593600000)])

    with patch("trading_learning.market_data.binance_klines.requests.get", return_value=response) as get:
        frame = fetch_klines(
            symbol="btcusdt",
            interval="1d",
            start_ms=1777593600000,
            limit=1,
        )

    assert list(frame.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(frame) == 1
    assert str(frame.loc[0, "timestamp"].tzinfo) == "UTC"
    assert frame.loc[0, "open"] == 100.0
    assert frame.loc[0, "close"] == 104.0
    assert frame.loc[0, "volume"] == 12.5
    get.assert_called_once_with(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "1d", "limit": 1, "startTime": 1777593600000},
        timeout=30,
    )


def test_update_csv_creates_new_csv_with_project_schema(tmp_path):
    csv_path = tmp_path / "BTCUSDT-1d.csv"
    response = _mock_response([_kline(1777593600000), _kline(1777680000000, "110.0")])

    with patch("trading_learning.market_data.binance_klines.requests.get", return_value=response):
        added = update_csv(csv_path)

    assert added == 2
    assert csv_path.read_text(encoding="utf-8").splitlines() == [
        "opened_at,open,high,low,close,volume",
        "2026-05-01T00:00:00+00:00,100.0,105.0,99.0,104.0,12.5",
        "2026-05-02T00:00:00+00:00,110.0,105.0,99.0,104.0,12.5",
    ]


def test_update_csv_appends_only_new_rows_without_rewriting_existing_rows(tmp_path):
    csv_path = tmp_path / "BTCUSDT-1d.csv"
    original = (
        "opened_at,open,high,low,close,volume\n"
        "2026-05-01T00:00:00+00:00,100,105,99,104,12.5\n"
        "2026-05-02T00:00:00+00:00,110,115,109,114,13.5\n"
    )
    csv_path.write_text(original, encoding="utf-8")
    response = _mock_response([_kline(1777680000000, "110.0"), _kline(1777766400000, "120.0")])

    with patch("trading_learning.market_data.binance_klines.requests.get", return_value=response) as get:
        added = update_csv(csv_path)

    assert added == 1
    params = get.call_args.kwargs["params"]
    assert params["startTime"] == 1777680000000 + 1
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines[:3] == original.splitlines()
    assert lines[3] == "2026-05-03T00:00:00+00:00,120.0,105.0,99.0,104.0,12.5"


def test_update_csv_returns_zero_and_does_not_modify_file_when_no_new_data(tmp_path):
    csv_path = tmp_path / "BTCUSDT-1d.csv"
    original = (
        "opened_at,open,high,low,close,volume\n"
        "2026-05-01T00:00:00+00:00,100,105,99,104,12.5\n"
    )
    csv_path.write_text(original, encoding="utf-8")
    response = _mock_response([])

    with patch("trading_learning.market_data.binance_klines.requests.get", return_value=response):
        added = update_csv(csv_path)

    assert added == 0
    assert csv_path.read_text(encoding="utf-8") == original


def test_fetch_klines_raises_http_errors():
    response = _mock_response([])
    response.raise_for_status.side_effect = requests.HTTPError("blocked")

    with patch("trading_learning.market_data.binance_klines.requests.get", return_value=response):
        with pytest.raises(requests.HTTPError):
            fetch_klines()


def test_fetch_klines_keeps_legacy_candle_mode_for_existing_callers():
    captured_urls = []

    def fake_urlopen(request, timeout):
        captured_urls.append(request.full_url)
        assert timeout == 30
        return FakeResponse([_kline(1777593600000)])

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
        start_time_ms=None,
        urlopen=lambda request, timeout: FakeResponse([_kline(1777593600000)]),
    )
    csv_path = tmp_path / "klines.csv"

    save_klines_csv(candles, csv_path)

    assert csv_path.read_text(encoding="utf-8").splitlines() == [
        "opened_at,open,high,low,close,volume",
        "2026-05-01T00:00:00+00:00,100.0,105.0,99.0,104.0,12.5",
    ]
