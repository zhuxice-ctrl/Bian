from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from trading_learning.models import Candle


def load_candles_csv(path: Path, symbol: str) -> list[Candle]:
    candles: list[Candle] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            candles.append(
                Candle(
                    symbol=symbol,
                    opened_at=datetime.fromisoformat(row["opened_at"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
    return candles
