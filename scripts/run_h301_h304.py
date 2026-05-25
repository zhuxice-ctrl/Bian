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
    hypothesis_id: str
    name: str
    slug: str
    description: str
    parameters: str
    pass_metric: str
    pass_threshold: float
    prior_note: str
    report_filename: str

    def build_forecast(self, price: pd.Series) -> pd.Series:
        if self.hypothesis_id == "H-301":
            return ewmac_forecast(price, fast_span=8, slow_span=32, normalization="expanding").rename(self.name)
        if self.hypothesis_id == "H-302":
            return momentum_forecast(price, lookback=60, normalization="expanding").rename(self.name)
        if self.hypothesis_id == "H-303":
            return mean_reversion_forecast(price, window=20, normalization="expanding").rename(self.name)
        if self.hypothesis_id == "H-304":
            return vol_regime_forecast(price, vol_window=60, normalization="expanding").rename(self.name)
        raise ValueError(f"unknown signal spec: {self.hypothesis_id}")


SIGNAL_SPECS = (
    SignalSpec(
        hypothesis_id="H-301",
        name="SIG_TREND_FAST",
        slug="ewmac-fast-trend",
        description="EWMAC(8,32) fast trend forecast.",
        parameters="fast_span=8, slow_span=32, normalization=expanding",
        pass_metric="Net Sharpe",
        pass_threshold=0.3,
        prior_note="H-301 is the fast trend baseline from the H-213 signal set.",
        report_filename="ablation-h301-ewmac-fast-trend-{date}.md",
    ),
    SignalSpec(
        hypothesis_id="H-302",
        name="SIG_MOMENTUM",
        slug="momentum",
        description="Past 60-day return momentum forecast.",
        parameters="lookback=60, normalization=expanding",
        pass_metric="Net Sharpe",
        pass_threshold=0.3,
        prior_note="H-214 showed this signal as regime-dependent: first half 1.50, second half -0.21.",
        report_filename="ablation-h302-momentum-{date}.md",
    ),
    SignalSpec(
        hypothesis_id="H-303",
        name="SIG_MEAN_REV",
        slug="mean-reversion",
        description="-1 times 20-day price z-score mean-reversion forecast.",
        parameters="window=20, normalization=expanding",
        pass_metric="Net Sharpe",
        pass_threshold=0.1,
        prior_note="H-214 showed this as the only candidate with positive standalone Sharpe in both halves.",
        report_filename="ablation-h303-mean-reversion-{date}.md",
    ),
    SignalSpec(
        hypothesis_id="H-304",
        name="SIG_VOL_REGIME",
        slug="vol-regime",
        description="Expanding-normalized rolling 60-day volatility-regime forecast.",
        parameters="vol_window=60, normalization=expanding",
        pass_metric="Net Sharpe",
        pass_threshold=0.0,
        prior_note="H-214 showed this signal flipping sign: first half -0.87, second half +1.40.",
        report_filename="ablation-h304-vol-regime-{date}.md",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-301 through H-304 single-signal BTC backtests.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "exports")
    args = parser.parse_args()

    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = pd.DataFrame({spec.name: spec.build_forecast(price) for spec in SIGNAL_SPECS}).dropna(how="any")
    if forecasts.index.min().date().isoformat() != EXPECTED_START or forecasts.index.max().date().isoformat() != EXPECTED_END:
        raise ValueError(
            f"unexpected aligned window: {forecasts.index.min().date()} ~ {forecasts.index.max().date()}"
        )
    aligned_price = price.reindex(forecasts.index)
    benchmark = buy_and_hold_result(aligned_price, capital=CAPITAL, periods_per_year=PERIODS_PER_YEAR)

    results: dict[str, BacktestResult] = {}
    for spec in SIGNAL_SPECS:
        result = backtest_forecast(
            forecasts[spec.name],
            aligned_price,
            target_vol=TARGET_VOL,
            vol_lookback=VOL_LOOKBACK,
            cost_per_round_trip=COST_PER_ROUND_TRIP,
            capital=CAPITAL,
            max_leverage=MAX_LEVERAGE,
            periods_per_year=PERIODS_PER_YEAR,
        )
        results[spec.name] = result
        report = render_signal_report(
            spec=spec,
            result=result,
            benchmark=benchmark,
            price_csv=args.price_csv,
            rows=len(forecasts),
            start=forecasts.index.min().date().isoformat(),
            end=forecasts.index.max().date().isoformat(),
        )
        output_path = args.output_dir / spec.report_filename.format(date=args.report_date)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"wrote {output_path}")

    summary_path = args.output_dir / f"summary-h301-h304-{args.report_date}.md"
    summary_path.write_text(render_summary_report(results=results, benchmark=benchmark), encoding="utf-8")
    print(f"wrote {summary_path}")


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


def render_signal_report(
    *,
    spec: SignalSpec,
    result: BacktestResult,
    benchmark: BacktestResult,
    price_csv: Path,
    rows: int,
    start: str,
    end: str,
) -> str:
    passed = result.metrics["sharpe"] >= spec.pass_threshold
    return "\n".join(
        [
            f"# {spec.hypothesis_id} {spec.name} Baseline Backtest",
            "",
            "## Signal",
            f"- Description: {spec.description}",
            f"- Parameters: `{spec.parameters}`",
            "- Forecast source: `trading_learning.signals.forecast_library`",
            f"- Prior note: {spec.prior_note}",
            "",
            "## Backtest Setup",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            f"- Data: `{price_csv.as_posix()}`",
            f"- Window: {start} ~ {end}",
            f"- Rows: {rows}",
            f"- Capital: {CAPITAL:,.0f}",
            f"- Vol target: {_format_percent(TARGET_VOL)}",
            f"- Vol lookback: {VOL_LOOKBACK}",
            f"- Cost: {_format_percent(COST_PER_ROUND_TRIP)} round trip",
            f"- Max leverage: {MAX_LEVERAGE:.1f}x",
            "- Benchmark: BTC buy-and-hold over the same window",
            "",
            "## Metrics",
            _metrics_table({"Signal": result}),
            "",
            "## BTC Buy-and-Hold Comparison",
            _metrics_table({"Signal": result, "BTC B&H": benchmark}),
            "",
            "## Pass/Fail",
            f"- Standard: net Sharpe >= {spec.pass_threshold:.2f}",
            f"- Observed net Sharpe: {result.metrics['sharpe']:.6f}",
            f"- Result: {'PASS' if passed else 'FAIL'}",
            "",
            "## Known Limitations",
            "- Funding-rate cost is not included.",
            "- This is a single BTCUSDT 1d window, not a walk-forward or multi-market validation.",
            "- No signal selection recommendation is made here; signal combination is deferred to H-310.",
            "",
        ]
    )


def render_summary_report(*, results: dict[str, BacktestResult], benchmark: BacktestResult) -> str:
    ordered_results = {spec.name: results[spec.name] for spec in SIGNAL_SPECS}
    ordered_results["BTC B&H"] = benchmark
    return "\n".join(
        [
            "# H-301~H-304 Single-Signal Backtest Summary",
            "",
            "## Shared Setup",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            f"- Window: {EXPECTED_START} ~ {EXPECTED_END}",
            f"- Capital: {CAPITAL:,.0f}",
            f"- Vol target: {_format_percent(TARGET_VOL)}",
            f"- Cost: {_format_percent(COST_PER_ROUND_TRIP)} round trip",
            f"- Max leverage: {MAX_LEVERAGE:.1f}x",
            "- Funding-rate cost is not included.",
            "",
            "## Metrics",
            _metrics_table(ordered_results),
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


def _format_metric(value: float, *, kind: str) -> str:
    if kind == "percent":
        return _format_percent(value)
    return f"{value:.6f}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    main()
