from __future__ import annotations

from typing import Any

import pandas as pd

from trading_learning.trend.donchian import donchian_channels, donchian_signals


def run_donchian_backtest(
    prices: pd.DataFrame,
    n: int,
    exit_n: int | None = None,
    initial_capital: float = 1.0,
) -> dict[str, Any]:
    """
    Run a single-symbol Donchian baseline with fixed-notional, non-compounded PnL.

    The position recorded at t is the end-of-bar state after any close[t] signal,
    while returns[t] are earned from close[t-1] to close[t] by the prior state.
    """

    if prices.empty:
        raise ValueError("prices must contain at least one row")
    if initial_capital <= 0.0:
        raise ValueError("initial_capital must be positive")

    exit_window = exit_n if exit_n is not None else n // 2
    if exit_window <= 0:
        raise ValueError("exit_n must be positive")

    frame = prices.reset_index(drop=True).copy()
    entry_signals = donchian_signals(frame, n)
    exit_channels = donchian_channels(frame, exit_window)

    returns: list[float] = []
    positions: list[int] = []
    trades: list[dict[str, Any]] = []

    position = 0
    entry_price: float | None = None
    entry_index: int | None = None

    for i, row in frame.iterrows():
        close = float(row["close"])
        if i == 0 or position == 0 or entry_price is None:
            period_return = 0.0
        else:
            previous_close = float(frame.loc[i - 1, "close"])
            period_return = position * (close - previous_close) / entry_price
        returns.append(period_return)

        if position == 1 and close < float(exit_channels.loc[i, "lower"]):
            trades.append(_trade_record(frame, "long", entry_index, i, entry_price, close, "reverse_to_short"))
            position = -1
            entry_price = close
            entry_index = i
        elif position == -1 and close > float(exit_channels.loc[i, "upper"]):
            trades.append(_trade_record(frame, "short", entry_index, i, entry_price, close, "reverse_to_long"))
            position = 1
            entry_price = close
            entry_index = i
        elif position == 0:
            signal = int(entry_signals.loc[i])
            if signal == 1:
                position = 1
                entry_price = close
                entry_index = i
            elif signal == -1:
                position = -1
                entry_price = close
                entry_index = i

        positions.append(position)

    if position != 0 and entry_price is not None and entry_index is not None:
        final_index = len(frame) - 1
        final_close = float(frame.loc[final_index, "close"])
        trades.append(
            _trade_record(
                frame,
                "long" if position == 1 else "short",
                entry_index,
                final_index,
                entry_price,
                final_close,
                "mark_to_market",
            )
        )

    returns_series = pd.Series(returns, index=prices.index, name="returns")
    equity_series = (float(initial_capital) + returns_series.cumsum() * float(initial_capital)).rename("equity")
    positions_series = pd.Series(positions, index=prices.index, name="position")

    return {
        "equity_curve": equity_series,
        "returns": returns_series,
        "positions": positions_series,
        "trades": pd.DataFrame(
            trades,
            columns=["side", "entry_index", "exit_index", "entry_time", "exit_time", "entry_price", "exit_price", "pnl", "exit_reason"],
        ),
    }


def _trade_record(
    prices: pd.DataFrame,
    side: str,
    entry_index: int | None,
    exit_index: int,
    entry_price: float | None,
    exit_price: float,
    exit_reason: str,
) -> dict[str, Any]:
    if entry_index is None or entry_price is None:
        raise ValueError("cannot close a trade before entry")
    direction = 1 if side == "long" else -1
    return {
        "side": side,
        "entry_index": entry_index,
        "exit_index": exit_index,
        "entry_time": _time_value(prices, entry_index),
        "exit_time": _time_value(prices, exit_index),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": direction * (exit_price - entry_price) / entry_price,
        "exit_reason": exit_reason,
    }


def _time_value(prices: pd.DataFrame, row_index: int) -> Any:
    if "opened_at" in prices.columns:
        return prices.loc[row_index, "opened_at"]
    return prices.index[row_index]
