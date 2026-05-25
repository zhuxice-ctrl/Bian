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

from trading_learning.metrics.diversification import effective_n_bets, pairwise_correlation  # noqa: E402
from trading_learning.signals.forecast_library import (  # noqa: E402
    ewmac_forecast,
    sig_breakout,
    sig_mean_rev,
    sig_momentum,
    sig_trend_fast,
    sig_trend_slow,
    sig_vol_regime,
)

EWMAC_SPEEDS = (
    (2, 8),
    (4, 16),
    (8, 32),
    (16, 64),
    (32, 128),
    (64, 256),
)
CARVER_CLASSIC_SPEEDS = ("EWMAC_8_32", "EWMAC_16_64", "EWMAC_64_256")
H210_SIGNAL_BUILDERS = {
    "SIG_TREND_FAST": lambda price: sig_trend_fast(price, normalization="rolling"),
    "SIG_TREND_SLOW": lambda price: sig_trend_slow(price, normalization="rolling"),
    "SIG_BREAKOUT": lambda price: sig_breakout(price, normalization="rolling"),
    "SIG_MEAN_REV": lambda price: sig_mean_rev(price, normalization="rolling"),
    "SIG_MOMENTUM": lambda price: sig_momentum(price, normalization="rolling"),
    "SIG_VOL_REGIME": lambda price: sig_vol_regime(price, normalization="rolling"),
}
DEFAULT_PRICE_CSV = REPO_ROOT / "data" / "local" / "market_data" / "BTCUSDT" / "1d" / "BTCUSDT-1d.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-212 BTC cross-lookback EWMAC effective N measurement.")
    parser.add_argument("--price-csv", type=Path, default=DEFAULT_PRICE_CSV)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report-date", default=date.today().isoformat())
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h212-cross-lookback-N_eff-{args.report_date}.md"
    price = load_close_price(args.price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]

    ewmac_forecasts = build_ewmac_forecasts(price)
    pearson = pairwise_correlation(ewmac_forecasts, method="pearson")
    all_speed_n_eff = effective_n_bets(pearson)

    carver_pearson = pearson.loc[list(CARVER_CLASSIC_SPEEDS), list(CARVER_CLASSIC_SPEEDS)]
    carver_n_eff = effective_n_bets(carver_pearson)

    h210_forecasts = build_h210_forecasts(price)
    comparison_index = ewmac_forecasts.index.intersection(h210_forecasts.index)
    if comparison_index.empty:
        raise ValueError("no common dates between H-212 and H-210 forecast sets")
    comparison_ewmac = ewmac_forecasts.loc[comparison_index]
    comparison_h210 = h210_forecasts.loc[comparison_index]
    comparison_ewmac_n_eff = effective_n_bets(pairwise_correlation(comparison_ewmac, method="pearson"))
    comparison_h210_n_eff = effective_n_bets(pairwise_correlation(comparison_h210, method="pearson"))

    report = render_report(
        price=price,
        ewmac_forecasts=ewmac_forecasts,
        pearson=pearson,
        all_speed_n_eff=all_speed_n_eff,
        carver_pearson=carver_pearson,
        carver_n_eff=carver_n_eff,
        comparison_ewmac=comparison_ewmac,
        comparison_h210=comparison_h210,
        comparison_ewmac_n_eff=comparison_ewmac_n_eff,
        comparison_h210_n_eff=comparison_h210_n_eff,
        price_csv=args.price_csv,
        output_path=output_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"all_speed_N_eff={all_speed_n_eff:.6f}")
    print(f"carver_three_speed_N_eff={carver_n_eff:.6f}")
    print(f"comparison_ewmac_six_speed_N_eff={comparison_ewmac_n_eff:.6f}")
    print(f"comparison_h210_six_signal_N_eff={comparison_h210_n_eff:.6f}")


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


def build_ewmac_forecasts(price: pd.Series) -> pd.DataFrame:
    forecasts = pd.DataFrame(
        {
            f"EWMAC_{fast}_{slow}": ewmac_forecast(
                price, fast_span=fast, slow_span=slow, normalization="rolling"
            ).rename(f"EWMAC_{fast}_{slow}")
            for fast, slow in EWMAC_SPEEDS
        }
    )
    aligned = forecasts.dropna(how="any")
    if aligned.empty:
        raise ValueError("no aligned non-null EWMAC forecast rows")
    return aligned


def build_h210_forecasts(price: pd.Series) -> pd.DataFrame:
    forecasts = pd.DataFrame({name: builder(price) for name, builder in H210_SIGNAL_BUILDERS.items()})
    aligned = forecasts.dropna(how="any")
    if aligned.empty:
        raise ValueError("no aligned non-null H-210 forecast rows")
    return aligned


def render_report(
    *,
    price: pd.Series,
    ewmac_forecasts: pd.DataFrame,
    pearson: pd.DataFrame,
    all_speed_n_eff: float,
    carver_pearson: pd.DataFrame,
    carver_n_eff: float,
    comparison_ewmac: pd.DataFrame,
    comparison_h210: pd.DataFrame,
    comparison_ewmac_n_eff: float,
    comparison_h210_n_eff: float,
    price_csv: Path,
    output_path: Path,
) -> str:
    return "\n".join(
        [
            "# H-212 Cross-Lookback Effective N Measurement",
            "",
            "## Metadata",
            "- Measurement type: methodology measurement, not alpha hypothesis",
            "- Symbol: BTCUSDT",
            "- Interval: 1d",
            f"- Price source: `{price_csv.as_posix()}`",
            f"- Price window: {price.index.min().date().isoformat()} ~ {price.index.max().date().isoformat()}",
            f"- Price rows: {len(price)}",
            f"- EWMAC aligned forecast window: {ewmac_forecasts.index.min().date().isoformat()} ~ {ewmac_forecasts.index.max().date().isoformat()}",
            f"- EWMAC aligned forecast rows: {len(ewmac_forecasts)}",
            f"- H-210 comparison window: {comparison_h210.index.min().date().isoformat()} ~ {comparison_h210.index.max().date().isoformat()}",
            f"- H-210 comparison rows: {len(comparison_h210)}",
            f"- Output: `{output_path.as_posix()}`",
            "",
            "## Six-Speed Pearson Correlation Matrix",
            _matrix_to_markdown(pearson),
            "",
            "## Equal-Weight Effective N",
            f"- Six EWMAC speeds: {all_speed_n_eff:.6f}",
            f"- Carver classic three-speed subset ({', '.join(CARVER_CLASSIC_SPEEDS)}): {carver_n_eff:.6f}",
            f"- Six EWMAC speeds on the H-210 comparison window: {comparison_ewmac_n_eff:.6f}",
            f"- H-210 six cross-signal dimensions on the same comparison window: {comparison_h210_n_eff:.6f}",
            "",
            "## Carver Three-Speed Pearson Correlation Matrix",
            _matrix_to_markdown(carver_pearson),
            "",
            "## H-210 Comparison",
            _comparison_to_markdown(
                all_speed_n_eff=all_speed_n_eff,
                carver_n_eff=carver_n_eff,
                comparison_ewmac_n_eff=comparison_ewmac_n_eff,
                comparison_h210_n_eff=comparison_h210_n_eff,
            ),
            "",
            "## Interpretation",
            _interpretation(
                comparison_ewmac_n_eff=comparison_ewmac_n_eff,
                comparison_h210_n_eff=comparison_h210_n_eff,
            ),
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


def _comparison_to_markdown(
    *,
    all_speed_n_eff: float,
    carver_n_eff: float,
    comparison_ewmac_n_eff: float,
    comparison_h210_n_eff: float,
) -> str:
    lines = ["| Measurement | Nominal Signals | N_eff |", "|---|---:|---:|"]
    lines.append(f"| H-212 six EWMAC speeds | 6 | {all_speed_n_eff:.6f} |")
    lines.append(f"| H-212 Carver three EWMAC speeds | 3 | {carver_n_eff:.6f} |")
    lines.append(f"| H-212 six EWMAC speeds on H-210 comparison window | 6 | {comparison_ewmac_n_eff:.6f} |")
    lines.append(f"| H-210 six cross-signal dimensions on same comparison window | 6 | {comparison_h210_n_eff:.6f} |")
    return "\n".join(lines)


def _interpretation(*, comparison_ewmac_n_eff: float, comparison_h210_n_eff: float) -> str:
    if comparison_h210_n_eff > comparison_ewmac_n_eff:
        comparison = "the cross-signal H-210 set measured higher diversification than the cross-speed EWMAC set"
    elif comparison_h210_n_eff < comparison_ewmac_n_eff:
        comparison = "the cross-speed EWMAC set measured higher diversification than the cross-signal H-210 set"
    else:
        comparison = "the two six-signal sets measured the same effective N"
    return (
        f"On the shared comparison dates, six EWMAC speeds produced N_eff {comparison_ewmac_n_eff:.2f}, "
        f"while the six H-210 cross-signal dimensions produced N_eff {comparison_h210_n_eff:.2f}; {comparison}. "
        "This is a structural correlation measurement only and does not evaluate returns, costs, capacity, or trading suitability."
    )


if __name__ == "__main__":
    main()
