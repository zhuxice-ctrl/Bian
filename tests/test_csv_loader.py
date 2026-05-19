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
