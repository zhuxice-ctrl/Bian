from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from trading_learning.backtest.engine import compute_fdm
from trading_learning.signals.forecast_library import (
    ewmac_forecast,
    mean_reversion_forecast,
    momentum_forecast,
    vol_regime_forecast,
)

DEFAULT_FDM = 2.753598
DEFAULT_VOL_LOOKBACK = 60
DEFAULT_PERIODS_PER_YEAR = 365
DEFAULT_FORECAST_CAP = 2.0


@dataclass(frozen=True)
class DailySignals:
    date: str
    price: float
    sig_trend_fast: float
    sig_momentum: float
    sig_mean_rev: float
    sig_vol_regime: float
    combined_forecast: float
    fdm: float
    instrument_vol: float

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


def generate_signals(
    price_csv: str | Path,
    fdm: float | None = None,
) -> DailySignals:
    """Read latest BTCUSDT daily data and return the most recent paper-trading signals."""
    frame = generate_signal_frame(price_csv, fdm=fdm)
    if frame.empty:
        raise ValueError("signal frame is empty")
    latest = frame.iloc[-1]
    return DailySignals(
        date=frame.index[-1].date().isoformat(),
        price=float(latest["price"]),
        sig_trend_fast=float(latest["sig_fast"]),
        sig_momentum=float(latest["sig_mom"]),
        sig_mean_rev=float(latest["sig_mr"]),
        sig_vol_regime=float(latest["sig_vol"]),
        combined_forecast=float(latest["combined"]),
        fdm=float(latest["fdm"]),
        instrument_vol=float(latest["inst_vol"]),
    )


def generate_signal_frame(
    price_csv: str | Path,
    fdm: float | None = None,
    *,
    vol_lookback: int = DEFAULT_VOL_LOOKBACK,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
    forecast_cap: float = DEFAULT_FORECAST_CAP,
) -> pd.DataFrame:
    """Return the aligned daily signal frame used by paper trading and backfill."""
    price = load_close_price(price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    forecasts = pd.DataFrame(
        {
            "sig_fast": ewmac_forecast(price, fast_span=8, slow_span=32, normalization="expanding").rename("sig_fast"),
            "sig_mom": momentum_forecast(price, lookback=60, normalization="expanding").rename("sig_mom"),
            "sig_mr": mean_reversion_forecast(price, window=20, normalization="expanding").rename("sig_mr"),
            "sig_vol": vol_regime_forecast(price, vol_window=60, normalization="expanding").rename("sig_vol"),
        }
    ).dropna(how="any")
    if forecasts.empty:
        raise ValueError("aligned forecast data is empty")

    fdm_value = compute_fdm(forecasts) if fdm is None else float(fdm)
    aligned_price = price.reindex(forecasts.index)
    instrument_vol = (
        aligned_price.pct_change().fillna(0.0).ewm(span=vol_lookback, adjust=False).std() * np.sqrt(periods_per_year)
    )
    combined = (forecasts.mean(axis=1) * fdm_value).clip(-forecast_cap, forecast_cap)
    return pd.DataFrame(
        {
            "price": aligned_price,
            "sig_fast": forecasts["sig_fast"],
            "sig_mom": forecasts["sig_mom"],
            "sig_mr": forecasts["sig_mr"],
            "sig_vol": forecasts["sig_vol"],
            "combined": combined,
            "fdm": fdm_value,
            "inst_vol": instrument_vol,
        }
    )


def load_close_price(path: str | Path) -> pd.Series:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))
    frame = pd.read_csv(csv_path, usecols=["opened_at", "close"])
    if frame.empty:
        raise ValueError("price data is empty")
    frame["opened_at"] = pd.to_datetime(frame["opened_at"], utc=True)
    frame = frame.sort_values("opened_at").drop_duplicates(subset=["opened_at"], keep="last")
    price = frame.set_index("opened_at")["close"].astype(float).rename("BTCUSDT")
    if price.empty:
        raise ValueError("price data is empty")
    return price
