from __future__ import annotations

from trading_learning.models import Candle, Signal, SignalAction


def simple_average(values: list[float]) -> float:
    return sum(values) / len(values)


def moving_average_crossover_signals(
    candles: list[Candle],
    short_window: int,
    long_window: int,
) -> list[Signal]:
    if short_window <= 0 or long_window <= 0:
        raise ValueError("windows must be positive")
    if short_window >= long_window:
        raise ValueError("short_window must be lower than long_window")

    signals: list[Signal] = []
    previous_relation: int | None = None

    closes = [candle.close for candle in candles]
    for index in range(long_window - 1, len(candles)):
        short_ma = simple_average(closes[index - short_window + 1 : index + 1])
        long_ma = simple_average(closes[index - long_window + 1 : index + 1])
        relation = 1 if short_ma > long_ma else -1 if short_ma < long_ma else 0

        if previous_relation is not None:
            if previous_relation <= 0 and relation > 0:
                signals.append(
                    Signal(
                        symbol=candles[index].symbol,
                        timestamp=candles[index].opened_at,
                        action=SignalAction.BUY,
                        reason=f"short MA {short_window} crossed above long MA {long_window}",
                    )
                )
            elif previous_relation >= 0 and relation < 0:
                signals.append(
                    Signal(
                        symbol=candles[index].symbol,
                        timestamp=candles[index].opened_at,
                        action=SignalAction.SELL,
                        reason=f"short MA {short_window} crossed below long MA {long_window}",
                    )
                )

        previous_relation = relation

    return signals
