from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from trading_learning.metrics.dimension_analysis import (  # noqa: E402
    absolute_correlation_n_eff,
    effective_dimension_threshold,
    pca_explained_variance,
)
from trading_learning.metrics.diversification import effective_n_bets, pairwise_correlation  # noqa: E402
from trading_learning.signals.forecast_library import (  # noqa: E402
    sig_breakout,
    sig_mean_rev,
    sig_momentum,
    sig_trend_fast,
    sig_trend_slow,
    sig_vol_regime,
)
from trading_learning.signals.standalone_sharpe import signal_standalone_sharpe  # noqa: E402

SIGNAL_BUILDERS = {
    "SIG_TREND_FAST": lambda price: sig_trend_fast(price, normalization="expanding"),
    "SIG_TREND_SLOW": lambda price: sig_trend_slow(price, normalization="expanding"),
    "SIG_BREAKOUT": lambda price: sig_breakout(price, normalization="expanding"),
    "SIG_MEAN_REV": lambda price: sig_mean_rev(price, normalization="expanding"),
    "SIG_MOMENTUM": lambda price: sig_momentum(price, normalization="expanding"),
    "SIG_VOL_REGIME": lambda price: sig_vol_regime(price, normalization="expanding"),
}

DEFAULT_PRICE_CSV = REPO_ROOT / "data" / "local" / "market_data" / "BTCUSDT" / "1d" / "BTCUSDT-1d.csv"
H210_REPORT = REPO_ROOT / "exports" / "ablation-h210-signal-correlation-N_eff-2026-05-25.md"
H210_SIGNED_N_EFF = 10.703608
H210_ALIGNED_ROWS = 168
H210_ALIGNED_WINDOW = "2025-12-06 ~ 2026-05-22"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-213 signal-dimension methodology upgrade measurement.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report-date", default=date.today().isoformat())
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h213-methodology-upgrade-{args.report_date}.md"
    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = build_forecasts(price)
    if len(forecasts) <= 600:
        raise ValueError(f"H-213 expected more than 600 aligned forecast rows, got {len(forecasts)}")

    pearson = pairwise_correlation(forecasts, method="pearson")
    spearman = pairwise_correlation(forecasts, method="spearman")
    signed_n_eff = effective_n_bets(pearson)
    absolute_n_eff = absolute_correlation_n_eff(pearson)
    pca = pca_explained_variance(forecasts)
    pca_90 = effective_dimension_threshold(pca, threshold=0.9)
    sharpe = standalone_sharpes(price=price, forecasts=forecasts)

    report = render_report(
        price=price,
        forecasts=forecasts,
        pearson=pearson,
        spearman=spearman,
        signed_n_eff=signed_n_eff,
        absolute_n_eff=absolute_n_eff,
        pca=pca,
        pca_90=pca_90,
        sharpe=sharpe,
        price_csv=args.price_csv,
        output_path=output_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"aligned_rows={len(forecasts)}")
    print(f"signed_N_eff={signed_n_eff:.6f}")
    print(f"absolute_correlation_N_eff={absolute_n_eff:.6f}")
    print(f"pca_90_components={pca_90}")


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
    forecasts = pd.DataFrame({name: builder(price) for name, builder in SIGNAL_BUILDERS.items()})
    aligned = forecasts.dropna(how="any")
    if aligned.empty:
        raise ValueError("no aligned non-null forecast rows")
    return aligned


def standalone_sharpes(*, price: pd.Series, forecasts: pd.DataFrame) -> pd.Series:
    next_return = price.pct_change().shift(-1).rename("next_return")
    values = {
        signal: signal_standalone_sharpe(forecasts[signal], next_return, periods_per_year=365)
        for signal in forecasts.columns
    }
    return pd.Series(values, name="standalone_sharpe")


def render_report(
    *,
    price: pd.Series,
    forecasts: pd.DataFrame,
    pearson: pd.DataFrame,
    spearman: pd.DataFrame,
    signed_n_eff: float,
    absolute_n_eff: float,
    pca: pd.Series,
    pca_90: int,
    sharpe: pd.Series,
    price_csv: Path,
    output_path: Path,
) -> str:
    return "\n".join(
        [
            "# H-213 Signal Dimension Methodology Upgrade",
            "",
            "## Metadata",
            "- Measurement type: methodology correction, not alpha hypothesis",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            "- Data policy: local data only; no new data downloaded",
            f"- Price source: `{price_csv.as_posix()}`",
            f"- Price window: {price.index.min().date().isoformat()} ~ {price.index.max().date().isoformat()}",
            f"- Price rows: {len(price)}",
            "- Signal definitions: same six H-210 price-derived forecasts",
            "- Normalization: expanding mean absolute signal, available from day 60",
            f"- Aligned forecast window: {forecasts.index.min().date().isoformat()} ~ {forecasts.index.max().date().isoformat()}",
            f"- Aligned forecast rows: {len(forecasts)}",
            f"- H-210 report retained at: `{H210_REPORT.as_posix()}`",
            f"- Output: `{output_path.as_posix()}`",
            "",
            "## Pearson Correlation Matrix",
            _matrix_to_markdown(pearson),
            "",
            "## Spearman Correlation Matrix",
            _matrix_to_markdown(spearman),
            "",
            "## Effective N Estimates",
            f"- Signed equal-weight N_eff: {signed_n_eff:.6f}",
            f"- Absolute-correlation equal-weight N_eff: {absolute_n_eff:.6f}",
            "",
            "## PCA Explained Variance",
            _series_to_markdown(pca, value_name="Explained Variance"),
            "",
            "## Effective Dimension Threshold",
            f"- Threshold: 90% cumulative explained variance",
            f"- Components required: {pca_90}",
            "",
            "## Standalone Sharpe by Signal",
            _series_to_markdown(sharpe, value_name="Standalone Sharpe"),
            "",
            "## H-210 vs H-213 Comparison",
            _comparison_to_markdown(
                signed_n_eff=signed_n_eff,
                absolute_n_eff=absolute_n_eff,
                pca_90=pca_90,
                h213_rows=len(forecasts),
                h213_window=f"{forecasts.index.min().date().isoformat()} ~ {forecasts.index.max().date().isoformat()}",
            ),
            "",
            "## Interpretation",
            _interpretation(signed_n_eff=signed_n_eff, absolute_n_eff=absolute_n_eff, pca_90=pca_90),
            "",
        ]
    )


def _matrix_to_markdown(matrix: pd.DataFrame) -> str:
    rounded = matrix.round(6)
    lines = ["| Signal | " + " | ".join(rounded.columns) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in rounded.columns) + "|")
    for index, row in rounded.iterrows():
        lines.append("| " + str(index) + " | " + " | ".join(f"{value:.6f}" for value in row) + " |")
    return "\n".join(lines)


def _series_to_markdown(series: pd.Series, *, value_name: str) -> str:
    lines = [f"| Item | {value_name} |", "|---|---:|"]
    for index, value in series.items():
        lines.append(f"| {index} | {float(value):.6f} |")
    return "\n".join(lines)


def _comparison_to_markdown(
    *,
    signed_n_eff: float,
    absolute_n_eff: float,
    pca_90: int,
    h213_rows: int,
    h213_window: str,
) -> str:
    lines = ["| Measurement | Window | Rows | Estimate Type | Value |", "|---|---|---:|---|---:|"]
    lines.append(f"| H-210 published | {H210_ALIGNED_WINDOW} | {H210_ALIGNED_ROWS} | signed N_eff | {H210_SIGNED_N_EFF:.6f} |")
    lines.append(f"| H-213 upgraded | {h213_window} | {h213_rows} | signed N_eff | {signed_n_eff:.6f} |")
    lines.append(f"| H-213 upgraded | {h213_window} | {h213_rows} | absolute-correlation N_eff | {absolute_n_eff:.6f} |")
    lines.append(f"| H-213 upgraded | {h213_window} | {h213_rows} | PCA 90% components | {pca_90:.0f} |")
    return "\n".join(lines)


def _interpretation(*, signed_n_eff: float, absolute_n_eff: float, pca_90: int) -> str:
    return (
        "H-210's 10.7 was pushed up by a negative-correlation artifact: the signed formula counted "
        "structural negative correlation as if it were additional independent breadth, especially between "
        "trend-like and mean-reversion-like forecasts in a short 168-day reversal window. "
        f"With expanding normalization, the aligned window is much longer and the signed risk-diversification "
        f"estimate is {signed_n_eff:.2f}, while the absolute-correlation estimate is {absolute_n_eff:.2f} "
        f"and PCA needs {pca_90} components to explain 90% of forecast variance. "
        f"In this upgraded window, the credible structural dimension estimate is therefore not one number: "
        f"signed risk dimension is {signed_n_eff:.2f}, no-hedge absolute-correlation dimension is "
        f"{absolute_n_eff:.2f}, and PCA 90% dimension is {pca_90}. "
        "Risk diversification and alpha diversification are different concepts: negative correlation can reduce "
        "portfolio risk, but it does not prove that a mechanically opposite forecast is an independent alpha source. "
        "Standalone Sharpe is reported only as a descriptive, no-cost alpha diagnostic; no signal is accepted, "
        "rejected, or removed by this card."
    )


if __name__ == "__main__":
    main()
