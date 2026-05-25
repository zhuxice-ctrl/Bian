import importlib.util
import json
import sys
from pathlib import Path

from trading_learning.market_data import binance_klines
from trading_learning.market_data.catalog import dataset_path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backfill_klines.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("backfill_klines_script_funding", SCRIPT_PATH)
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


def test_fetch_funding_rate_history_calls_binance_usdm_endpoint_and_preserves_fields():
    captured_urls = []

    def fake_urlopen(request, timeout):
        captured_urls.append(request.full_url)
        assert request.get_method() == "GET"
        assert timeout == 30
        return FakeResponse(
            [
                {
                    "symbol": "BTCUSDT",
                    "fundingTime": 1777593600000,
                    "fundingRate": "0.00010000",
                    "markPrice": "100.50",
                }
            ]
        )

    rows = binance_klines.fetch_funding_rate_history(
        symbol="btcusdt",
        start_ms=1777593600000,
        end_ms=1777680000000,
        limit=1,
        urlopen=fake_urlopen,
    )

    assert "/fapi/v1/fundingRate?" in captured_urls[0]
    assert "symbol=BTCUSDT" in captured_urls[0]
    assert "startTime=1777593600000" in captured_urls[0]
    assert "endTime=1777680000000" in captured_urls[0]
    assert "limit=1" in captured_urls[0]
    assert rows == [
        {
            "fundingTime": 1777593600000,
            "fundingRate": "0.00010000",
            "markPrice": "100.50",
        }
    ]


def test_fetch_funding_rate_history_paginates_until_response_is_not_full():
    captured_urls = []
    pages = [
        [
            {"fundingTime": 1000, "fundingRate": "0.00010000", "markPrice": "100.50"},
            {"fundingTime": 2000, "fundingRate": "0.00020000", "markPrice": "101.50"},
        ],
        [
            {"fundingTime": 3000, "fundingRate": "0.00030000", "markPrice": "102.50"},
        ],
    ]

    def fake_urlopen(request, timeout):
        del timeout
        captured_urls.append(request.full_url)
        return FakeResponse(pages[len(captured_urls) - 1])

    rows = binance_klines.fetch_funding_rate_history(
        symbol="BTCUSDT",
        start_ms=1000,
        end_ms=4000,
        limit=2,
        urlopen=fake_urlopen,
    )

    assert "startTime=1000" in captured_urls[0]
    assert "startTime=2001" in captured_urls[1]
    assert [row["fundingTime"] for row in rows] == [1000, 2000, 3000]


def test_catalog_funding_rate_dataset_uses_funding_path_and_required_fields(tmp_path):
    root = tmp_path / "data" / "local"
    path = dataset_path("btcusdt", "funding_rate", root=root)

    assert path == root / "market_data" / "BTCUSDT" / "funding" / "BTCUSDT-funding.csv"

    binance_klines.save_funding_rate_csv(
        [
            {
                "fundingTime": 1777593600000,
                "fundingRate": "0.00010000",
                "markPrice": "100.50",
                "ignored": "not written",
            }
        ],
        path,
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "fundingTime,fundingRate,markPrice",
        "1777593600000,0.00010000,100.50",
    ]


def test_backfill_script_supports_funding_data_type_without_kline_backfill(monkeypatch, capsys):
    calls = []

    def fake_fetch_funding_rate_history(**kwargs):
        calls.append(kwargs)
        return [{"fundingTime": kwargs["start_ms"], "fundingRate": "0.00010000", "markPrice": "100.50"}]

    def fake_save_funding_rate_csv(rows, path):
        calls.append({"rows": rows, "path": path})

    def unexpected_backfill(**kwargs):
        raise AssertionError(f"funding backfill must not call kline backfill: {kwargs}")

    monkeypatch.setattr(backfill_klines_script, "fetch_funding_rate_history", fake_fetch_funding_rate_history)
    monkeypatch.setattr(backfill_klines_script, "save_funding_rate_csv", fake_save_funding_rate_csv)
    monkeypatch.setattr(backfill_klines_script, "backfill_symbol", unexpected_backfill)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "backfill_klines.py",
            "--symbols",
            "BTCUSDT",
            "--data-type",
            "funding",
            "--months",
            "1",
            "--no-backup",
        ],
    )

    assert backfill_klines_script.main() == 0
    output = capsys.readouterr().out

    assert calls[0]["symbol"] == "BTCUSDT"
    assert isinstance(calls[0]["start_ms"], int)
    assert isinstance(calls[0]["end_ms"], int)
    assert calls[1]["rows"] == [
        {"fundingTime": calls[0]["start_ms"], "fundingRate": "0.00010000", "markPrice": "100.50"}
    ]
    assert str(calls[1]["path"]).endswith("market_data/BTCUSDT/funding/BTCUSDT-funding.csv") or str(
        calls[1]["path"]
    ).endswith("market_data\\BTCUSDT\\funding\\BTCUSDT-funding.csv")
    assert "[BTCUSDT] saved funding rows=1" in output
