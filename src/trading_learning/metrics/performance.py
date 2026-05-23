from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

import numpy as np
import pandas as pd

ArrayLike: TypeAlias = Sequence[float] | np.ndarray | pd.Series


def sharpe_ratio(returns: ArrayLike, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """Return annualized Sharpe ratio: SR = mean(R - Rf/P) / std(R) * sqrt(P)."""

    values = _clean_array(returns)
    if values.size < 2:
        return float("nan")
    excess = values - (risk_free_rate / periods_per_year)
    std = np.std(values, ddof=1)
    if std == 0.0 or not np.isfinite(std):
        return float("nan")
    return float(np.mean(excess) / std * np.sqrt(periods_per_year))


def sortino_ratio(returns: ArrayLike, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """Return annualized Sortino ratio: Sortino = mean(E) / sqrt(mean(min(E,0)^2)) * sqrt(P)."""

    values = _clean_array(returns)
    if values.size == 0:
        return float("nan")
    excess = values - (risk_free_rate / periods_per_year)
    downside = np.minimum(excess, 0.0)
    downside_deviation = np.sqrt(np.mean(np.square(downside)))
    if downside_deviation == 0.0 or not np.isfinite(downside_deviation):
        return float("nan")
    return float(np.mean(excess) / downside_deviation * np.sqrt(periods_per_year))


def calmar_ratio(returns: ArrayLike, periods_per_year: int = 252) -> float:
    """Return Calmar ratio from a returns series: Calmar = CAGR(equity(R)) / abs(max drawdown)."""

    curve = equity_curve(returns)
    annual_growth = cagr(curve, periods_per_year=periods_per_year)
    drawdown, _ = max_drawdown(curve)
    if not np.isfinite(annual_growth) or drawdown == 0.0 or not np.isfinite(drawdown):
        return float("nan")
    return float(annual_growth / abs(drawdown))


def max_drawdown(equity_curve: ArrayLike) -> tuple[float, int]:
    """Return worst drawdown and duration: DD_t = equity_t / max(equity_0..t) - 1."""

    values = _clean_array(equity_curve)
    if values.size == 0:
        return float("nan"), 0
    if values.size == 1:
        return 0.0, 0

    peak = values[0]
    max_dd = 0.0
    current_duration = 0
    max_duration = 0
    for value in values:
        if value >= peak:
            peak = value
            current_duration = 0
            continue
        if peak <= 0.0:
            continue
        current_duration += 1
        max_duration = max(max_duration, current_duration)
        drawdown = value / peak - 1.0
        max_dd = min(max_dd, drawdown)
    return float(max_dd), max_duration


def cagr(equity_curve: ArrayLike, periods_per_year: int = 252) -> float:
    """Return compound annual growth rate: CAGR = (final / initial)^(P / (N - 1)) - 1."""

    values = _clean_array(equity_curve)
    if values.size < 2:
        return float("nan")
    initial = values[0]
    final = values[-1]
    if initial <= 0.0 or final <= 0.0:
        return float("nan")
    elapsed_periods = values.size - 1
    return float((final / initial) ** (periods_per_year / elapsed_periods) - 1.0)


def volatility(returns: ArrayLike, periods_per_year: int = 252) -> float:
    """Return annualized volatility: Vol = std(R) * sqrt(P)."""

    values = _clean_array(returns)
    if values.size < 2:
        return float("nan")
    return float(np.std(values, ddof=1) * np.sqrt(periods_per_year))


def win_rate(trade_pnls: ArrayLike) -> float:
    """Return win rate: win_rate = count(PnL > 0) / count(PnL)."""

    values = _clean_array(trade_pnls)
    if values.size == 0:
        return 0.0
    return float(np.sum(values > 0.0) / values.size)


def profit_factor(trade_pnls: ArrayLike) -> float:
    """Return profit factor: PF = gross_profit / abs(gross_loss)."""

    values = _clean_array(trade_pnls)
    if values.size == 0:
        return 0.0
    gross_profit = float(np.sum(values[values > 0.0]))
    gross_loss = float(np.sum(values[values < 0.0]))
    if gross_profit == 0.0:
        return 0.0
    if gross_loss == 0.0:
        return float("inf")
    return gross_profit / abs(gross_loss)


def equity_curve(returns: ArrayLike, initial_capital: float = 1.0) -> pd.Series:
    """Return compounded equity: equity_t = initial_capital * product(1 + R_i)."""

    values = _clean_array(returns)
    if values.size == 0:
        return pd.Series([float(initial_capital)])
    compounded = np.concatenate(([1.0], np.cumprod(1.0 + values)))
    return pd.Series(float(initial_capital) * compounded)


def _clean_array(values: ArrayLike) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim == 0:
        array = array.reshape(1)
    return array[np.isfinite(array)]
