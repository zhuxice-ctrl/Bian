import importlib.util
import json
import sys
from importlib import import_module
from pathlib import Path
from urllib.error import HTTPError

import pytest

from trading_learning.market_data.catalog import dataset_path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backfill_klines.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("backfill_klines_script_okx", SCRIPT_PATH)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
backfill_klines_script = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(backfill_klines_script)


class FakeResponse:
    def __init__(self, payload: object):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeErrorBody:
    def __init__(self, text: str):
        self.text = text

    def read(self):
        return self.text.encode("utf-8")


def _okx_data():
    return import_module("trading_learning.market_data.okx_data")


def test_fetch_okx_funding_rate_history_parses_success_and_fills_missing_fields():
    okx_data = _okx_data()
    captured_urls = []

    def fake_urlopen(request, timeout):
        captured_urls.append(request.full_url)
        assert request.get_method() == "GET"
        assert timeout == 30
        return FakeResponse(
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "fundingRate": "0.000075",
                        "fundingTime": "1777593600000",
                        "realizedRate": "0.000074",
                    }
                ],
            }
        )

    rows = okx_data.fetch_funding_rate_history(
        symbol="btcusdt",
        start_ms=1777590000000,
        end_ms=1777600000000,
        limit=1,
        urlopen=fake_urlopen,
    )

    assert "/api/v5/public/funding-rate-history?" in captured_urls[0]
    assert "instId=BTC-USDT-SWAP" in captured_urls[0]
    assert "limit=1" in captured_urls[0]
    assert rows == [
        {
            "exchange": "okx",
            "fundingTime": 1777593600000,
            "fundingRate": "0.000075",
            "markPrice": "",
            "instId": "BTC-USDT-SWAP",
            "realizedRate": "0.000074",
        }
    ]


def test_fetch_okx_funding_rate_history_public_alias_matches_client():
    okx_data = _okx_data()

    assert okx_data.fetch_okx_funding_rate_history is okx_data.fetch_funding_rate_history


def test_fetch_okx_funding_rate_history_paginates_older_pages_with_after_cursor():
    okx_data = _okx_data()
    captured_urls = []
    pages = [
        {
            "code": "0",
            "msg": "",
            "data": [
                {"instId": "BTC-USDT-SWAP", "fundingTime": "3000", "fundingRate": "0.3"},
                {"instId": "BTC-USDT-SWAP", "fundingTime": "2000", "fundingRate": "0.2"},
            ],
        },
        {
            "code": "0",
            "msg": "",
            "data": [
                {"instId": "BTC-USDT-SWAP", "fundingTime": "1000", "fundingRate": "0.1"},
            ],
        },
    ]

    def fake_urlopen(request, timeout):
        del timeout
        captured_urls.append(request.full_url)
        return FakeResponse(pages[len(captured_urls) - 1])

    rows = okx_data.fetch_funding_rate_history(
        symbol="BTCUSDT",
        start_ms=1000,
        end_ms=3500,
        limit=2,
        urlopen=fake_urlopen,
    )

    assert "after=" not in captured_urls[0]
    assert "after=2000" in captured_urls[1]
    assert [row["fundingTime"] for row in rows] == [1000, 2000, 3000]


def test_fetch_okx_funding_rate_history_raises_diagnostic_error_for_api_error():
    okx_data = _okx_data()

    def fake_urlopen(request, timeout):
        del request, timeout
        return FakeResponse({"code": "51001", "msg": "Instrument ID does not exist", "data": []})

    with pytest.raises(okx_data.OkxAPIError, match="OKX API error code=51001 msg=Instrument ID does not exist"):
        okx_data.fetch_funding_rate_history(
            symbol="NOTREALUSDT",
            start_ms=1000,
            end_ms=2000,
            urlopen=fake_urlopen,
        )


def test_fetch_okx_funding_rate_history_raises_diagnostic_error_for_http_error():
    okx_data = _okx_data()

    def fake_urlopen(request, timeout):
        del request, timeout
        raise HTTPError(
            url="https://www.okx.com/api/v5/public/funding-rate-history",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=FakeErrorBody('{"code":"50011","msg":"Rate limit"}'),
        )

    with pytest.raises(
        okx_data.OkxAPIError,
        match=r"OKX HTTP error status=429 reason=Too Many Requests body=.*Rate limit",
    ):
        okx_data.fetch_funding_rate_history(symbol="BTCUSDT", start_ms=1000, end_ms=2000, urlopen=fake_urlopen)


def test_save_okx_funding_rate_csv_writes_expected_columns_and_okx_catalog_path(tmp_path):
    okx_data = _okx_data()
    root = tmp_path / "data" / "local"
    path = dataset_path("btcusdt", "funding_rate", root=root, exchange="okx")

    assert path == root / "market_data" / "BTCUSDT" / "funding" / "BTCUSDT-funding-okx.csv"

    okx_data.save_funding_rate_csv(
        [
            {
                "exchange": "okx",
                "fundingTime": 1777593600000,
                "fundingRate": "0.000075",
                "markPrice": "",
                "instId": "BTC-USDT-SWAP",
                "realizedRate": "0.000074",
                "ignored": "not written",
            }
        ],
        path,
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "exchange,fundingTime,fundingRate,markPrice,instId,realizedRate",
        "okx,1777593600000,0.000075,,BTC-USDT-SWAP,0.000074",
    ]


def test_backfill_script_supports_okx_funding_without_binance_funding(monkeypatch, capsys):
    calls = []

    def fake_fetch_okx_funding_rate_history(**kwargs):
        calls.append(kwargs)
        return [
            {
                "exchange": "okx",
                "fundingTime": kwargs["start_ms"],
                "fundingRate": "0.000075",
                "markPrice": "",
                "instId": "BTC-USDT-SWAP",
                "realizedRate": "0.000074",
            }
        ]

    def fake_save_okx_funding_rate_csv(rows, path):
        calls.append({"rows": rows, "path": path})

    def unexpected_binance_fetch(**kwargs):
        raise AssertionError(f"okx funding backfill must not call binance funding: {kwargs}")

    monkeypatch.setattr(backfill_klines_script, "fetch_okx_funding_rate_history", fake_fetch_okx_funding_rate_history)
    monkeypatch.setattr(backfill_klines_script, "save_okx_funding_rate_csv", fake_save_okx_funding_rate_csv)
    monkeypatch.setattr(backfill_klines_script, "fetch_funding_rate_history", unexpected_binance_fetch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "backfill_klines.py",
            "--exchange",
            "okx",
            "--symbols",
            "BTCUSDT",
            "--data-type",
            "funding",
            "--months",
            "1",
            "--max-pages",
            "2",
            "--no-backup",
        ],
    )

    assert backfill_klines_script.main() == 0
    output = capsys.readouterr().out

    assert calls[0]["symbol"] == "BTCUSDT"
    assert calls[0]["max_pages"] == 2
    assert calls[1]["rows"][0]["exchange"] == "okx"
    assert str(calls[1]["path"]).endswith("market_data/BTCUSDT/funding/BTCUSDT-funding-okx.csv") or str(
        calls[1]["path"]
    ).endswith("market_data\\BTCUSDT\\funding\\BTCUSDT-funding-okx.csv")
    assert "[BTCUSDT] saved okx funding rows=1" in output
