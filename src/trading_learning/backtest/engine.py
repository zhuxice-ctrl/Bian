from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from trading_learning.metrics.performance import (
    cagr,
    calmar_ratio,
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    volatility,
    win_rate,
)
from trading_learning.models import BacktestResult as SpotBacktestResult
from trading_learning.models import Side, Signal, SignalAction, Trade


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.Series
    daily_returns: pd.Series
    gross_returns: pd.Series
    positions: pd.Series
    costs: pd.Series
    turnover: pd.Series
    metrics: dict


def compute_fdm(
    forecasts: pd.DataFrame,
    weights: np.ndarray | None = None,
) -> float:
    """Compute the Forecast Diversification Multiplier from forecast correlations."""
    clean_forecasts = forecasts.astype(float).dropna(how="any")
    if clean_forecasts.empty:
        raise ValueError("forecasts must contain at least one complete row")

    corr = clean_forecasts.corr()
    n = len(corr)
    if n == 0:
        raise ValueError("forecasts must contain at least one column")
    if weights is None:
        weights = np.ones(n) / n
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (n,):
        raise ValueError("weights must match the number of forecast columns")

    portfolio_var = float(weights @ corr.values @ weights)
    if portfolio_var <= 0.0 or not np.isfinite(portfolio_var):
        return 1.0
    return float(1.0 / np.sqrt(portfolio_var))


def combine_forecasts(
    forecasts: pd.DataFrame,
    weights: np.ndarray | None = None,
    apply_fdm: bool = True,
    forecast_cap: float = 2.0,
) -> pd.Series:
    """Combine forecast columns and optionally apply FDM before clipping."""
    if forecast_cap <= 0.0:
        raise ValueError("forecast_cap must be positive")

    clean_forecasts = forecasts.astype(float).dropna(how="any")
    if clean_forecasts.empty:
        raise ValueError("forecasts must contain at least one complete row")

    n = clean_forecasts.shape[1]
    if weights is None:
        weights = np.ones(n) / n
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (n,):
        raise ValueError("weights must match the number of forecast columns")

    combined = clean_forecasts @ weights
    if apply_fdm:
        combined = combined * compute_fdm(clean_forecasts, weights)
    return combined.clip(-forecast_cap, forecast_cap).rename("combined_forecast")


def backtest_forecast(
    forecast: pd.Series,
    price: pd.Series,
    target_vol: float = 0.20,
    vol_lookback: int = 60,
    cost_per_round_trip: float = 0.002,
    capital: float = 100_000,
    max_leverage: float = 2.0,
    periods_per_year: int = 365,
) -> BacktestResult:
    if target_vol < 0.0:
        raise ValueError("target_vol must be non-negative")
    if vol_lookback <= 1:
        raise ValueError("vol_lookback must be greater than 1")
    if cost_per_round_trip < 0.0:
        raise ValueError("cost_per_round_trip must be non-negative")
    if capital <= 0.0:
        raise ValueError("capital must be positive")
    if max_leverage <= 0.0:
        raise ValueError("max_leverage must be positive")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")

    aligned = pd.concat(
        [forecast.astype(float).rename("forecast"), price.astype(float).rename("price")],
        axis=1,
        join="inner",
    ).dropna(subset=["price"])
    if aligned.empty:
        raise ValueError("forecast and price must have overlapping price rows")

    daily_price_returns = aligned["price"].pct_change().fillna(0.0)
    instrument_vol = daily_price_returns.ewm(span=vol_lookback, adjust=False).std() * np.sqrt(periods_per_year)
    raw_position = aligned["forecast"].fillna(0.0) * (target_vol / instrument_vol.replace(0.0, np.nan))
    positions = raw_position.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-max_leverage, max_leverage)
    gross_returns = (positions.shift(1).fillna(0.0) * daily_price_returns).fillna(0.0)
    turnover = positions.diff().abs().fillna(positions.abs())
    cost_returns = turnover * cost_per_round_trip
    costs = cost_returns * capital
    daily_returns = (gross_returns - cost_returns).fillna(0.0)
    equity_curve = capital * (1.0 + daily_returns).cumprod()
    if len(equity_curve) > 0:
        equity_curve.iloc[0] = capital

    metrics = _metrics(
        net_returns=daily_returns,
        gross_returns=gross_returns,
        equity_curve=equity_curve,
        turnover=turnover,
        costs=costs,
        capital=capital,
        periods_per_year=periods_per_year,
    )
    return BacktestResult(
        equity_curve=equity_curve.rename("equity"),
        daily_returns=daily_returns.rename("daily_returns"),
        gross_returns=gross_returns.rename("gross_returns"),
        positions=positions.rename("position_fraction"),
        costs=costs.rename("costs"),
        turnover=turnover.rename("turnover"),
        metrics=metrics,
    )


def buy_and_hold_result(
    price: pd.Series,
    capital: float = 100_000,
    periods_per_year: int = 365,
) -> BacktestResult:
    if capital <= 0.0:
        raise ValueError("capital must be positive")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    clean_price = price.astype(float).dropna()
    if clean_price.empty:
        raise ValueError("price must not be empty")

    daily_returns = clean_price.pct_change().fillna(0.0)
    equity_curve = capital * (clean_price / clean_price.iloc[0])
    positions = pd.Series(1.0, index=clean_price.index, name="position_fraction")
    costs = pd.Series(0.0, index=clean_price.index, name="costs")
    turnover = pd.Series(0.0, index=clean_price.index, name="turnover")
    gross_returns = daily_returns.copy()
    metrics = _metrics(
        net_returns=daily_returns,
        gross_returns=gross_returns,
        equity_curve=equity_curve,
        turnover=turnover,
        costs=costs,
        capital=capital,
        periods_per_year=periods_per_year,
    )
    return BacktestResult(
        equity_curve=equity_curve.rename("equity"),
        daily_returns=daily_returns.rename("daily_returns"),
        gross_returns=gross_returns.rename("gross_returns"),
        positions=positions,
        costs=costs,
        turnover=turnover,
        metrics=metrics,
    )


def run_spot_backtest(
    symbol: str,
    signals: list[Signal],
    prices_by_timestamp: dict,
    starting_cash: float,
    quote_amount_per_buy: float,
    fee_rate: float,
    daily_trade_limit: int,
) -> SpotBacktestResult:
    cash = starting_cash
    position_quantity = 0.0
    trades: list[Trade] = []
    daily_counts: dict[str, int] = defaultdict(int)

    for signal in signals:
        day_key = signal.timestamp.date().isoformat()
        if daily_counts[day_key] >= daily_trade_limit:
            continue

        if signal.action == SignalAction.BUY and cash >= quote_amount_per_buy:
            price = float(prices_by_timestamp[signal.timestamp])
            fee = quote_amount_per_buy * fee_rate
            quantity = (quote_amount_per_buy - fee) / price
            cash -= quote_amount_per_buy
            position_quantity += quantity
            daily_counts[day_key] += 1
            trades.append(
                Trade(
                    external_id=f"backtest-{symbol}-{signal.timestamp.isoformat()}-buy",
                    symbol=symbol,
                    side=Side.BUY,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    timestamp=signal.timestamp,
                    reason=signal.reason,
                )
            )
        elif signal.action == SignalAction.SELL and position_quantity > 0:
            price = float(prices_by_timestamp[signal.timestamp])
            gross = position_quantity * price
            fee = gross * fee_rate
            cash += gross - fee
            quantity = position_quantity
            position_quantity = 0.0
            daily_counts[day_key] += 1
            trades.append(
                Trade(
                    external_id=f"backtest-{symbol}-{signal.timestamp.isoformat()}-sell",
                    symbol=symbol,
                    side=Side.SELL,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    timestamp=signal.timestamp,
                    reason=signal.reason,
                )
            )

    return SpotBacktestResult(
        symbol=symbol,
        starting_cash=starting_cash,
        ending_cash=cash,
        position_quantity=position_quantity,
        trade_count=len(trades),
        trades=tuple(trades),
    )


def _metrics(
    *,
    net_returns: pd.Series,
    gross_returns: pd.Series,
    equity_curve: pd.Series,
    turnover: pd.Series,
    costs: pd.Series,
    capital: float,
    periods_per_year: int,
) -> dict:
    drawdown, _ = max_drawdown(equity_curve)
    net_sharpe = _finite_or_zero(sharpe_ratio(net_returns, periods_per_year=periods_per_year))
    gross_sharpe = _finite_or_zero(sharpe_ratio(gross_returns, periods_per_year=periods_per_year))
    years = len(net_returns) / periods_per_year if len(net_returns) else float("nan")
    return {
        "sharpe": net_sharpe,
        "gross_sharpe": gross_sharpe,
        "sortino": _finite_or_zero(sortino_ratio(net_returns, periods_per_year=periods_per_year)),
        "calmar": _finite_or_zero(calmar_ratio(net_returns, periods_per_year=periods_per_year)),
        "cagr": _finite_or_zero(cagr(equity_curve, periods_per_year=periods_per_year)),
        "max_drawdown": _finite_or_zero(drawdown),
        "annual_volatility": _finite_or_zero(volatility(net_returns, periods_per_year=periods_per_year)),
        "total_return": float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0) if len(equity_curve) > 1 else 0.0,
        "win_rate": win_rate(net_returns[net_returns != 0.0]),
        "profit_factor": profit_factor(net_returns[net_returns != 0.0]),
        "annual_turnover": float(turnover.sum() / years) if years and np.isfinite(years) and years > 0.0 else 0.0,
        "total_cost_drag": float(costs.sum() / capital),
        "cost_sharpe_drag": gross_sharpe - net_sharpe,
    }


def _finite_or_zero(value: float) -> float:
    return float(value) if np.isfinite(value) else 0.0
