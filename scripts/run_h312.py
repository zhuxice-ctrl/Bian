from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from trading_learning.backtest.engine import (  # noqa: E402
    BacktestResult,
    backtest_forecast,
    buy_and_hold_result,
    combine_forecasts,
    compute_fdm,
)
from trading_learning.signals.forecast_library import (  # noqa: E402
    ewmac_forecast,
    mean_reversion_forecast,
    mean_reversion_slow_forecast,
    momentum_forecast,
    vol_regime_forecast,
)

DEFAULT_PRICE_CSV = REPO_ROOT / "data" / "local" / "market_data" / "BTCUSDT" / "1d" / "BTCUSDT-1d.csv"
CAPITAL = 100_000
TARGET_VOL = 0.20
VOL_LOOKBACK = 60
COST_PER_ROUND_TRIP = 0.002
MAX_LEVERAGE = 2.0
PERIODS_PER_YEAR = 365
FORECAST_CAP = 2.0
PYSYSTEMTRADE_EWMAC = {
    "sharpe": 0.617,
    "gross_sharpe": None,
    "cagr": 0.1231,
    "max_drawdown": -0.175,
    "sortino": None,
    "calmar": None,
    "win_rate": None,
    "profit_factor": None,
    "annual_turnover": None,
    "total_cost_drag": None,
    "cost_sharpe_drag": None,
    "total_return": None,
    "annual_volatility": 0.1994,
}
METRIC_ROWS = (
    ("Net Sharpe", "sharpe", "number"),
    ("Gross Sharpe", "gross_sharpe", "number"),
    ("CAGR", "cagr", "percent"),
    ("Max DD", "max_drawdown", "percent"),
    ("Sortino", "sortino", "number"),
    ("Calmar", "calmar", "number"),
    ("Win Rate", "win_rate", "percent"),
    ("Profit Factor", "profit_factor", "number"),
    ("Annual Turnover", "annual_turnover", "number"),
    ("Total Cost Drag", "total_cost_drag", "percent"),
    ("Cost Sharpe Drag", "cost_sharpe_drag", "number"),
    ("Total Return", "total_return", "percent"),
    ("Annual Volatility", "annual_volatility", "percent"),
)


@dataclass(frozen=True)
class SubsetResult:
    label: str
    description: str
    signal_names: tuple[str, ...]
    fdm: float
    result: BacktestResult


SUBSETS = {
    "A": (
        "MOMENTUM + VOL_REGIME",
        ("SIG_MOMENTUM", "SIG_VOL_REGIME"),
    ),
    "B": (
        "TREND_FAST + MOMENTUM + VOL_REGIME",
        ("SIG_TREND_FAST", "SIG_MOMENTUM", "SIG_VOL_REGIME"),
    ),
    "C": (
        "MOMENTUM + VOL_REGIME + MEAN_REV_SLOW",
        ("SIG_MOMENTUM", "SIG_VOL_REGIME", "SIG_MEAN_REV_SLOW"),
    ),
    "D": (
        "TREND_FAST + MOMENTUM + VOL_REGIME + MEAN_REV_SLOW",
        ("SIG_TREND_FAST", "SIG_MOMENTUM", "SIG_VOL_REGIME", "SIG_MEAN_REV_SLOW"),
    ),
    "E": (
        "H-311 original four-signal FDM baseline",
        ("SIG_TREND_FAST", "SIG_MOMENTUM", "SIG_MEAN_REV", "SIG_VOL_REGIME"),
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-312 FDM signal subset optimization.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h312-signal-subset-optimization-{args.report_date}.md"
    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = build_forecasts(price).dropna(how="any")
    aligned_price = price.reindex(forecasts.index)

    subset_results = [
        run_subset(label=label, description=description, signal_names=signal_names, forecasts=forecasts, price=aligned_price)
        for label, (description, signal_names) in SUBSETS.items()
    ]
    benchmark = buy_and_hold_result(aligned_price, capital=CAPITAL, periods_per_year=PERIODS_PER_YEAR)
    mean_rev_fast = run_forecast_backtest(forecasts["SIG_MEAN_REV"], aligned_price)
    mean_rev_slow = run_forecast_backtest(forecasts["SIG_MEAN_REV_SLOW"], aligned_price)

    report = render_report(
        subset_results=subset_results,
        benchmark=benchmark,
        mean_rev_fast=mean_rev_fast,
        mean_rev_slow=mean_rev_slow,
        price_csv=args.price_csv,
        rows=len(forecasts),
        start=forecasts.index.min().date().isoformat(),
        end=forecasts.index.max().date().isoformat(),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    for subset in subset_results:
        print(
            f"{subset.label}: sharpe={subset.result.metrics['sharpe']:.6f} "
            f"turnover={subset.result.metrics['annual_turnover']:.6f} "
            f"vol={subset.result.metrics['annual_volatility']:.6f} "
            f"fdm={subset.fdm:.6f}"
        )


def load_close_price(path: Path) -> pd.Series:
    if not path.exists():
        raise FileNotFoundError(str(path))
    frame = pd.read_csv(path, usecols=["opened_at", "close"])
    frame["opened_at"] = pd.to_datetime(frame["opened_at"], utc=True)
    frame = frame.sort_values("opened_at").drop_duplicates(subset=["opened_at"], keep="last")
    price = frame.set_index("opened_at")["close"].astype(float).rename("BTCUSDT")
    if price.empty:
        raise ValueError("BTCUSDT close series is empty")
    return price


def build_forecasts(price: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SIG_TREND_FAST": ewmac_forecast(
                price, fast_span=8, slow_span=32, normalization="expanding"
            ).rename("SIG_TREND_FAST"),
            "SIG_MOMENTUM": momentum_forecast(price, lookback=60, normalization="expanding").rename("SIG_MOMENTUM"),
            "SIG_VOL_REGIME": vol_regime_forecast(price, vol_window=60, normalization="expanding").rename(
                "SIG_VOL_REGIME"
            ),
            "SIG_MEAN_REV": mean_reversion_forecast(price, window=20, normalization="expanding").rename(
                "SIG_MEAN_REV"
            ),
            "SIG_MEAN_REV_SLOW": mean_reversion_slow_forecast(price, normalization="expanding"),
        }
    )


def run_subset(
    *,
    label: str,
    description: str,
    signal_names: tuple[str, ...],
    forecasts: pd.DataFrame,
    price: pd.Series,
) -> SubsetResult:
    subset_forecasts = forecasts.loc[:, list(signal_names)]
    fdm = compute_fdm(subset_forecasts)
    combined = combine_forecasts(subset_forecasts, apply_fdm=True, forecast_cap=FORECAST_CAP)
    result = run_forecast_backtest(combined, price)
    return SubsetResult(label=label, description=description, signal_names=signal_names, fdm=fdm, result=result)


def run_forecast_backtest(forecast: pd.Series, price: pd.Series) -> BacktestResult:
    return backtest_forecast(
        forecast,
        price,
        target_vol=TARGET_VOL,
        vol_lookback=VOL_LOOKBACK,
        cost_per_round_trip=COST_PER_ROUND_TRIP,
        capital=CAPITAL,
        max_leverage=MAX_LEVERAGE,
        periods_per_year=PERIODS_PER_YEAR,
    )


def render_report(
    *,
    subset_results: list[SubsetResult],
    benchmark: BacktestResult,
    mean_rev_fast: BacktestResult,
    mean_rev_slow: BacktestResult,
    price_csv: Path,
    rows: int,
    start: str,
    end: str,
) -> str:
    subset_map = {subset.label: subset for subset in subset_results}
    baseline = subset_map["E"].result
    sharpe_improved = any(subset.result.metrics["sharpe"] > baseline.metrics["sharpe"] for subset in subset_results if subset.label != "E")
    turnover_improved = any(
        subset.result.metrics["annual_turnover"] < baseline.metrics["annual_turnover"]
        for subset in subset_results
        if subset.label != "E"
    )
    eligible = [
        subset
        for subset in subset_results
        if subset.result.metrics["annual_turnover"] < 15.0
    ]
    best_eligible = max(eligible, key=lambda subset: subset.result.metrics["sharpe"]) if eligible else None
    overall_pass = sharpe_improved and turnover_improved

    metric_results = {subset.label: subset.result.metrics for subset in subset_results}
    metric_results["BTC B&H"] = benchmark.metrics
    metric_results["pysystemtrade EWMAC"] = PYSYSTEMTRADE_EWMAC

    return "\n".join(
        [
            "# H-312 Signal Subset Optimization",
            "",
            "## Setup",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            f"- Data: `{price_csv.as_posix()}`",
            f"- Common aligned window: {start} ~ {end}",
            f"- Rows: {rows}",
            "- Combination: equal weights + FDM, then clip to [-2, 2]",
            f"- Capital: {CAPITAL:,.0f}",
            f"- Vol target: {_format_percent(TARGET_VOL)}",
            f"- Vol lookback: {VOL_LOOKBACK}",
            f"- Cost: {_format_percent(COST_PER_ROUND_TRIP)} round trip",
            f"- Max leverage: {MAX_LEVERAGE:.1f}x",
            "",
            "## Subsets",
            _subset_table(subset_results),
            "",
            "## Seven-Column Metric Comparison",
            _metrics_table(metric_results),
            "",
            "## FDM, Turnover, Cost, and Realized Vol",
            _fdm_turnover_table(subset_results),
            "",
            "## MEAN_REV Speed Comparison",
            _mean_rev_speed_table(mean_rev_fast, mean_rev_slow),
            "",
            "## Rank by Net Sharpe",
            _rank_table(subset_results),
            "",
            "## Pass/Fail",
            f"- At least one subset Net Sharpe > E baseline ({baseline.metrics['sharpe']:.6f}): "
            f"{'PASS' if sharpe_improved else 'FAIL'}",
            f"- At least one subset Annual Turnover < E baseline ({baseline.metrics['annual_turnover']:.6f}): "
            f"{'PASS' if turnover_improved else 'FAIL'}",
            f"- Overall result: {'PASS' if overall_pass else 'FAIL'}",
            "",
            "## Mechanical Best Eligible Subset",
            _best_eligible_line(best_eligible),
            "",
            "## Known Limitations",
            "- This is in-sample only.",
            "- The measurement covers one symbol and one BTCUSDT market cycle.",
            "- Funding-rate cost is not included.",
            "- This card ranks observed subset metrics but does not make a final signal inclusion or exclusion recommendation.",
            "",
        ]
    )


def _subset_table(subset_results: list[SubsetResult]) -> str:
    lines = ["| Label | Description | Signals |", "|---|---|---|"]
    for subset in subset_results:
        lines.append(f"| {subset.label} | {subset.description} | {', '.join(subset.signal_names)} |")
    return "\n".join(lines)


def _metrics_table(results: dict[str, dict]) -> str:
    lines = ["| Metric | " + " | ".join(results.keys()) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in results) + "|")
    for label, key, kind in METRIC_ROWS:
        values = [_format_optional_metric(result.get(key), kind=kind) for result in results.values()]
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    return "\n".join(lines)


def _fdm_turnover_table(subset_results: list[SubsetResult]) -> str:
    lines = [
        "| Subset | FDM | Annual Turnover | Total Cost Drag | Realized Vol |",
        "|---|---:|---:|---:|---:|",
    ]
    for subset in subset_results:
        metrics = subset.result.metrics
        lines.append(
            f"| {subset.label} | {subset.fdm:.6f} | {metrics['annual_turnover']:.6f} | "
            f"{_format_percent(metrics['total_cost_drag'])} | {_format_percent(metrics['annual_volatility'])} |"
        )
    return "\n".join(lines)


def _mean_rev_speed_table(mean_rev_fast: BacktestResult, mean_rev_slow: BacktestResult) -> str:
    lines = [
        "| Signal | Window | Net Sharpe | Annual Turnover | Total Cost Drag | Realized Vol |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, window, result in (
        ("SIG_MEAN_REV", 20, mean_rev_fast),
        ("SIG_MEAN_REV_SLOW", 120, mean_rev_slow),
    ):
        metrics = result.metrics
        lines.append(
            f"| {name} | {window} | {metrics['sharpe']:.6f} | {metrics['annual_turnover']:.6f} | "
            f"{_format_percent(metrics['total_cost_drag'])} | {_format_percent(metrics['annual_volatility'])} |"
        )
    return "\n".join(lines)


def _rank_table(subset_results: list[SubsetResult]) -> str:
    ranked = sorted(subset_results, key=lambda subset: subset.result.metrics["sharpe"], reverse=True)
    lines = [
        "| Rank | Subset | Net Sharpe | Annual Turnover | Realized Vol |",
        "|---:|---|---:|---:|---:|",
    ]
    for rank, subset in enumerate(ranked, start=1):
        metrics = subset.result.metrics
        lines.append(
            f"| {rank} | {subset.label} | {metrics['sharpe']:.6f} | "
            f"{metrics['annual_turnover']:.6f} | {_format_percent(metrics['annual_volatility'])} |"
        )
    return "\n".join(lines)


def _best_eligible_line(subset: SubsetResult | None) -> str:
    if subset is None:
        return "- No subset has annual turnover below 15x."
    metrics = subset.result.metrics
    return (
        f"- Highest net Sharpe among subsets with turnover < 15x: subset {subset.label} "
        f"(Net Sharpe {metrics['sharpe']:.6f}, Annual Turnover {metrics['annual_turnover']:.6f})."
    )


def _format_optional_metric(value: float | None, *, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind == "percent":
        return _format_percent(value)
    return f"{value:.6f}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    main()
