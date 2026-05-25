from __future__ import annotations

import argparse
import itertools
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from trading_learning.metrics.diversification import effective_n_bets, pairwise_correlation  # noqa: E402
from trading_learning.signals.forecast_library import (  # noqa: E402
    sig_breakout,
    sig_mean_rev,
    sig_momentum,
    sig_trend_fast,
    sig_trend_slow,
    sig_vol_regime,
)

SIGNAL_BUILDERS = {
    "SIG_TREND_FAST": lambda price: sig_trend_fast(price, normalization="rolling"),
    "SIG_TREND_SLOW": lambda price: sig_trend_slow(price, normalization="rolling"),
    "SIG_BREAKOUT": lambda price: sig_breakout(price, normalization="rolling"),
    "SIG_MEAN_REV": lambda price: sig_mean_rev(price, normalization="rolling"),
    "SIG_MOMENTUM": lambda price: sig_momentum(price, normalization="rolling"),
    "SIG_VOL_REGIME": lambda price: sig_vol_regime(price, normalization="rolling"),
}

DEFAULT_PRICE_CSV = REPO_ROOT / "data" / "local" / "market_data" / "BTCUSDT" / "1d" / "BTCUSDT-1d.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-210 BTC signal-dimension effective N measurement.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report-date", default=date.today().isoformat())
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h210-signal-correlation-N_eff-{args.report_date}.md"
    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = build_forecasts(price)

    pearson = pairwise_correlation(forecasts, method="pearson")
    spearman = pairwise_correlation(forecasts, method="spearman")
    n_eff = effective_n_bets(pearson)
    lowest_pairs = lowest_abs_correlations(pearson, count=3)

    report = render_report(
        price=price,
        forecasts=forecasts,
        pearson=pearson,
        spearman=spearman,
        n_eff=n_eff,
        lowest_pairs=lowest_pairs,
        price_csv=args.price_csv,
        output_path=output_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"N_eff={n_eff:.6f}")


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


def lowest_abs_correlations(correlation: pd.DataFrame, *, count: int) -> list[tuple[str, str, float, float]]:
    pairs: list[tuple[str, str, float, float]] = []
    for left, right in itertools.combinations(correlation.columns, 2):
        value = float(correlation.loc[left, right])
        pairs.append((left, right, value, abs(value)))
    return sorted(pairs, key=lambda item: item[3])[:count]


def render_report(
    *,
    price: pd.Series,
    forecasts: pd.DataFrame,
    pearson: pd.DataFrame,
    spearman: pd.DataFrame,
    n_eff: float,
    lowest_pairs: list[tuple[str, str, float, float]],
    price_csv: Path,
    output_path: Path,
) -> str:
    return "\n".join(
        [
            "# H-210 Signal Dimension Effective N Measurement",
            "",
            "## Metadata",
            "- Measurement type: methodology measurement, not alpha hypothesis",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            f"- Price source: `{price_csv.as_posix()}`",
            f"- Price window: {price.index.min().date().isoformat()} ~ {price.index.max().date().isoformat()}",
            f"- Price rows: {len(price)}",
            f"- Aligned forecast window: {forecasts.index.min().date().isoformat()} ~ {forecasts.index.max().date().isoformat()}",
            f"- Aligned forecast rows: {len(forecasts)}",
            f"- Output: `{output_path.as_posix()}`",
            "",
            "## Signal Set",
            "\n".join(f"- {name}" for name in forecasts.columns),
            "",
            "## Pearson Correlation Matrix",
            _matrix_to_markdown(pearson),
            "",
            "## Spearman Correlation Matrix",
            _matrix_to_markdown(spearman),
            "",
            "## Equal-Weight Effective N",
            f"- Equal weights: {', '.join(f'{name}=1/6' for name in forecasts.columns)}",
            f"- N_eff: {n_eff:.6f}",
            "",
            "## Three Lowest Absolute Pearson Correlation Pairs",
            _pairs_to_markdown(lowest_pairs),
            "",
            "## Interpretation",
            _interpretation(pearson=pearson, n_eff=n_eff, lowest_pairs=lowest_pairs),
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


def _pairs_to_markdown(pairs: list[tuple[str, str, float, float]]) -> str:
    lines = ["| Rank | Signal A | Signal B | Pearson | Abs Pearson |", "|---:|---|---|---:|---:|"]
    for rank, (left, right, value, abs_value) in enumerate(pairs, start=1):
        lines.append(f"| {rank} | {left} | {right} | {value:.6f} | {abs_value:.6f} |")
    return "\n".join(lines)


def _interpretation(
    *,
    pearson: pd.DataFrame,
    n_eff: float,
    lowest_pairs: list[tuple[str, str, float, float]],
) -> str:
    off_diagonal = [
        abs(float(pearson.loc[left, right]))
        for left, right in itertools.combinations(pearson.columns, 2)
    ]
    mean_abs_corr = sum(off_diagonal) / len(off_diagonal)
    lowest_names = ", ".join(f"{left}/{right}" for left, right, _, _ in lowest_pairs)
    return (
        f"The six BTCUSDT forecast dimensions have mean absolute Pearson correlation {mean_abs_corr:.3f}, "
        f"which produces an equal-weight N_eff of {n_eff:.2f} versus six nominal signals. "
        f"The least-overlapping pairs by absolute Pearson correlation are {lowest_names}. "
        "This describes the measured signal-dimension structure only; it does not evaluate expected returns, "
        "transaction costs, capacity, or whether any signal should be traded."
    )


if __name__ == "__main__":
    main()
