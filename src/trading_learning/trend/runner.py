from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from trading_learning.metrics import (
    cagr,
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    volatility,
    win_rate,
)
from trading_learning.trend.backtest import run_donchian_backtest

DEFAULT_THRESHOLDS = {
    "sharpe_ratio": 0.3,
    "max_drawdown": -0.6,
    "trade_count": 10,
    "profit_factor": 1.2,
}


def run_h300_ablation(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    parameter_set: list[int] | None = None,
    data_root: Path = Path("data/local"),
) -> dict[str, Any]:
    """Run the H-300 Donchian parameter family and BTC buy-and-hold benchmarks."""

    parameters = parameter_set if parameter_set is not None else [20, 40, 60]
    prices = _load_prices(symbol=symbol, interval=interval, data_root=data_root)
    strategies: dict[int, dict[str, Any]] = {}
    for n in parameters:
        backtest = run_donchian_backtest(prices, n=n)
        metrics = _metrics_from_series(backtest["returns"], backtest["equity_curve"], backtest["trades"]["pnl"])
        pass_fail = _pass_fail(metrics)
        strategies[n] = {
            "metrics": metrics,
            "pass_fail": pass_fail,
            "trade_count": len(backtest["trades"]),
        }

    benchmarks = _buy_and_hold_benchmarks(prices)
    opened_at = pd.to_datetime(prices["opened_at"])
    return {
        "meta": {
            "symbol": symbol.upper(),
            "interval": interval,
            "start": opened_at.iloc[0].date().isoformat(),
            "end": opened_at.iloc[-1].date().isoformat(),
            "rows": int(len(prices)),
            "parameter_set": list(parameters),
        },
        "thresholds": dict(DEFAULT_THRESHOLDS),
        "strategies": strategies,
        "benchmarks": benchmarks,
        "overall_pass": all(result["pass_fail"]["overall"] for result in strategies.values()),
    }


def generate_h300_report(ablation_result: dict[str, Any], output_path: Path) -> None:
    """Write a Markdown report for exports/ablation-trend-h300-{date}.md."""

    meta = ablation_result["meta"]
    lines = [
        "# H-300 Donchian 趋势策略 Ablation 报告",
        "",
        "## 卡片元信息",
        f"- Symbol：{meta['symbol']}",
        f"- Interval：{meta['interval']}",
        f"- 时间窗口：{meta['start']} ~ {meta['end']}",
        f"- 数据条数：{meta['rows']}",
        f"- 参数族：{', '.join('N=' + str(n) for n in meta['parameter_set'])}",
        "",
        "## Donchian 参数族 Metrics",
        _metrics_table(ablation_result["strategies"]),
        "",
        "## Buy-and-Hold Benchmark",
        _benchmark_table(ablation_result["benchmarks"]),
        "",
        "## Pass/Fail 判定",
        _pass_fail_table(ablation_result["strategies"]),
        "",
        f"总体结论：{'Pass' if ablation_result['overall_pass'] else 'Fail'}",
        "",
        "阈值未调整，判定按 H-300 卡片机械执行。",
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _load_prices(symbol: str, interval: str, data_root: Path) -> pd.DataFrame:
    normalized_symbol = symbol.upper()
    csv_path = data_root / "market_data" / normalized_symbol / interval / f"{normalized_symbol}-{interval}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))
    prices = pd.read_csv(csv_path)
    required = {"opened_at", "open", "high", "low", "close", "volume"}
    missing = required.difference(prices.columns)
    if missing:
        raise ValueError(f"price csv missing required columns: {', '.join(sorted(missing))}")
    prices["opened_at"] = pd.to_datetime(prices["opened_at"], utc=True)
    return prices.sort_values("opened_at").reset_index(drop=True)


def _metrics_from_series(returns: pd.Series, equity_curve: pd.Series, trade_pnls: pd.Series) -> dict[str, float | int]:
    drawdown, _ = max_drawdown(equity_curve)
    annual_growth = cagr(equity_curve)
    calmar = float("nan")
    if math.isfinite(annual_growth) and math.isfinite(drawdown) and drawdown != 0.0:
        calmar = annual_growth / abs(drawdown)
    return {
        "sharpe_ratio": sharpe_ratio(returns),
        "sortino_ratio": sortino_ratio(returns),
        "calmar_ratio": calmar,
        "max_drawdown": drawdown,
        "cagr": annual_growth,
        "volatility": volatility(returns),
        "win_rate": win_rate(trade_pnls),
        "profit_factor": profit_factor(trade_pnls),
        "trade_count": int(len(trade_pnls)),
    }


def _buy_and_hold_benchmarks(prices: pd.DataFrame) -> dict[str, dict[str, Any]]:
    close = prices["close"].astype(float).reset_index(drop=True)
    initial_close = float(close.iloc[0])

    simple_returns = close.diff().fillna(0.0) / initial_close
    simple_equity = 1.0 + simple_returns.cumsum()
    simple_trade_pnls = pd.Series([(float(close.iloc[-1]) - initial_close) / initial_close])

    compounded_returns = close.pct_change().fillna(0.0)
    compounded_equity = (1.0 + compounded_returns).cumprod()
    compounded_trade_pnls = pd.Series([float(compounded_equity.iloc[-1]) - 1.0])

    return {
        "simple": {"metrics": _metrics_from_series(simple_returns, simple_equity, simple_trade_pnls)},
        "compounded": {"metrics": _metrics_from_series(compounded_returns, compounded_equity, compounded_trade_pnls)},
    }


def _pass_fail(metrics: dict[str, float | int]) -> dict[str, bool]:
    checks = {
        "sharpe_ratio": float(metrics["sharpe_ratio"]) >= DEFAULT_THRESHOLDS["sharpe_ratio"],
        "max_drawdown": float(metrics["max_drawdown"]) >= DEFAULT_THRESHOLDS["max_drawdown"],
        "trade_count": int(metrics["trade_count"]) >= DEFAULT_THRESHOLDS["trade_count"],
        "profit_factor": float(metrics["profit_factor"]) >= DEFAULT_THRESHOLDS["profit_factor"],
    }
    checks["overall"] = all(checks.values())
    return checks


def _metrics_table(strategies: dict[int, dict[str, Any]]) -> str:
    rows = [
        "| 参数 | Sharpe | Sortino | Calmar | Max DD | CAGR | Volatility | Win Rate | Profit Factor | Trades |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for n, result in strategies.items():
        metrics = result["metrics"]
        rows.append(
            "| "
            + " | ".join(
                [
                    f"N={n}",
                    _number(metrics["sharpe_ratio"]),
                    _number(metrics["sortino_ratio"]),
                    _number(metrics["calmar_ratio"]),
                    _percent(metrics["max_drawdown"]),
                    _percent(metrics["cagr"]),
                    _percent(metrics["volatility"]),
                    _percent(metrics["win_rate"]),
                    _number(metrics["profit_factor"]),
                    str(metrics["trade_count"]),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _benchmark_table(benchmarks: dict[str, dict[str, Any]]) -> str:
    rows = [
        "| Benchmark | Sharpe | Sortino | Calmar | Max DD | CAGR | Volatility | Win Rate | Profit Factor | Trades |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in benchmarks.items():
        metrics = result["metrics"]
        rows.append(
            "| "
            + " | ".join(
                [
                    name,
                    _number(metrics["sharpe_ratio"]),
                    _number(metrics["sortino_ratio"]),
                    _number(metrics["calmar_ratio"]),
                    _percent(metrics["max_drawdown"]),
                    _percent(metrics["cagr"]),
                    _percent(metrics["volatility"]),
                    _percent(metrics["win_rate"]),
                    _number(metrics["profit_factor"]),
                    str(metrics["trade_count"]),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _pass_fail_table(strategies: dict[int, dict[str, Any]]) -> str:
    rows = [
        "| 参数 | Sharpe ≥ 0.3 | Max DD ≤ 60% | Trades ≥ 10 | PF ≥ 1.2 | Overall |",
        "|---|---|---|---|---|---|",
    ]
    for n, result in strategies.items():
        checks = result["pass_fail"]
        rows.append(
            "| "
            + " | ".join(
                [
                    f"N={n}",
                    _pass(checks["sharpe_ratio"]),
                    _pass(checks["max_drawdown"]),
                    _pass(checks["trade_count"]),
                    _pass(checks["profit_factor"]),
                    _pass(checks["overall"]),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _number(value: object) -> str:
    number = float(value)
    if math.isinf(number):
        return "inf"
    if math.isnan(number):
        return "nan"
    return f"{number:.6f}"


def _percent(value: object) -> str:
    number = float(value)
    if math.isnan(number):
        return "nan"
    return f"{number * 100.0:.2f}%"


def _pass(value: bool) -> str:
    return "Pass" if value else "Fail"
