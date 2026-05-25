from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from trading_learning.backtest.engine import BacktestResult, backtest_forecast, buy_and_hold_result, combine_forecasts, compute_fdm  # noqa: E402
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
class SplitResult:
    name: str
    start: str
    end: str
    rows: int
    fdm: float
    system: BacktestResult
    benchmark: BacktestResult


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-320 train/test FDM walk-forward validation.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h320-walk-forward-{args.report_date}.md"
    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = build_forecasts(price).dropna(how="any")
    start = forecasts.index.min().date().isoformat()
    end = forecasts.index.max().date().isoformat()
    if start != EXPECTED_START or end != EXPECTED_END:
        raise ValueError(f"unexpected aligned window: {start} ~ {end}")

    midpoint = len(forecasts) // 2
    train_forecasts = forecasts.iloc[:midpoint]
    test_forecasts = forecasts.iloc[midpoint:]
    train_price = price.reindex(train_forecasts.index)
    test_price = price.reindex(test_forecasts.index)

    fdm_train = compute_fdm(train_forecasts)
    fdm_test = compute_fdm(test_forecasts)
    combined_train = combine_forecasts(train_forecasts, apply_fdm=True, forecast_cap=FORECAST_CAP)
    combined_test = apply_frozen_fdm(test_forecasts, fdm=fdm_train)

    train = SplitResult(
        name="Train",
        start=train_forecasts.index.min().date().isoformat(),
        end=train_forecasts.index.max().date().isoformat(),
        rows=len(train_forecasts),
        fdm=fdm_train,
        system=run_forecast_backtest(combined_train, train_price),
        benchmark=buy_and_hold_result(train_price, capital=CAPITAL, periods_per_year=PERIODS_PER_YEAR),
    )
    test = SplitResult(
        name="Test",
        start=test_forecasts.index.min().date().isoformat(),
        end=test_forecasts.index.max().date().isoformat(),
        rows=len(test_forecasts),
        fdm=fdm_test,
        system=run_forecast_backtest(combined_test, test_price),
        benchmark=buy_and_hold_result(test_price, capital=CAPITAL, periods_per_year=PERIODS_PER_YEAR),
    )

    report = render_report(
        train=train,
        test=test,
        price_csv=args.price_csv,
        full_rows=len(forecasts),
        full_start=start,
        full_end=end,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"train_fdm={fdm_train:.6f}")
    print(f"test_fdm={fdm_test:.6f}")
    print(f"train_sharpe={train.system.metrics['sharpe']:.6f}")
    print(f"test_sharpe={test.system.metrics['sharpe']:.6f}")


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
            "SIG_MEAN_REV": mean_reversion_forecast(price, window=20, normalization="expanding").rename(
                "SIG_MEAN_REV"
            ),
            "SIG_VOL_REGIME": vol_regime_forecast(price, vol_window=60, normalization="expanding").rename(
                "SIG_VOL_REGIME"
            ),
        }
    )


def apply_frozen_fdm(forecasts: pd.DataFrame, *, fdm: float) -> pd.Series:
    weights = np.ones(forecasts.shape[1]) / forecasts.shape[1]
    raw = forecasts @ weights
    return (raw * fdm).clip(-FORECAST_CAP, FORECAST_CAP).rename("combined_forecast")


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
    train: SplitResult,
    test: SplitResult,
    price_csv: Path,
    full_rows: int,
    full_start: str,
    full_end: str,
) -> str:
    train_sharpe = train.system.metrics["sharpe"]
    test_sharpe = test.system.metrics["sharpe"]
    sharpe_decay = test_sharpe / train_sharpe if train_sharpe != 0.0 else float("nan")
    fdm_drift = abs(train.fdm - test.fdm) / train.fdm
    positive_test_pass = test_sharpe > 0.0
    disaster_pass = test_sharpe > -0.3
    drift_pass = fdm_drift < 0.30
    overall_pass = positive_test_pass and disaster_pass and drift_pass
    return "\n".join(
        [
            "# H-320 Walk-Forward Validation",
            "",
            "## Setup",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            f"- Data: `{price_csv.as_posix()}`",
            f"- Full aligned window: {full_start} ~ {full_end}",
            f"- Full rows: {full_rows}",
            "- Split rule: `len // 2`",
            "- Train FDM is estimated on Train and frozen for Test.",
            f"- Capital: {CAPITAL:,.0f}",
            f"- Vol target: {_format_percent(TARGET_VOL)}",
            f"- Vol lookback: {VOL_LOOKBACK}",
            f"- Cost: {_format_percent(COST_PER_ROUND_TRIP)} round trip",
            f"- Max leverage: {MAX_LEVERAGE:.1f}x",
            "",
            "## Train/Test Windows",
            _split_table(train, test),
            "",
            "## FDM Drift",
            f"- FDM_train: {train.fdm:.6f}",
            f"- FDM_test: {test.fdm:.6f}",
            f"- Drift: {_format_percent(fdm_drift)}",
            "",
            "## Metric Comparison",
            _metrics_table(
                {
                    "Train System": train.system.metrics,
                    "Test System": test.system.metrics,
                    "Train B&H": train.benchmark.metrics,
                    "Test B&H": test.benchmark.metrics,
                }
            ),
            "",
            "## Sharpe Decay",
            f"- Train net Sharpe: {train_sharpe:.6f}",
            f"- Test net Sharpe: {test_sharpe:.6f}",
            f"- Test / Train Sharpe: {sharpe_decay:.6f}",
            "",
            "## Pass/Fail",
            _pass_fail_table(
                [
                    ("Test Net Sharpe > 0.0", f"{test_sharpe:.6f} > 0.000000", positive_test_pass),
                    ("Test Net Sharpe > -0.3", f"{test_sharpe:.6f} > -0.300000", disaster_pass),
                    ("FDM drift < 30%", f"{_format_percent(fdm_drift)} < 30.00%", drift_pass),
                ]
            ),
            f"- Overall result: {'PASS' if overall_pass else 'FAIL'}",
            "",
            "## Known Limitations",
            "- This is one train/test split, not k-fold or repeated walk-forward validation.",
            "- The test period is a specific regime: BTC bull-market top plus correction.",
            "- FDM is the only frozen fitted parameter; signal parameters are theory-driven and not fitted in this card.",
            "- No system modification recommendation is made here.",
            "",
        ]
    )


def _split_table(train: SplitResult, test: SplitResult) -> str:
    lines = ["| Split | Start | End | Rows |", "|---|---|---|---:|"]
    for split in (train, test):
        lines.append(f"| {split.name} | {split.start} | {split.end} | {split.rows} |")
    return "\n".join(lines)


def _metrics_table(results: dict[str, dict]) -> str:
    lines = ["| Metric | " + " | ".join(results.keys()) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in results) + "|")
    for label, key, kind in METRIC_ROWS:
        values = [_format_metric(result[key], kind=kind) for result in results.values()]
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    return "\n".join(lines)


def _pass_fail_table(rows: list[tuple[str, str, bool]]) -> str:
    lines = ["| Criterion | Observed | Result |", "|---|---|---|"]
    for criterion, observed, passed in rows:
        lines.append(f"| {criterion} | {observed} | {'PASS' if passed else 'FAIL'} |")
    return "\n".join(lines)


def _format_metric(value: float, *, kind: str) -> str:
    if kind == "percent":
        return _format_percent(value)
    return f"{value:.6f}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    main()
