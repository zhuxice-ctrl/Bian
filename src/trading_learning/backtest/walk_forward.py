from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from itertools import product
from typing import Any, Callable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WalkForwardConfig:
    train_window_days: int = 365
    test_window_days: int = 90
    step_days: int = 90
    purge_days: int = 5


@dataclass
class WalkForwardResult:
    windows: list[dict[str, Any]]
    aggregate_metrics: dict[str, Any]
    consistency_score: float
    oos_returns: np.ndarray


def run_walk_forward(
    strategy_factory: Callable[[dict[str, Any]], Callable[[pd.DataFrame], pd.Series]],
    df: pd.DataFrame,
    config: WalkForwardConfig,
    param_grid: dict[str, list[Any]] | None = None,
) -> WalkForwardResult:
    frame = _normalize_frame(df)
    windows: list[dict[str, Any]] = []
    oos_returns: list[float] = []
    start = frame["opened_at"].min()
    final_time = frame["opened_at"].max()
    train_delta = timedelta(days=config.train_window_days - 1)
    test_delta = timedelta(days=config.test_window_days - 1)
    step_delta = timedelta(days=config.step_days)
    purge_delta = timedelta(days=config.purge_days)

    while True:
        train_start = start
        train_end = train_start + train_delta
        test_start = train_end + purge_delta + timedelta(days=1)
        test_end = test_start + test_delta
        if test_end > final_time:
            break
        train = frame[(frame["opened_at"] >= train_start) & (frame["opened_at"] <= train_end)].copy()
        test = frame[(frame["opened_at"] >= test_start) & (frame["opened_at"] <= test_end)].copy()
        if not train.empty and not test.empty:
            params = _select_params(strategy_factory, train, param_grid)
            train_returns = _run_strategy(strategy_factory, params, train)
            test_returns = _run_strategy(strategy_factory, params, test)
            oos_returns.extend(test_returns.tolist())
            windows.append(
                {
                    "train_start": train_start,
                    "train_end": train_end,
                    "test_start": test_start,
                    "test_end": test_end,
                    "selected_params": params,
                    "train_metrics": _metrics(train_returns),
                    "test_metrics": _metrics(test_returns),
                    "oos_returns": test_returns,
                }
            )
        start = start + step_delta

    oos_array = np.asarray(oos_returns, dtype="float64")
    aggregate = _metrics(oos_array)
    aggregate["oos_sharpe"] = aggregate["sharpe"]
    aggregate["oos_trade_count"] = aggregate["trade_count"]
    consistency = 0.0
    if windows:
        consistency = sum(1 for window in windows if window["test_metrics"]["sharpe"] > 0) / len(windows)
    return WalkForwardResult(windows=windows, aggregate_metrics=aggregate, consistency_score=consistency, oos_returns=oos_array)


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "opened_at" not in df.columns:
        raise ValueError("df must include opened_at")
    frame = df.copy()
    frame["opened_at"] = pd.to_datetime(frame["opened_at"], utc=True)
    return frame.sort_values("opened_at").reset_index(drop=True)


def _select_params(strategy_factory, train: pd.DataFrame, param_grid: dict[str, list[Any]] | None) -> dict[str, Any]:
    candidates = _param_candidates(param_grid)
    best_params = candidates[0]
    best_sharpe = float("-inf")
    for params in candidates:
        returns = _run_strategy(strategy_factory, params, train)
        sharpe = _metrics(returns)["sharpe"]
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_params = params
    return best_params


def _param_candidates(param_grid: dict[str, list[Any]] | None) -> list[dict[str, Any]]:
    if not param_grid:
        return [{}]
    keys = list(param_grid)
    values = [param_grid[key] for key in keys]
    return [dict(zip(keys, combo)) for combo in product(*values)]


def _run_strategy(strategy_factory, params: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
    runner = strategy_factory(params)
    returns = runner(frame.copy())
    if isinstance(returns, pd.Series):
        values = returns.to_numpy(dtype="float64")
    else:
        values = np.asarray(returns, dtype="float64")
    return values[np.isfinite(values)]


def _metrics(returns: np.ndarray) -> dict[str, Any]:
    if len(returns) < 2:
        sharpe = 0.0
    else:
        std = float(np.std(returns, ddof=1))
        sharpe = 0.0 if std == 0 else float(np.mean(returns) / std * np.sqrt(252))
    equity = np.cumprod(1 + returns) if len(returns) else np.asarray([1.0])
    peaks = np.maximum.accumulate(equity)
    max_drawdown = float(np.min(equity / peaks - 1)) if len(equity) else 0.0
    return {
        "sharpe": sharpe,
        "total_return": float(equity[-1] - 1) if len(equity) else 0.0,
        "max_drawdown": max_drawdown,
        "trade_count": int(len(returns)),
    }
