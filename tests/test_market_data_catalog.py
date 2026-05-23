from datetime import datetime
from pathlib import Path

import pytest

from trading_learning.market_data.catalog import DEFAULT_MARKET_INTERVALS
from trading_learning.market_data.catalog import dataset_path
from trading_learning.market_data.catalog import import_market_csv
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
    _normalize_updated_at(result["datasets"])
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
                "exists": True,
                "source": "binance_public_cache",
                "updated_at": csv_path_stat_any(),
                "gap_count": 0,
                "has_gaps": False,
                "next_expected_opened_at": "2026-05-21T01:00:00+00:00",
            },
            {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "path": str(tmp_path / "data" / "local" / "market_data" / "BTCUSDT" / "15m" / "BTCUSDT-15m.csv"),
                "row_count": 1,
                "first_opened_at": "2026-05-21T00:00:00+00:00",
                "last_opened_at": "2026-05-21T00:00:00+00:00",
                "exists": True,
                "source": "binance_public_cache",
                "updated_at": csv_path_stat_any(),
                "gap_count": 0,
                "has_gaps": False,
                "next_expected_opened_at": "2026-05-21T00:15:00+00:00",
            },
            {
                "symbol": "ETHUSDT",
                "interval": "1h",
                "path": str(tmp_path / "data" / "local" / "market_data" / "ETHUSDT" / "ETHUSDT-1h.csv"),
                "row_count": 1,
                "first_opened_at": "2026-05-21T00:00:00+00:00",
                "last_opened_at": "2026-05-21T00:00:00+00:00",
                "exists": True,
                "source": "binance_public_cache",
                "updated_at": csv_path_stat_any(),
                "gap_count": 0,
                "has_gaps": False,
                "next_expected_opened_at": "2026-05-21T01:00:00+00:00",
            },
            {
                "symbol": "ETHUSDT",
                "interval": "15m",
                "path": str(tmp_path / "data" / "local" / "market_data" / "ETHUSDT" / "15m" / "ETHUSDT-15m.csv"),
                "row_count": 1,
                "first_opened_at": "2026-05-21T00:00:00+00:00",
                "last_opened_at": "2026-05-21T00:00:00+00:00",
                "exists": True,
                "source": "binance_public_cache",
                "updated_at": csv_path_stat_any(),
                "gap_count": 0,
                "has_gaps": False,
                "next_expected_opened_at": "2026-05-21T00:15:00+00:00",
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

    inventory = inventory_datasets(root=root, allowed_symbols=("BTCUSDT",), intervals=("1m", "1h"))
    _normalize_updated_at(inventory)

    assert inventory == [
        {
            "symbol": "BTCUSDT",
            "exists": False,
            "source": "missing_local_cache",
            "interval": "1m",
            "path": str(root / "market_data" / "BTCUSDT" / "1m" / "BTCUSDT-1m.csv"),
            "row_count": 0,
            "first_opened_at": None,
            "last_opened_at": None,
            "updated_at": None,
            "gap_count": 0,
            "has_gaps": False,
            "next_expected_opened_at": None,
        },
        {
            "symbol": "BTCUSDT",
            "exists": True,
            "source": "binance_public_cache",
            "interval": "1h",
            "path": str(csv_path),
            "row_count": 2,
            "first_opened_at": "2026-05-21T00:00:00+00:00",
            "last_opened_at": "2026-05-21T01:00:00+00:00",
            "updated_at": csv_path_stat_any(),
            "gap_count": 0,
            "has_gaps": False,
            "next_expected_opened_at": "2026-05-21T02:00:00+00:00",
        }
    ]


def test_refresh_market_data_merges_incremental_candles_without_duplicates(tmp_path):
    root = tmp_path / "data" / "local"
    csv_path = root / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,105,99,104,12\n"
        "2026-05-21T01:00:00+00:00,104,108,101,107,10\n",
        encoding="utf-8",
    )
    captured = []

    def fake_fetcher(**kwargs):
        captured.append(kwargs)
        return [
            Candle(
                symbol="BTCUSDT",
                opened_at=datetime.fromisoformat("2026-05-21T01:00:00+00:00"),
                open=104.0,
                high=108.0,
                low=101.0,
                close=107.0,
                volume=10.0,
            ),
            Candle(
                symbol="BTCUSDT",
                opened_at=datetime.fromisoformat("2026-05-21T02:00:00+00:00"),
                open=107.0,
                high=111.0,
                low=106.0,
                close=110.0,
                volume=9.0,
            ),
        ]

    result = refresh_market_data(
        symbols=("BTCUSDT",),
        intervals=("1h",),
        allowed_symbols=("BTCUSDT",),
        root=root,
        limit=500,
        fetcher=fake_fetcher,
    )

    rows = csv_path.read_text(encoding="utf-8").splitlines()
    assert captured[0]["start_time_ms"] == 1779328800000
    assert len(rows) == 4
    assert rows[1].startswith("2026-05-21T00:00:00+00:00")
    assert rows[2].startswith("2026-05-21T01:00:00+00:00")
    assert rows[3].startswith("2026-05-21T02:00:00+00:00")
    assert result["datasets"][0]["row_count"] == 3
    assert result["datasets"][0]["next_expected_opened_at"] == "2026-05-21T03:00:00+00:00"


def test_inventory_datasets_reports_interval_gaps(tmp_path):
    root = tmp_path / "data" / "local"
    csv_path = root / "market_data" / "BTCUSDT" / "BTCUSDT-1h.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-21T00:00:00+00:00,100,105,99,104,12\n"
        "2026-05-21T03:00:00+00:00,104,108,101,107,10\n",
        encoding="utf-8",
    )

    inventory = inventory_datasets(root=root, allowed_symbols=("BTCUSDT",), intervals=("1h",))

    assert inventory[0]["has_gaps"] is True
    assert inventory[0]["gap_count"] == 2
    assert inventory[0]["next_expected_opened_at"] == "2026-05-21T04:00:00+00:00"


def test_import_market_csv_copies_manual_dataset_into_market_cache(tmp_path):
    source = tmp_path / "spy.csv"
    source.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2026-05-20T00:00:00+00:00,500,505,499,504,1200\n"
        "2026-05-21T00:00:00+00:00,504,508,503,507,1300\n",
        encoding="utf-8",
    )

    result = import_market_csv(
        source_csv=source,
        symbol="SPY",
        interval="1d",
        root=tmp_path / "data" / "local",
    )

    target = tmp_path / "data" / "local" / "market_data" / "SPY" / "1d" / "SPY-1d.csv"
    assert target.exists()
    assert result["status"] == "saved"
    assert result["dataset"]["symbol"] == "SPY"
    assert result["dataset"]["interval"] == "1d"
    assert result["dataset"]["row_count"] == 2
    assert result["dataset"]["source"] == "manual_csv"


def test_default_market_intervals_include_higher_timeframes():
    assert DEFAULT_MARKET_INTERVALS == ("1m", "5m", "15m", "1h", "4h", "1d")


def csv_path_stat_any():
    return "__ANY_TIMESTAMP__"


def _normalize_updated_at(datasets):
    for dataset in datasets:
        if dataset.get("updated_at"):
            dataset["updated_at"] = csv_path_stat_any()
