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
EXPECTED_START = "2024-09-19"
EXPECTED_END = "2026-05-22"
H310_NO_FDM_METRICS = {
    "sharpe": 0.625799,
    "gross_sharpe": 0.998668,
    "cagr": 0.0271,
    "max_drawdown": -0.039539,
    "sortino": 0.930058,
    "calmar": 0.683401,
    "win_rate": 0.5115,
    "profit_factor": 1.117769,
    "annual_turnover": 8.279067,
    "total_cost_drag": 0.0277,
    "cost_sharpe_drag": 0.372869,
    "total_return": 0.0456,
    "annual_volatility": 0.0442,
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
    parser = argparse.ArgumentParser(description="Run H-311 FDM vol-restoration backtest.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h311-fdm-vol-restoration-{args.report_date}.md"
    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = pd.DataFrame({spec.name: spec.build_forecast(price) for spec in SIGNAL_SPECS}).dropna(how="any")
    start = forecasts.index.min().date().isoformat()
    end = forecasts.index.max().date().isoformat()
    if start != EXPECTED_START or end != EXPECTED_END:
        raise ValueError(f"unexpected aligned window: {start} ~ {end}")

    aligned_price = price.reindex(forecasts.index)
    fdm = compute_fdm(forecasts)
    combined_forecast = combine_forecasts(forecasts, apply_fdm=True, forecast_cap=FORECAST_CAP)
    fdm_result = run_forecast_backtest(combined_forecast, aligned_price)
    benchmark = buy_and_hold_result(aligned_price, capital=CAPITAL, periods_per_year=PERIODS_PER_YEAR)

    report = render_report(
        forecasts=forecasts,
        fdm=fdm,
        fdm_result=fdm_result,
        benchmark=benchmark,
        price_csv=args.price_csv,
        rows=len(forecasts),
        start=start,
        end=end,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"fdm={fdm:.6f}")
    print(f"annual_volatility={fdm_result.metrics['annual_volatility']:.6f}")
    print(f"net_sharpe={fdm_result.metrics['sharpe']:.6f}")


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
    forecasts: pd.DataFrame,
    fdm: float,
    fdm_result: BacktestResult,
    benchmark: BacktestResult,
    price_csv: Path,
    rows: int,
    start: str,
    end: str,
) -> str:
    vol_pass = fdm_result.metrics["annual_volatility"] >= 0.12
    sharpe_threshold = H310_NO_FDM_METRICS["sharpe"] - 0.05
    sharpe_pass = fdm_result.metrics["sharpe"] >= sharpe_threshold
    overall_pass = vol_pass and sharpe_pass
    return "\n".join(
        [
            "# H-311 FDM Vol Restoration",
            "",
            "## Setup",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            f"- Data: `{price_csv.as_posix()}`",
            f"- Window: {start} ~ {end}",
            f"- Rows: {rows}",
            "- Signals: SIG_TREND_FAST, SIG_MOMENTUM, SIG_MEAN_REV, SIG_VOL_REGIME",
            f"- FDM formula: `1 / sqrt(w' @ rho @ w)`",
            f"- Forecast cap after FDM: +/-{FORECAST_CAP:.1f}",
            f"- Capital: {CAPITAL:,.0f}",
            f"- Vol target: {_format_percent(TARGET_VOL)}",
            f"- Vol lookback: {VOL_LOOKBACK}",
            f"- Cost: {_format_percent(COST_PER_ROUND_TRIP)} round trip",
            f"- Max leverage: {MAX_LEVERAGE:.1f}x",
            "",
            "## FDM",
            f"- FDM value: {fdm:.6f}",
            "",
            "## Forecast Pearson Correlation Matrix",
            _frame_to_markdown(forecasts.corr()),
            "",
            "## Metric Comparison",
            _metrics_table(
                {
                    "H-310 No FDM": H310_NO_FDM_METRICS,
                    "H-311 FDM": fdm_result.metrics,
                    "BTC B&H": benchmark.metrics,
                }
            ),
            "",
            "## Vol Restoration",
            f"- Standard: annual volatility >= 12.00%",
            f"- Observed: {_format_percent(fdm_result.metrics['annual_volatility'])}",
            f"- Result: {'PASS' if vol_pass else 'FAIL'}",
            "",
            "## Sharpe Preservation",
            f"- Standard: net Sharpe >= {sharpe_threshold:.6f} (H-310 net Sharpe - 0.05)",
            f"- Observed: {fdm_result.metrics['sharpe']:.6f}",
            f"- Result: {'PASS' if sharpe_pass else 'FAIL'}",
            "",
            "## Pass/Fail",
            f"- Overall result: {'PASS' if overall_pass else 'FAIL'}",
            "",
            "## Interpretation",
            "- H-310 is retained as the no-FDM baseline.",
            "- H-311 tests whether forecast scaling restores risk usage after signal cancellation.",
            "- No signal add/remove/reweight decision is made in this card.",
            "",
        ]
    )


def _metrics_table(results: dict[str, dict]) -> str:
    lines = ["| Metric | " + " | ".join(results.keys()) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in results) + "|")
    for label, key, kind in METRIC_ROWS:
        values = [_format_metric(result[key], kind=kind) for result in results.values()]
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    return "\n".join(lines)


def _frame_to_markdown(frame: pd.DataFrame) -> str:
    lines = ["| | " + " | ".join(frame.columns) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in frame.columns) + "|")
    for index, row in frame.iterrows():
        lines.append("| " + str(index) + " | " + " | ".join(f"{value:.6f}" for value in row) + " |")
    return "\n".join(lines)


def _format_metric(value: float, *, kind: str) -> str:
    if kind == "percent":
        return _format_percent(value)
    return f"{value:.6f}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    main()
