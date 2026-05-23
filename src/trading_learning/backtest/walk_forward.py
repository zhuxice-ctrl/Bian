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


@dataclass(frozen=True)
class StrategyRunResult:
    returns: np.ndarray
    trade_count: int
    metadata: dict[str, Any]


@dataclass
class WalkForwardResult:
    windows: list[dict[str, Any]]
    aggregate_metrics: dict[str, Any]
    consistency_score: float
    oos_returns: np.ndarray


def run_walk_forward(
    strategy_factory: Callable[[dict[str, Any]], Callable[[Any], Any]],
    df: pd.DataFrame | dict[str, pd.DataFrame],
    config: WalkForwardConfig,
    param_grid: dict[str, list[Any]] | None = None,
    *,
    primary_timeframe: str = "1h",
) -> WalkForwardResult:
    frames, is_single_frame = _normalize_input(df, primary_timeframe)
    frame = frames[primary_timeframe]
    windows: list[dict[str, Any]] = []
    oos_returns: list[float] = []
    oos_trade_count = 0
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
        train = _slice_input(frames, train_start, train_end, is_single_frame)
        test = _slice_input(frames, test_start, test_end, is_single_frame)
        if not _is_empty(train, primary_timeframe) and not _is_empty(test, primary_timeframe):
            params = _select_params(strategy_factory, train, param_grid)
            train_result = _run_strategy(strategy_factory, params, train)
            test_result = _run_strategy(strategy_factory, params, test)
            oos_returns.extend(test_result.returns.tolist())
            oos_trade_count += test_result.trade_count
            windows.append(
                {
                    "train_start": train_start,
                    "train_end": train_end,
                    "test_start": test_start,
                    "test_end": test_end,
                    "selected_params": params,
                    "train_metrics": _metrics(train_result.returns, train_result.trade_count),
                    "test_metrics": _metrics(test_result.returns, test_result.trade_count),
                    "oos_returns": test_result.returns,
                    "metadata": test_result.metadata,
                }
            )
        start = start + step_delta

    oos_array = np.asarray(oos_returns, dtype="float64")
    aggregate = _metrics(oos_array, oos_trade_count)
    aggregate["oos_sharpe"] = aggregate["sharpe"]
    aggregate["oos_trade_count"] = aggregate["trade_count"]
    aggregate["oos_bar_count"] = int(len(oos_array))
    consistency = 0.0
    if windows:
        consistency = sum(1 for window in windows if window["test_metrics"]["sharpe"] > 0) / len(windows)
    return WalkForwardResult(windows=windows, aggregate_metrics=aggregate, consistency_score=consistency, oos_returns=oos_array)


def _normalize_input(df: pd.DataFrame | dict[str, pd.DataFrame], primary_timeframe: str) -> tuple[dict[str, pd.DataFrame], bool]:
    if isinstance(df, dict):
        if primary_timeframe not in df:
            raise ValueError(f"frames must include primary timeframe {primary_timeframe}")
        return {key: _normalize_frame(value) for key, value in df.items()}, False
    return {primary_timeframe: _normalize_frame(df)}, True


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "opened_at" not in df.columns:
        raise ValueError("df must include opened_at")
    frame = df.copy()
    frame["opened_at"] = pd.to_datetime(frame["opened_at"], utc=True)
    return frame.sort_values("opened_at").reset_index(drop=True)


def _slice_input(
    frames: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    is_single_frame: bool,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    sliced = {
        key: value[(value["opened_at"] >= start) & (value["opened_at"] <= end)].copy()
        for key, value in frames.items()
    }
    if is_single_frame:
        return next(iter(sliced.values()))
    return sliced


def _is_empty(value: pd.DataFrame | dict[str, pd.DataFrame], primary_timeframe: str) -> bool:
    if isinstance(value, dict):
        return value[primary_timeframe].empty
    return value.empty


def _select_params(strategy_factory, train: Any, param_grid: dict[str, list[Any]] | None) -> dict[str, Any]:
    candidates = _param_candidates(param_grid)
    best_params = candidates[0]
    best_sharpe = float("-inf")
    for params in candidates:
        result = _run_strategy(strategy_factory, params, train)
        sharpe = _metrics(result.returns, result.trade_count)["sharpe"]
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


def _run_strategy(strategy_factory, params: dict[str, Any], frame: Any) -> StrategyRunResult:
    runner = strategy_factory(params)
    run_input = {key: value.copy() for key, value in frame.items()} if isinstance(frame, dict) else frame.copy()
    result = runner(run_input)
    if isinstance(result, StrategyRunResult):
        return result
    if isinstance(result, pd.Series):
        values = result.to_numpy(dtype="float64")
    else:
        values = np.asarray(result, dtype="float64")
    values = values[np.isfinite(values)]
    return StrategyRunResult(
        returns=values,
        trade_count=int(np.count_nonzero(values)),
        metadata={"legacy_return_series": True},
    )


def _metrics(returns: np.ndarray, trade_count: int) -> dict[str, Any]:
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
        "trade_count": int(trade_count),
        "bar_count": int(len(returns)),
    }
