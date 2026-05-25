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

from trading_learning.backtest.engine import BacktestResult, backtest_forecast, buy_and_hold_result  # noqa: E402
from trading_learning.signals.forecast_library import (  # noqa: E402
    ewmac_forecast,
    mean_reversion_forecast,
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
EXPECTED_START = "2024-09-19"
EXPECTED_END = "2026-05-22"
PYSYSTEMTRADE_EWMAC = {
    "sharpe": 0.617,
    "cagr": 0.1231,
    "max_drawdown": -0.175,
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
class SignalSpec:
    name: str

    def build_forecast(self, price: pd.Series) -> pd.Series:
        if self.name == "SIG_TREND_FAST":
            return ewmac_forecast(price, fast_span=8, slow_span=32, normalization="expanding").rename(self.name)
        if self.name == "SIG_MOMENTUM":
            return momentum_forecast(price, lookback=60, normalization="expanding").rename(self.name)
        if self.name == "SIG_MEAN_REV":
            return mean_reversion_forecast(price, window=20, normalization="expanding").rename(self.name)
        if self.name == "SIG_VOL_REGIME":
            return vol_regime_forecast(price, vol_window=60, normalization="expanding").rename(self.name)
        raise ValueError(f"unknown signal: {self.name}")


SIGNAL_SPECS = (
    SignalSpec("SIG_TREND_FAST"),
    SignalSpec("SIG_MOMENTUM"),
    SignalSpec("SIG_MEAN_REV"),
    SignalSpec("SIG_VOL_REGIME"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-310 equal-weight four-signal system backtest.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h310-equal-weight-system-{args.report_date}.md"
    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = pd.DataFrame({spec.name: spec.build_forecast(price) for spec in SIGNAL_SPECS}).dropna(how="any")
    if forecasts.index.min().date().isoformat() != EXPECTED_START or forecasts.index.max().date().isoformat() != EXPECTED_END:
        raise ValueError(
            f"unexpected aligned window: {forecasts.index.min().date()} ~ {forecasts.index.max().date()}"
        )
    aligned_price = price.reindex(forecasts.index)

    results: dict[str, BacktestResult] = {}
    for spec in SIGNAL_SPECS:
        results[spec.name] = run_forecast_backtest(forecasts[spec.name], aligned_price)
    combined_forecast = forecasts.mean(axis=1).rename("EQUAL_WEIGHT_SYSTEM")
    combined = run_forecast_backtest(combined_forecast, aligned_price)
    benchmark = buy_and_hold_result(aligned_price, capital=CAPITAL, periods_per_year=PERIODS_PER_YEAR)

    report = render_report(
        single_results=results,
        combined=combined,
        benchmark=benchmark,
        price_csv=args.price_csv,
        rows=len(forecasts),
        start=forecasts.index.min().date().isoformat(),
        end=forecasts.index.max().date().isoformat(),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"combined_net_sharpe={combined.metrics['sharpe']:.6f}")
    print(f"best_single_net_sharpe={max(result.metrics['sharpe'] for result in results.values()):.6f}")
    print(f"combined_max_dd={combined.metrics['max_drawdown']:.6f}")
    print(f"bh_max_dd={benchmark.metrics['max_drawdown']:.6f}")


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
    single_results: dict[str, BacktestResult],
    combined: BacktestResult,
    benchmark: BacktestResult,
    price_csv: Path,
    rows: int,
    start: str,
    end: str,
) -> str:
    ordered_results = dict(single_results)
    ordered_results["EQUAL_WEIGHT_SYSTEM"] = combined
    ordered_results["BTC B&H"] = benchmark
    best_single_sharpe = max(result.metrics["sharpe"] for result in single_results.values())
    checks = {
        "Net Sharpe >= 0.4": combined.metrics["sharpe"] >= 0.4,
        "Net Sharpe > best single signal": combined.metrics["sharpe"] > best_single_sharpe,
        "Max DD less severe than BTC B&H": abs(combined.metrics["max_drawdown"]) < abs(benchmark.metrics["max_drawdown"]),
    }
    overall_pass = all(checks.values())
    return "\n".join(
        [
            "# H-310 Equal-Weight Four-Signal System",
            "",
            "## Setup",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            f"- Data: `{price_csv.as_posix()}`",
            f"- Window: {start} ~ {end}",
            f"- Rows: {rows}",
            "- Combined forecast: mean(SIG_TREND_FAST, SIG_MOMENTUM, SIG_MEAN_REV, SIG_VOL_REGIME)",
            f"- Capital: {CAPITAL:,.0f}",
            f"- Vol target: {_format_percent(TARGET_VOL)}",
            f"- Vol lookback: {VOL_LOOKBACK}",
            f"- Cost: {_format_percent(COST_PER_ROUND_TRIP)} round trip",
            f"- Max leverage: {MAX_LEVERAGE:.1f}x",
            "",
            "## Six-Column Metric Comparison",
            _metrics_table(ordered_results),
            "",
            "## pysystemtrade EWMAC Comparison",
            _pysystemtrade_comparison(combined),
            "",
            "## Pass/Fail",
            _pass_fail_table(checks, combined=combined, best_single_sharpe=best_single_sharpe, benchmark=benchmark),
            f"- Overall result: {'PASS' if overall_pass else 'FAIL'}",
            "",
            "## Cost and Turnover",
            f"- Combination annual turnover: {combined.metrics['annual_turnover']:.6f}",
            f"- Combination total cost drag: {_format_percent(combined.metrics['total_cost_drag'])}",
            f"- Combination cost Sharpe drag: {combined.metrics['cost_sharpe_drag']:.6f}",
            "",
            "## Known Limitations",
            "- Funding-rate cost is not included.",
            "- The measurement covers only one BTCUSDT bull/bear cycle.",
            "- The four-signal set contains redundant trend plus momentum exposure.",
            "- No recommendation is made here to add, remove, or reweight signals.",
            "",
        ]
    )


def _metrics_table(results: dict[str, BacktestResult]) -> str:
    lines = ["| Metric | " + " | ".join(results.keys()) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in results) + "|")
    for label, key, kind in METRIC_ROWS:
        values = [_format_metric(result.metrics[key], kind=kind) for result in results.values()]
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    return "\n".join(lines)


def _pysystemtrade_comparison(combined: BacktestResult) -> str:
    rows = [
        ("Sharpe", combined.metrics["sharpe"], PYSYSTEMTRADE_EWMAC["sharpe"], "number"),
        ("CAGR", combined.metrics["cagr"], PYSYSTEMTRADE_EWMAC["cagr"], "percent"),
        ("Max DD", combined.metrics["max_drawdown"], PYSYSTEMTRADE_EWMAC["max_drawdown"], "percent"),
        ("Vol", combined.metrics["annual_volatility"], PYSYSTEMTRADE_EWMAC["annual_volatility"], "percent"),
    ]
    lines = ["| Metric | H-310 Equal Weight | pysystemtrade EWMAC |", "|---|---:|---:|"]
    for label, ours, reference, kind in rows:
        lines.append(f"| {label} | {_format_metric(ours, kind=kind)} | {_format_metric(reference, kind=kind)} |")
    return "\n".join(lines)


def _pass_fail_table(
    checks: dict[str, bool],
    *,
    combined: BacktestResult,
    best_single_sharpe: float,
    benchmark: BacktestResult,
) -> str:
    observed = {
        "Net Sharpe >= 0.4": f"{combined.metrics['sharpe']:.6f} >= 0.400000",
        "Net Sharpe > best single signal": f"{combined.metrics['sharpe']:.6f} > {best_single_sharpe:.6f}",
        "Max DD less severe than BTC B&H": (
            f"{_format_percent(combined.metrics['max_drawdown'])} vs "
            f"{_format_percent(benchmark.metrics['max_drawdown'])}"
        ),
    }
    lines = ["| Criterion | Observed | Result |", "|---|---|---|"]
    for criterion, passed in checks.items():
        lines.append(f"| {criterion} | {observed[criterion]} | {'PASS' if passed else 'FAIL'} |")
    return "\n".join(lines)


def _format_metric(value: float, *, kind: str) -> str:
    if kind == "percent":
        return _format_percent(value)
    return f"{value:.6f}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    main()
