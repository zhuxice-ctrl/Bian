from datetime import datetime
from pathlib import Path

import pytest

from trading_learning.market_data.catalog import DEFAULT_MARKET_INTERVALS
from trading_learning.market_data.catalog import dataset_path
from trading_learning.market_data.catalog import inventory_datasets
from trading_learning.market_data.catalog import refresh_market_data
from trading_learning.models import Candle


def test_dataset_path_uses_predictable_data_local_layout():
    assert dataset_path("btcusdt", "1h") == Path("data/local/market_data/BTCUSDT/BTCUSDT-1h.csv")


def test_refresh_market_data_rejects_symbols_outside_allowed_scope(tmp_path):
    def unexpected_fetcher(**kwargs):
        raise AssertionError("unsupported symbols must be rejected before fetching")

    with pytest.raises(ValueError, match="symbol not allowed: SOLUSDT"):
        refresh_market_data(
            symbols=("BTCUSDT", "SOLUSDT"),
            intervals=("1h",),
            allowed_symbols=("BTCUSDT", "ETHUSDT"),
            root=tmp_path / "data" / "local",
            fetcher=unexpected_fetcher,
        )


def test_refresh_market_data_writes_each_symbol_interval_and_returns_inventory(tmp_path):
    captured = []

    def fake_fetcher(**kwargs):
        captured.append(kwargs)
        return [
            Candle(
                symbol=kwargs["symbol"],
                opened_at=datetime.fromisoformat("2026-05-21T00:00:00+00:00"),
                open=100.0,
                high=105.0,
                low=99.0,
                close=104.0,
                volume=12.5,
            )
        ]

    result = refresh_market_data(
        symbols=("BTCUSDT", "ETHUSDT"),
        intervals=("1h", "15m"),
        allowed_symbols=("BTCUSDT", "ETHUSDT"),
        root=tmp_path / "data" / "local",
        limit=2,
        fetcher=fake_fetcher,
    )

    assert [item["symbol"] for item in captured] == ["BTCUSDT", "BTCUSDT", "ETHUSDT", "ETHUSDT"]
    assert [item["interval"] for item in captured] == ["1h", "15m", "1h", "15m"]
    assert all(item["limit"] == 2 for item in captured)
    assert result == {
        "status": "saved",
        "datasets": [
            {
                "symbol": "BTCUSDT",
                "interval": "1h",
                "path": str(tmp_path / "data" / "local" / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"),
                "row_count": 1,
                "first_opened_at": "2026-05-21T00:00:00+00:00",
                "last_opened_at": "2026-05-21T00:00:00+00:00",
            },
            {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "path": str(tmp_path / "data" / "local" / "market_data" / "BTCUSDT" / "BTCUSDT-15m.csv"),
                "row_count": 1,
                "first_opened_at": "2026-05-21T00:00:00+00:00",
                "last_opened_at": "2026-05-21T00:00:00+00:00",
            },
            {
                "symbol": "ETHUSDT",
                "interval": "1h",
                "path": str(tmp_path / "data" / "local" / "market_data" / "ETHUSDT" / "ETHUSDT-1h.csv"),
                "row_count": 1,
                "first_opened_at": "2026-05-21T00:00:00+00:00",
                "last_opened_at": "2026-05-21T00:00:00+00:00",
            },
            {
                "symbol": "ETHUSDT",
                "interval": "15m",
                "path": str(tmp_path / "data" / "local" / "market_data" / "ETHUSDT" / "ETHUSDT-15m.csv"),
                "row_count": 1,
                "first_opened_at": "2026-05-21T00:00:00+00:00",
                "last_opened_at": "2026-05-21T00:00:00+00:00",
            },
        ],
    }


def test_inventory_datasets_reads_existing_csv_files(tmp_path):
    root = tmp_path / "data" / "local"
    csv_path = root / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "\ufeffopened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,105,99,104,12\n"
        "2026-05-21T01:00:00+00:00,104,106,101,102,10\n",
        encoding="utf-8",
    )

    inventory = inventory_datasets(root=root, allowed_symbols=("BTCUSDT", "ETHUSDT"), intervals=DEFAULT_MARKET_INTERVALS)

    assert inventory == [
        {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "path": str(csv_path),
            "row_count": 2,
            "first_opened_at": "2026-05-21T00:00:00+00:00",
            "last_opened_at": "2026-05-21T01:00:00+00:00",
        }
    ]
