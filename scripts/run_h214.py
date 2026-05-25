from __future__ import annotations

import argparse
import itertools
import sys
from dataclasses import dataclass
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
EXPECTED_H213_ROWS = 611


@dataclass(frozen=True)
class WindowMetrics:
    name: str
    forecasts: pd.DataFrame
    pearson: pd.DataFrame
    spearman: pd.DataFrame
    signed_n_eff: float
    absolute_n_eff: float
    pca: pd.Series
    pca_90: int
    sharpe: pd.Series


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-214 signal-relation temporal stability measurement.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report-date", default=date.today().isoformat())
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h214-temporal-stability-{args.report_date}.md"
    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    full_forecasts = build_forecasts(price)
    if len(full_forecasts) != EXPECTED_H213_ROWS:
        raise ValueError(f"expected {EXPECTED_H213_ROWS} H-213 aligned rows, got {len(full_forecasts)}")

    first_forecasts, second_forecasts = split_forecasts(full_forecasts)
    windows = [
        measure_window("First Half", first_forecasts, price=price),
        measure_window("Second Half", second_forecasts, price=price),
        measure_window("Full H-213 Window", full_forecasts, price=price),
    ]

    pair_differences = pairwise_pearson_differences(windows[0].pearson, windows[1].pearson)
    report = render_report(
        price=price,
        windows=windows,
        pair_differences=pair_differences,
        price_csv=args.price_csv,
        output_path=output_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"full_rows={len(full_forecasts)}")
    print(f"first_rows={len(first_forecasts)}")
    print(f"second_rows={len(second_forecasts)}")
    print(f"max_pair_abs_corr_delta={pair_differences['abs_delta'].max():.6f}")


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


def split_forecasts(forecasts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    midpoint = len(forecasts) // 2
    return forecasts.iloc[:midpoint].copy(), forecasts.iloc[midpoint:].copy()


def measure_window(name: str, forecasts: pd.DataFrame, *, price: pd.Series) -> WindowMetrics:
    pearson = pairwise_correlation(forecasts, method="pearson")
    spearman = pairwise_correlation(forecasts, method="spearman")
    pca = pca_explained_variance(forecasts)
    return WindowMetrics(
        name=name,
        forecasts=forecasts,
        pearson=pearson,
        spearman=spearman,
        signed_n_eff=effective_n_bets(pearson),
        absolute_n_eff=absolute_correlation_n_eff(pearson),
        pca=pca,
        pca_90=effective_dimension_threshold(pca, threshold=0.9),
        sharpe=standalone_sharpes(price=price, forecasts=forecasts),
    )


def standalone_sharpes(*, price: pd.Series, forecasts: pd.DataFrame) -> pd.Series:
    next_return = price.pct_change().shift(-1).reindex(forecasts.index)
    if len(next_return) > 0:
        next_return.iloc[-1] = pd.NA
    return pd.Series(
        {
            signal: signal_standalone_sharpe(forecasts[signal], next_return, periods_per_year=365)
            for signal in forecasts.columns
        },
        name="standalone_sharpe",
    )


def pairwise_pearson_differences(first: pd.DataFrame, second: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for left, right in itertools.combinations(first.columns, 2):
        first_value = float(first.loc[left, right])
        second_value = float(second.loc[left, right])
        rows.append(
            {
                "pair": f"{left} / {right}",
                "first": first_value,
                "second": second_value,
                "delta": second_value - first_value,
                "abs_delta": abs(first_value - second_value),
            }
        )
    return pd.DataFrame(rows).sort_values("abs_delta", ascending=False).reset_index(drop=True)


def render_report(
    *,
    price: pd.Series,
    windows: list[WindowMetrics],
    pair_differences: pd.DataFrame,
    price_csv: Path,
    output_path: Path,
) -> str:
    first, second, full = windows
    return "\n".join(
        [
            "# H-214 Signal Relation Temporal Stability",
            "",
            "## Metadata",
            "- Measurement type: methodology robustness check, not alpha hypothesis",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            "- Signal set: H-213 six expanding-normalized forecasts",
            "- Data policy: local data only; no new data downloaded",
            f"- Price source: `{price_csv.as_posix()}`",
            f"- Price window: {price.index.min().date().isoformat()} ~ {price.index.max().date().isoformat()}",
            f"- Full aligned window: {full.forecasts.index.min().date().isoformat()} ~ {full.forecasts.index.max().date().isoformat()}",
            f"- Full aligned rows: {len(full.forecasts)}",
            f"- First half: {first.forecasts.index.min().date().isoformat()} ~ {first.forecasts.index.max().date().isoformat()} ({len(first.forecasts)} rows)",
            f"- Second half: {second.forecasts.index.min().date().isoformat()} ~ {second.forecasts.index.max().date().isoformat()} ({len(second.forecasts)} rows)",
            f"- Output: `{output_path.as_posix()}`",
            "",
            "## Summary Metrics",
            _summary_metrics_to_markdown(windows),
            "",
            "## Pearson Matrices",
            "### First Half",
            _matrix_to_markdown(first.pearson),
            "",
            "### Second Half",
            _matrix_to_markdown(second.pearson),
            "",
            "### Full H-213 Window",
            _matrix_to_markdown(full.pearson),
            "",
            "## Spearman Matrices",
            "### First Half",
            _matrix_to_markdown(first.spearman),
            "",
            "### Second Half",
            _matrix_to_markdown(second.spearman),
            "",
            "### Full H-213 Window",
            _matrix_to_markdown(full.spearman),
            "",
            "## Pairwise Pearson Correlation Difference",
            _pair_differences_to_markdown(pair_differences),
            "",
            "## Standalone Sharpe Comparison",
            _aligned_series_to_markdown(
                {"First Half": first.sharpe, "Second Half": second.sharpe, "Full H-213 Window": full.sharpe}
            ),
            "",
            "## PCA Explained Variance Comparison",
            _aligned_series_to_markdown(
                {"First Half": first.pca, "Second Half": second.pca, "Full H-213 Window": full.pca}
            ),
            "",
            "## Interpretation",
            _interpretation(pair_differences),
            "",
        ]
    )


def _summary_metrics_to_markdown(windows: list[WindowMetrics]) -> str:
    lines = [
        "| Window | Rows | Start | End | Signed N_eff | Absolute-Corr N_eff | PCA 90% Components |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for window in windows:
        lines.append(
            f"| {window.name} | {len(window.forecasts)} | {window.forecasts.index.min().date().isoformat()} | "
            f"{window.forecasts.index.max().date().isoformat()} | {window.signed_n_eff:.6f} | "
            f"{window.absolute_n_eff:.6f} | {window.pca_90} |"
        )
    return "\n".join(lines)


def _matrix_to_markdown(matrix: pd.DataFrame) -> str:
    rounded = matrix.round(6)
    lines = ["| Signal | " + " | ".join(rounded.columns) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in rounded.columns) + "|")
    for index, row in rounded.iterrows():
        lines.append("| " + str(index) + " | " + " | ".join(f"{value:.6f}" for value in row) + " |")
    return "\n".join(lines)


def _pair_differences_to_markdown(differences: pd.DataFrame) -> str:
    lines = ["| Pair | First Pearson | Second Pearson | Second - First | Abs Delta |", "|---|---:|---:|---:|---:|"]
    for row in differences.itertuples(index=False):
        lines.append(
            f"| {row.pair} | {row.first:.6f} | {row.second:.6f} | {row.delta:.6f} | {row.abs_delta:.6f} |"
        )
    return "\n".join(lines)


def _aligned_series_to_markdown(series_by_name: dict[str, pd.Series]) -> str:
    item_index = list(next(iter(series_by_name.values())).index)
    lines = ["| Item | " + " | ".join(series_by_name) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in series_by_name) + "|")
    for item in item_index:
        values = [series_by_name[name].loc[item] for name in series_by_name]
        lines.append("| " + str(item) + " | " + " | ".join(f"{float(value):.6f}" for value in values) + " |")
    return "\n".join(lines)


def _interpretation(pair_differences: pd.DataFrame) -> str:
    lower_drift = pair_differences.sort_values("abs_delta", ascending=True).head(3)
    higher_drift = pair_differences.head(3)
    lower_text = ", ".join(f"{row.pair} ({row.abs_delta:.3f})" for row in lower_drift.itertuples(index=False))
    higher_text = ", ".join(f"{row.pair} ({row.abs_delta:.3f})" for row in higher_drift.itertuples(index=False))
    return (
        "This robustness check reports subwindow differences without making an overall stable/unstable call. "
        f"The lowest Pearson absolute-delta relationship candidates are {lower_text}. "
        f"The highest Pearson absolute-delta relationship candidates are {higher_text}. "
        "Use the tables above for Cascade review of whether those differences are economically meaningful; "
        "this card does not accept, reject, or modify any signal."
    )


if __name__ == "__main__":
    main()
