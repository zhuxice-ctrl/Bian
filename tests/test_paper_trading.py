import json

import pandas as pd
import pytest

from trading_learning.backtest.engine import backtest_forecast
from trading_learning.paper_trading.daily_runner import run_backfill, run_daily
from trading_learning.paper_trading.position_tracker import PaperPortfolio
from trading_learning.paper_trading.signal_generator import DailySignals, generate_signal_frame, generate_signals
from trading_learning.signals.forecast_library import (
    ewmac_forecast,
    mean_reversion_forecast,
    momentum_forecast,
    vol_regime_forecast,
)


def test_signal_generator_matches_forecast_library(tmp_path):
    price_csv = _write_price_csv(tmp_path, _sample_prices())
    fdm = 1.75

    signals = generate_signals(price_csv, fdm=fdm)
    price = _load_price(price_csv)
    price = price.loc[price.index >= price.index.max() - pd.DateOffset(years=2)]
    expected_forecasts = pd.DataFrame(
        {
            "SIG_TREND_FAST": ewmac_forecast(
                price, fast_span=8, slow_span=32, normalization="expanding"
            ).rename("SIG_TREND_FAST"),
            "SIG_MOMENTUM": momentum_forecast(price, lookback=60, normalization="expanding").rename("SIG_MOMENTUM"),
            "SIG_MEAN_REV": mean_reversion_forecast(price, window=20, normalization="expanding").rename("SIG_MEAN_REV"),
            "SIG_VOL_REGIME": vol_regime_forecast(price, vol_window=60, normalization="expanding").rename(
                "SIG_VOL_REGIME"
            ),
        }
    ).dropna(how="any")
    latest = expected_forecasts.iloc[-1]
    expected_combined = float((latest.mean() * fdm).clip(-2.0, 2.0))
    aligned_price = price.reindex(expected_forecasts.index)
    expected_vol = float(aligned_price.pct_change().fillna(0.0).ewm(span=60, adjust=False).std().iloc[-1] * (365 ** 0.5))

    assert signals.date == expected_forecasts.index[-1].date().isoformat()
    assert signals.price == pytest.approx(float(aligned_price.iloc[-1]))
    assert signals.sig_trend_fast == pytest.approx(float(latest["SIG_TREND_FAST"]))
    assert signals.sig_momentum == pytest.approx(float(latest["SIG_MOMENTUM"]))
    assert signals.sig_mean_rev == pytest.approx(float(latest["SIG_MEAN_REV"]))
    assert signals.sig_vol_regime == pytest.approx(float(latest["SIG_VOL_REGIME"]))
    assert signals.combined_forecast == pytest.approx(expected_combined)
    assert signals.fdm == pytest.approx(fdm)
    assert signals.instrument_vol == pytest.approx(expected_vol)


def test_position_tracker_updates_three_day_pnl_by_hand():
    portfolio = PaperPortfolio(capital=100_000, cost_per_rt=0.002, target_vol=0.20, max_leverage=2.0)
    day_one = DailySignals("2026-01-01", 100.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.20)
    day_two = DailySignals("2026-01-02", 110.0, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 0.20)
    day_three = DailySignals("2026-01-03", 99.0, 0.0, 0.0, 0.0, 0.0, -0.5, 1.0, 0.20)

    state_one = portfolio.update(day_one)
    state_two = portfolio.update(day_two)
    state_three = portfolio.update(day_three)

    assert state_one.target_position == pytest.approx(1.0)
    assert state_one.current_position == pytest.approx(0.0)
    assert state_one.estimated_cost == pytest.approx(0.002)
    assert state_one.daily_pnl == pytest.approx(-0.002)
    assert state_one.equity == pytest.approx(99_800.0)
    assert state_two.current_position == pytest.approx(1.0)
    assert state_two.target_position == pytest.approx(0.5)
    assert state_two.estimated_cost == pytest.approx(0.001)
    assert state_two.daily_pnl == pytest.approx(0.099)
    assert state_two.equity == pytest.approx(99_800.0 * 1.099)
    assert state_three.current_position == pytest.approx(0.5)
    assert state_three.target_position == pytest.approx(-0.5)
    assert state_three.estimated_cost == pytest.approx(0.002)
    assert state_three.daily_pnl == pytest.approx(-0.052)


def test_backfill_matches_backtest_forecast(tmp_path):
    price_csv = _write_price_csv(tmp_path, _sample_prices())
    state_dir = tmp_path / "paper"
    fdm = 2.0

    portfolio = run_backfill(price_csv=price_csv, state_dir=state_dir, fdm=fdm, capital=100_000, verbose=False)
    signal_frame = generate_signal_frame(price_csv, fdm=fdm)
    backtest = backtest_forecast(
        signal_frame["combined"],
        signal_frame["price"],
        target_vol=0.20,
        vol_lookback=60,
        cost_per_round_trip=0.002,
        capital=100_000,
        max_leverage=2.0,
        periods_per_year=365,
    )

    assert portfolio.get_history()["equity"].iloc[-1] == pytest.approx(backtest.equity_curve.iloc[-1], rel=0.0001)


def test_save_load_roundtrip_preserves_history(tmp_path):
    portfolio = PaperPortfolio(capital=100_000)
    portfolio.update(DailySignals("2026-01-01", 100.0, 0.1, 0.2, -0.1, 0.0, 0.2, 2.0, 0.20))
    path = tmp_path / "portfolio_state.csv"

    portfolio.save(path)
    loaded = PaperPortfolio.load(path)

    pd.testing.assert_frame_equal(loaded.get_history(), portfolio.get_history())


def test_run_daily_writes_state_signals_and_config(tmp_path):
    price_csv = _write_price_csv(tmp_path, _sample_prices())
    state_dir = tmp_path / "paper"

    state = run_daily(price_csv=price_csv, state_dir=state_dir, fdm=2.0, capital=100_000, verbose=False)

    assert state.equity > 0.0
    assert (state_dir / "portfolio_state.csv").exists()
    assert (state_dir / "latest_signals.json").exists()
    assert (state_dir / "config.json").exists()
    config = json.loads((state_dir / "config.json").read_text(encoding="utf-8"))
    assert config["fdm"] == pytest.approx(2.0)


def test_empty_price_csv_raises_clear_error(tmp_path):
    price_csv = tmp_path / "empty.csv"
    price_csv.write_text("opened_at,close\n", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        generate_signals(price_csv)


def _sample_prices() -> pd.Series:
    index = pd.date_range("2024-01-01", periods=760, freq="D", tz="UTC")
    returns = pd.Series([0.001 + ((i % 17) - 8) * 0.0002 for i in range(len(index))], index=index)
    return (100.0 * (1.0 + returns).cumprod()).rename("close")


def _write_price_csv(tmp_path, price: pd.Series) -> str:
    frame = pd.DataFrame({"opened_at": price.index, "close": price.values})
    path = tmp_path / "BTCUSDT-1d.csv"
    frame.to_csv(path, index=False)
    return str(path)


def _load_price(path: str) -> pd.Series:
    frame = pd.read_csv(path, usecols=["opened_at", "close"])
    frame["opened_at"] = pd.to_datetime(frame["opened_at"], utc=True)
    return frame.set_index("opened_at")["close"].astype(float).rename("BTCUSDT")
