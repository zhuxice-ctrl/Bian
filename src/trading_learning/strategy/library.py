from __future__ import annotations

from typing import Any

from trading_learning.models import Candle, Signal, SignalAction
from trading_learning.strategy.moving_average import moving_average_crossover_signals, simple_average


def generate_strategy_signals(strategy_name: str, candles: list[Candle], parameters: dict[str, Any]) -> list[Signal]:
    normalized = strategy_name.strip().lower()
    if normalized in {"moving_average_crossover", "ma_cross", "ma"}:
        return moving_average_crossover_signals(
            candles,
            short_window=int(parameters.get("short_window", parameters.get("short", 20))),
            long_window=int(parameters.get("long_window", parameters.get("long", 60))),
        )
    if normalized == "breakout":
        return breakout_signals(candles, lookback=int(parameters.get("lookback", 20)))
    if normalized == "mean_reversion":
        return mean_reversion_signals(
            candles,
            window=int(parameters.get("window", 20)),
            threshold_pct=float(parameters.get("threshold_pct", 0.03)),
        )
    if normalized == "volatility_filter":
        return volatility_filter_signals(
            candles,
            short_window=int(parameters.get("short_window", parameters.get("short", 20))),
            long_window=int(parameters.get("long_window", parameters.get("long", 60))),
            min_range_pct=float(parameters.get("min_range_pct", 0.01)),
        )
    raise ValueError(f"unknown strategy: {strategy_name}")


def breakout_signals(candles: list[Candle], *, lookback: int) -> list[Signal]:
    if lookback < 2:
        raise ValueError("lookback must be at least 2")
    signals: list[Signal] = []
    in_position = False
    for index in range(lookback, len(candles)):
        previous = candles[index - lookback : index]
        candle = candles[index]
        resistance = max(item.high for item in previous)
        support = min(item.low for item in previous)
        if not in_position and candle.close > resistance:
            signals.append(Signal(candle.symbol, candle.opened_at, SignalAction.BUY, f"breakout above {lookback} candle resistance"))
            in_position = True
        elif in_position and candle.close < support:
            signals.append(Signal(candle.symbol, candle.opened_at, SignalAction.SELL, f"breakout failed below {lookback} candle support"))
            in_position = False
    return signals


def mean_reversion_signals(candles: list[Candle], *, window: int, threshold_pct: float) -> list[Signal]:
    if window < 2:
        raise ValueError("window must be at least 2")
    if threshold_pct <= 0:
        raise ValueError("threshold_pct must be positive")
    signals: list[Signal] = []
    in_position = False
    closes = [candle.close for candle in candles]
    for index in range(window - 1, len(candles)):
        average = simple_average(closes[index - window + 1 : index + 1])
        candle = candles[index]
        lower_band = average * (1 - threshold_pct)
        upper_band = average * (1 + threshold_pct)
        if not in_position and candle.close < lower_band:
            signals.append(Signal(candle.symbol, candle.opened_at, SignalAction.BUY, f"mean reversion below {window} candle average"))
            in_position = True
        elif in_position and candle.close > upper_band:
            signals.append(Signal(candle.symbol, candle.opened_at, SignalAction.SELL, f"mean reversion exit above {window} candle average"))
            in_position = False
    return signals


def volatility_filter_signals(
    candles: list[Candle],
    *,
    short_window: int,
    long_window: int,
    min_range_pct: float,
) -> list[Signal]:
    base_signals = moving_average_crossover_signals(candles, short_window=short_window, long_window=long_window)
    candles_by_time = {candle.opened_at: candle for candle in candles}
    filtered: list[Signal] = []
    for signal in base_signals:
        candle = candles_by_time[signal.timestamp]
        range_pct = (candle.high - candle.low) / candle.close if candle.close else 0
        if range_pct >= min_range_pct:
            filtered.append(
                Signal(
                    signal.symbol,
                    signal.timestamp,
                    signal.action,
                    f"volatility filter accepted {signal.reason}",
                )
            )
    return filtered
