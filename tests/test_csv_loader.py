from pathlib import Path

from trading_learning.market_data.csv_loader import load_candles_csv


def test_load_candles_csv_parses_rows():
    candles = load_candles_csv(
        Path("tests/fixtures/btcusdt_1h_sample.csv"),
        symbol="BTCUSDT",
    )

    assert len(candles) == 3
    assert candles[0].symbol == "BTCUSDT"
    assert candles[0].open == 100.0
    assert candles[1].close == 107.0
    assert candles[2].volume == 14.0


def test_load_candles_csv_handles_utf8_bom(tmp_path):
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "opened_at,open,high,low,close,volume\n"
        "2024-01-01T00:00:00,100,105,99,104,12\n",
        encoding="utf-8-sig",
    )

    candles = load_candles_csv(csv_path, symbol="BTCUSDT")

    assert len(candles) == 1
    assert candles[0].symbol == "BTCUSDT"
    assert candles[0].open == 100.0
    assert candles[0].close == 104.0
