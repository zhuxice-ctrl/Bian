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

from trading_learning.metrics.diversification import (  # noqa: E402
    effective_n_bets,
    pairwise_correlation,
    rolling_correlation,
)

SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT")
INTERVAL = "1d"
ROLLING_WINDOW = 90


def main() -> None:
    parser = argparse.ArgumentParser(description="Run H-209 crypto instrument diversification measurement.")
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / "data" / "local" / "market_data")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report-date", default=date.today().isoformat())
    args = parser.parse_args()

    output_path = args.output or REPO_ROOT / "exports" / f"ablation-h209-correlation-N_eff-{args.report_date}.md"
    prices = load_close_prices(args.data_root)
    returns = prices.pct_change().dropna(how="any")
    returns = returns.loc[returns.index >= returns.index.max() - pd.DateOffset(years=2)]

    pearson = pairwise_correlation(returns, method="pearson")
    spearman = pairwise_correlation(returns, method="spearman")
    n_eff = effective_n_bets(pearson)
    rolling = pd.DataFrame(
        {
            f"BTCUSDT_vs_{symbol}": rolling_correlation(returns["BTCUSDT"], returns[symbol], window=ROLLING_WINDOW)
            for symbol in SYMBOLS
            if symbol != "BTCUSDT"
        }
    ).dropna(how="any")

    report = render_report(
        returns=returns,
        pearson=pearson,
        spearman=spearman,
        n_eff=n_eff,
        rolling=rolling,
        output_path=output_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"N_eff={n_eff:.6f}")


def load_close_prices(data_root: Path) -> pd.DataFrame:
    series_by_symbol = {}
    for symbol in SYMBOLS:
        csv_path = data_root / symbol / INTERVAL / f"{symbol}-{INTERVAL}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(str(csv_path))
        frame = pd.read_csv(csv_path, usecols=["opened_at", "close"])
        frame["opened_at"] = pd.to_datetime(frame["opened_at"], utc=True)
        frame = frame.sort_values("opened_at").drop_duplicates(subset=["opened_at"], keep="last")
        series_by_symbol[symbol] = frame.set_index("opened_at")["close"].astype(float).rename(symbol)
    prices = pd.concat(series_by_symbol.values(), axis=1, join="inner").dropna(how="any")
    if prices.empty:
        raise ValueError("no common price rows across H-209 symbols")
    return prices


def render_report(
    *,
    returns: pd.DataFrame,
    pearson: pd.DataFrame,
    spearman: pd.DataFrame,
    n_eff: float,
    rolling: pd.DataFrame,
    output_path: Path,
) -> str:
    return "\n".join(
        [
            "# H-209 Crypto Instrument Effective N Measurement",
            "",
            "## Metadata",
            f"- Symbols: {', '.join(SYMBOLS)}",
            f"- Interval: {INTERVAL}",
            f"- Return window: {returns.index.min().date().isoformat()} ~ {returns.index.max().date().isoformat()}",
            f"- Common return rows: {len(returns)}",
            "- Return definition: close-to-close daily percentage return",
            f"- Output: `{output_path.as_posix()}`",
            "",
            "## Pearson Correlation Matrix",
            _matrix_to_markdown(pearson),
            "",
            "## Spearman Correlation Matrix",
            _matrix_to_markdown(spearman),
            "",
            "## Effective N of Bets",
            f"- Equal weights: {', '.join(f'{symbol}=0.25' for symbol in SYMBOLS)}",
            f"- N_eff: {n_eff:.6f}",
            f"- Interpretation: four nominal crypto instruments currently measure as about {n_eff:.2f} independent equal-weight bets under the Pearson correlation matrix.",
            "",
            f"## Rolling {ROLLING_WINDOW}D Correlation Summary",
            _rolling_summary_to_markdown(rolling),
            "",
            f"## Rolling {ROLLING_WINDOW}D Correlation Time Series",
            _rolling_timeseries_to_markdown(rolling),
            "",
        ]
    )


def _matrix_to_markdown(matrix: pd.DataFrame) -> str:
    rounded = matrix.round(6)
    lines = ["| Symbol | " + " | ".join(rounded.columns) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in rounded.columns) + "|")
    for index, row in rounded.iterrows():
        lines.append("| " + str(index) + " | " + " | ".join(f"{value:.6f}" for value in row) + " |")
    return "\n".join(lines)


def _rolling_summary_to_markdown(rolling: pd.DataFrame) -> str:
    lines = ["| Pair | Mean | Min | Max | Latest |", "|---|---:|---:|---:|---:|"]
    for column in rolling.columns:
        series = rolling[column].dropna()
        lines.append(
            f"| {column} | {series.mean():.6f} | {series.min():.6f} | {series.max():.6f} | {series.iloc[-1]:.6f} |"
        )
    return "\n".join(lines)


def _rolling_timeseries_to_markdown(rolling: pd.DataFrame) -> str:
    rounded = rolling.round(6)
    lines = ["| Date | " + " | ".join(rounded.columns) + " |"]
    lines.append("|---|" + "|".join("---:" for _ in rounded.columns) + "|")
    for timestamp, row in rounded.iterrows():
        lines.append("| " + timestamp.date().isoformat() + " | " + " | ".join(f"{value:.6f}" for value in row) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
