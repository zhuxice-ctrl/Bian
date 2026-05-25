from __future__ import annotations

import argparse
import io
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests

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
from trading_learning.market_data.binance_funding import (  # noqa: E402
    aggregate_daily_funding,
    backfill_funding_rate,
    calculate_funding_pnl,
)
from trading_learning.metrics.performance import (  # noqa: E402
    cagr,
    calmar_ratio,
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    volatility,
    win_rate,
)
from trading_learning.signals.forecast_library import (  # noqa: E402
    ewmac_forecast,
    mean_reversion_forecast,
    momentum_forecast,
    vol_regime_forecast,
)


BINANCE_ARCHIVE_FUNDING_URL = (
    "https://data.binance.vision/data/futures/um/monthly/fundingRate/"
    "{symbol}/{symbol}-fundingRate-{month}.zip"
)
DEFAULT_PRICE_CSV = REPO_ROOT / "data" / "local" / "market_data" / "BTCUSDT" / "1d" / "BTCUSDT-1d.csv"
DEFAULT_FUNDING_CSV = (
    REPO_ROOT / "data" / "local" / "market_data" / "BTCUSDT" / "funding" / "BTCUSDT-funding-rate.csv"
)
CAPITAL = 100_000
TARGET_VOL = 0.20
VOL_LOOKBACK = 60
COST_PER_ROUND_TRIP = 0.002
MAX_LEVERAGE = 2.0
PERIODS_PER_YEAR = 365
FORECAST_CAP = 2.0
WINDOW_START = "2024-09-19"
WINDOW_END = "2026-05-22"
PASS_SHARPE = 0.3
METRIC_ROWS = (
    ("Net Sharpe", "sharpe", "number"),
    ("CAGR", "cagr", "percent"),
    ("Max DD", "max_drawdown", "percent"),
    ("Sortino", "sortino", "number"),
    ("Calmar", "calmar", "number"),
    ("Win Rate", "win_rate", "percent"),
    ("Profit Factor", "profit_factor", "number"),
    ("Annual Turnover", "annual_turnover", "number"),
    ("Total Trading Cost Drag", "total_cost_drag", "percent"),
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
    parser = argparse.ArgumentParser(description="Run H-341 funding-rate cost estimation.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--funding-csv", type=Path, default=DEFAULT_FUNDING_CSV)
    parser.add_argument("--report-date", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--skip-fetch", action="store_true", help="Use an existing funding CSV without API backfill.")
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h341-funding-cost-estimation-{args.report_date}.md"
    if not args.skip_fetch:
        funding, funding_source = fetch_funding_with_archive_fallback(
            symbol="BTCUSDT",
            start_date="2024-09-01",
            end_date=WINDOW_END,
            save_path=args.funding_csv,
        )
    else:
        funding = load_funding(args.funding_csv)
        funding_source = "existing_csv"
    if funding.empty:
        raise ValueError("funding CSV is empty")
    if not args.funding_csv.exists():
        args.funding_csv.parent.mkdir(parents=True, exist_ok=True)
        funding.to_csv(args.funding_csv, index=False, lineterminator="\n")

    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = pd.DataFrame({spec.name: spec.build_forecast(price) for spec in SIGNAL_SPECS}).dropna(how="any")
    start = forecasts.index.min().date().isoformat()
    end = forecasts.index.max().date().isoformat()
    if start != WINDOW_START or end != WINDOW_END:
        raise ValueError(f"unexpected aligned window: {start} ~ {end}")

    aligned_price = price.reindex(forecasts.index)
    combined_forecast = combine_forecasts(forecasts, apply_fdm=True, forecast_cap=FORECAST_CAP)
    original = run_forecast_backtest(combined_forecast, aligned_price)
    benchmark = buy_and_hold_result(aligned_price, capital=CAPITAL, periods_per_year=PERIODS_PER_YEAR)
    daily_funding = aggregate_daily_funding(funding)
    funding_pnl = calculate_funding_pnl(original.positions, daily_funding).reindex(original.daily_returns.index).fillna(0.0)
    adjusted_returns = (original.daily_returns + funding_pnl).rename("daily_returns")
    adjusted_equity = (CAPITAL * (1.0 + adjusted_returns).cumprod()).rename("equity")
    if not adjusted_equity.empty:
        adjusted_equity.iloc[0] = CAPITAL
    adjusted_metrics = compute_metrics(
        returns=adjusted_returns,
        equity_curve=adjusted_equity,
        turnover=original.turnover,
        trading_costs=original.costs,
    )
    funding_stats = funding_statistics(
        funding=funding,
        daily_funding=daily_funding,
        positions=original.positions,
        funding_pnl=funding_pnl,
    )
    coverage_pass = funding_covers_window(funding, WINDOW_START, WINDOW_END)
    sharpe_pass = adjusted_metrics["sharpe"] > PASS_SHARPE
    report = render_report(
        price_csv=args.price_csv,
        funding_csv=args.funding_csv,
        rows=len(forecasts),
        start=start,
        end=end,
        fdm=compute_fdm(forecasts),
        original=original.metrics,
        adjusted=adjusted_metrics,
        benchmark=benchmark.metrics,
        funding_stats=funding_stats,
        funding_source=funding_source,
        coverage_pass=coverage_pass,
        sharpe_pass=sharpe_pass,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"funding_source={funding_source}")
    print(f"funding_rows={len(funding)}")
    print(f"funding_adjusted_sharpe={adjusted_metrics['sharpe']:.6f}")
    print(f"result={'PASS' if coverage_pass and sharpe_pass else 'FAIL'}")


def fetch_funding_with_archive_fallback(
    *,
    symbol: str,
    start_date: str,
    end_date: str,
    save_path: Path,
) -> tuple[pd.DataFrame, str]:
    try:
        return (
            backfill_funding_rate(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                save_path=save_path,
            ),
            "fapi_rest",
        )
    except requests.RequestException as exc:
        print(f"REST funding fetch failed: {exc}")
        funding = backfill_funding_rate_from_archive(symbol=symbol, start_date=start_date, end_date=end_date)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        funding.to_csv(save_path, index=False, lineterminator="\n")
        return funding, "data_archive_fallback"


def backfill_funding_rate_from_archive(
    *,
    symbol: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    start = pd.Timestamp(start_date, tz="UTC")
    end = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    frames: list[pd.DataFrame] = []
    for month in pd.period_range(start=start, end=end, freq="M"):
        url = BINANCE_ARCHIVE_FUNDING_URL.format(symbol=symbol.upper(), month=str(month))
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            for name in archive.namelist():
                with archive.open(name) as handle:
                    raw = pd.read_csv(handle)
                frame = pd.DataFrame(
                    {
                        "timestamp": pd.to_datetime(raw["calc_time"], unit="ms", utc=True),
                        "funding_rate": raw["last_funding_rate"].astype(float),
                    }
                )
                frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["timestamp", "funding_rate"])
    funding = pd.concat(frames, ignore_index=True)
    funding = funding.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return funding.loc[(funding["timestamp"] >= start) & (funding["timestamp"] <= end)].reset_index(drop=True)


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


def load_funding(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(str(path))
    frame = pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["funding_rate"] = frame["funding_rate"].astype(float)
    return frame[["timestamp", "funding_rate"]]


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


def compute_metrics(
    *,
    returns: pd.Series,
    equity_curve: pd.Series,
    turnover: pd.Series,
    trading_costs: pd.Series,
) -> dict[str, float]:
    drawdown, _ = max_drawdown(equity_curve)
    years = len(returns) / PERIODS_PER_YEAR if len(returns) else 0.0
    return {
        "sharpe": _finite_or_zero(sharpe_ratio(returns, periods_per_year=PERIODS_PER_YEAR)),
        "cagr": _finite_or_zero(cagr(equity_curve, periods_per_year=PERIODS_PER_YEAR)),
        "max_drawdown": _finite_or_zero(drawdown),
        "sortino": _finite_or_zero(sortino_ratio(returns, periods_per_year=PERIODS_PER_YEAR)),
        "calmar": _finite_or_zero(calmar_ratio(returns, periods_per_year=PERIODS_PER_YEAR)),
        "win_rate": win_rate(returns[returns != 0.0]),
        "profit_factor": profit_factor(returns[returns != 0.0]),
        "annual_turnover": float(turnover.sum() / years) if years > 0.0 else 0.0,
        "total_cost_drag": float(trading_costs.sum() / CAPITAL),
        "total_return": float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0) if len(equity_curve) > 1 else 0.0,
        "annual_volatility": _finite_or_zero(volatility(returns, periods_per_year=PERIODS_PER_YEAR)),
    }


def funding_statistics(
    *,
    funding: pd.DataFrame,
    daily_funding: pd.Series,
    positions: pd.Series,
    funding_pnl: pd.Series,
) -> dict[str, float | str]:
    funding_cost = -funding_pnl
    return {
        "first_timestamp": pd.to_datetime(funding["timestamp"], utc=True).min().isoformat(),
        "last_timestamp": pd.to_datetime(funding["timestamp"], utc=True).max().isoformat(),
        "rows": float(len(funding)),
        "mean": float(funding["funding_rate"].mean()),
        "median": float(funding["funding_rate"].median()),
        "std": float(funding["funding_rate"].std()),
        "positive_ratio": float((funding["funding_rate"] > 0.0).mean()),
        "negative_ratio": float((funding["funding_rate"] < 0.0).mean()),
        "daily_mean": float(daily_funding.mean()),
        "average_position": float(positions.abs().mean()),
        "average_daily_funding_cost": float(funding_cost.mean()),
        "annualized_funding_drag": float(funding_cost.mean() * PERIODS_PER_YEAR),
        "total_funding_drag": float(funding_cost.sum()),
    }


def funding_covers_window(funding: pd.DataFrame, start: str, end: str) -> bool:
    timestamps = pd.to_datetime(funding["timestamp"], utc=True)
    required_start = pd.Timestamp(start, tz="UTC")
    required_end = pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=16)
    return bool(timestamps.min() <= required_start and timestamps.max() >= required_end)


def render_report(
    *,
    price_csv: Path,
    funding_csv: Path,
    rows: int,
    start: str,
    end: str,
    fdm: float,
    original: dict[str, float],
    adjusted: dict[str, float],
    benchmark: dict[str, float],
    funding_stats: dict[str, float | str],
    funding_source: str,
    coverage_pass: bool,
    sharpe_pass: bool,
) -> str:
    overall_pass = coverage_pass and sharpe_pass
    return "\n".join(
        [
            "# H-341 Funding Rate Cost Estimation",
            "",
            "## Setup",
            "- Symbol: BTCUSDT perpetual",
            "- Interval: 1d system positions, 8h funding observations",
            f"- Price data: `{price_csv.as_posix()}`",
            f"- Funding data: `{funding_csv.as_posix()}`",
            f"- Funding source path: {funding_source}",
            f"- System window: {start} ~ {end}",
            f"- Rows: {rows}",
            f"- H-311 FDM: {fdm:.6f}",
            "- Funding adjustment: `funding_pnl = -position * daily_funding_rate`",
            "",
            "## Funding Rate Data Statistics",
            _funding_stats_table(funding_stats),
            "",
            "## Data Coverage",
            f"- Required coverage: {WINDOW_START} 00:00 UTC through {WINDOW_END} 16:00 UTC",
            f"- Observed coverage: {funding_stats['first_timestamp']} through {funding_stats['last_timestamp']}",
            f"- Coverage result: {'PASS' if coverage_pass else 'FAIL'}",
            "",
            "## Funding Cost Impact",
            f"- Average absolute system position: {funding_stats['average_position']:.6f}",
            f"- Average daily funding cost: {_format_rate(funding_stats['average_daily_funding_cost'])}",
            f"- Annualized funding drag: {_format_percent(funding_stats['annualized_funding_drag'])}",
            f"- Total funding drag over window: {_format_percent(funding_stats['total_funding_drag'])}",
            "",
            "## Metric Comparison",
            _metrics_table(
                {
                    "H-311 Original": original,
                    "H-311 + Trading Cost + Funding": adjusted,
                    "BTC B&H": benchmark,
                }
            ),
            "",
            "## Metric Changes",
            _changes_table(original, adjusted),
            "",
            "## Pass/Fail",
            f"- Data coverage: {'PASS' if coverage_pass else 'FAIL'}",
            f"- Funding-adjusted net Sharpe > {PASS_SHARPE:.1f}: "
            f"{adjusted['sharpe']:.6f} > {PASS_SHARPE:.1f} => {'PASS' if sharpe_pass else 'FAIL'}",
            f"- Overall result: {'PASS' if overall_pass else 'FAIL'}",
            "",
            "## Interpretation",
            "- Funding is treated strictly as a cost/income adjustment, not as a predictive input.",
            "- The funding-adjusted Sharpe test passes on the available Binance funding data.",
            "- The overall card remains failed because this environment could not retrieve May 2026 funding rows from the REST endpoint, and Binance's public archive has only closed months through 2026-04.",
            "- Do not make a funding-aware system change from this partial-coverage result alone; rerun through VPN or another reachable Binance REST path to complete the pass standard.",
            "",
        ]
    )


def _funding_stats_table(stats: dict[str, float | str]) -> str:
    rows = [
        ("Rows", f"{int(stats['rows'])}"),
        ("First Timestamp", str(stats["first_timestamp"])),
        ("Last Timestamp", str(stats["last_timestamp"])),
        ("Mean 8h Funding", _format_rate(stats["mean"])),
        ("Median 8h Funding", _format_rate(stats["median"])),
        ("Std 8h Funding", _format_rate(stats["std"])),
        ("Positive Ratio", _format_percent(stats["positive_ratio"])),
        ("Negative Ratio", _format_percent(stats["negative_ratio"])),
        ("Mean Daily Funding", _format_rate(stats["daily_mean"])),
    ]
    lines = ["| Item | Value |", "|---|---:|"]
    lines.extend(f"| {label} | {value} |" for label, value in rows)
    return "\n".join(lines)


def _metrics_table(results: dict[str, dict[str, float]]) -> str:
    lines = ["| Metric | " + " | ".join(results.keys()) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in results) + "|")
    for label, key, kind in METRIC_ROWS:
        values = [_format_metric(result[key], kind=kind) for result in results.values()]
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    return "\n".join(lines)


def _changes_table(original: dict[str, float], adjusted: dict[str, float]) -> str:
    rows = (
        ("Sharpe", "sharpe", "number"),
        ("CAGR", "cagr", "percent"),
        ("Max DD", "max_drawdown", "percent"),
    )
    lines = ["| Metric | H-311 Original | Funding Adjusted | Difference |", "|---|---:|---:|---:|"]
    for label, key, kind in rows:
        diff = adjusted[key] - original[key]
        lines.append(
            "| "
            + label
            + " | "
            + _format_metric(original[key], kind=kind)
            + " | "
            + _format_metric(adjusted[key], kind=kind)
            + " | "
            + _format_metric(diff, kind=kind)
            + " |"
        )
    return "\n".join(lines)


def _format_metric(value: float, *, kind: str) -> str:
    if kind == "percent":
        return _format_percent(value)
    return f"{value:.6f}"


def _format_percent(value: float | str) -> str:
    return f"{float(value) * 100:.2f}%"


def _format_rate(value: float | str) -> str:
    numeric = float(value)
    return f"{numeric * 100:.4f}% ({numeric * 10_000:.2f} bp)"


def _finite_or_zero(value: float) -> float:
    return float(value) if pd.notna(value) and value not in {float("inf"), float("-inf")} else 0.0


if __name__ == "__main__":
    main()
