from __future__ import annotations

import json
from pathlib import Path

from trading_learning.paper_trading.position_tracker import PaperPortfolio, PositionState
from trading_learning.paper_trading.signal_generator import (
    DEFAULT_FDM,
    DEFAULT_FORECAST_CAP,
    DEFAULT_PERIODS_PER_YEAR,
    DEFAULT_VOL_LOOKBACK,
    DailySignals,
    generate_signal_frame,
    generate_signals,
)

DEFAULT_PRICE_CSV = Path("F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv")
DEFAULT_STATE_DIR = Path("F:/Bian/data/paper_trading")
DEFAULT_CAPITAL = 100_000
DEFAULT_COST_PER_RT = 0.002
DEFAULT_TARGET_VOL = 0.20
DEFAULT_MAX_LEVERAGE = 2.0
STATE_FILE = "portfolio_state.csv"
SIGNALS_FILE = "latest_signals.json"
CONFIG_FILE = "config.json"


def run_daily(
    price_csv: str | Path = DEFAULT_PRICE_CSV,
    state_dir: str | Path = DEFAULT_STATE_DIR,
    fdm: float | None = None,
    capital: float = DEFAULT_CAPITAL,
    verbose: bool = True,
) -> PositionState:
    """
    Run one paper-trading cycle: read latest data, generate signals, update state, save files.
    """
    state_path = Path(state_dir)
    state_path.mkdir(parents=True, exist_ok=True)
    fdm_value = _resolve_fdm(state_path, fdm)
    signals = generate_signals(price_csv, fdm=fdm_value)
    portfolio = _load_portfolio(state_path / STATE_FILE, capital=capital)
    state = portfolio.update(signals)
    portfolio.save(state_path / STATE_FILE)
    _write_latest_signals(state_path / SIGNALS_FILE, signals)
    _write_config(state_path / CONFIG_FILE, fdm=fdm_value, capital=capital)
    if verbose:
        print(_summary_line(state))
    return state


def run_backfill(
    price_csv: str | Path = DEFAULT_PRICE_CSV,
    state_dir: str | Path = DEFAULT_STATE_DIR,
    fdm: float | None = DEFAULT_FDM,
    capital: float = DEFAULT_CAPITAL,
    verbose: bool = True,
) -> PaperPortfolio:
    """Backfill the paper-trading state from the H-311 aligned signal window."""
    state_path = Path(state_dir)
    state_path.mkdir(parents=True, exist_ok=True)
    fdm_value = DEFAULT_FDM if fdm is None else float(fdm)
    signal_frame = generate_signal_frame(price_csv, fdm=fdm_value)
    portfolio = PaperPortfolio(
        capital=capital,
        cost_per_rt=DEFAULT_COST_PER_RT,
        target_vol=DEFAULT_TARGET_VOL,
        max_leverage=DEFAULT_MAX_LEVERAGE,
    )
    latest_signals = None
    for timestamp, row in signal_frame.iterrows():
        latest_signals = DailySignals(
            date=timestamp.date().isoformat(),
            price=float(row["price"]),
            sig_trend_fast=float(row["sig_fast"]),
            sig_momentum=float(row["sig_mom"]),
            sig_mean_rev=float(row["sig_mr"]),
            sig_vol_regime=float(row["sig_vol"]),
            combined_forecast=float(row["combined"]),
            fdm=float(row["fdm"]),
            instrument_vol=float(row["inst_vol"]),
        )
        portfolio.update(latest_signals)
    portfolio.save(state_path / STATE_FILE)
    if latest_signals is not None:
        _write_latest_signals(state_path / SIGNALS_FILE, latest_signals)
    _write_config(state_path / CONFIG_FILE, fdm=fdm_value, capital=capital)
    if verbose:
        history = portfolio.get_history()
        print(f"backfilled {len(history)} rows; final_equity={history['equity'].iloc[-1]:.2f}")
    return portfolio


def load_status(state_dir: str | Path = DEFAULT_STATE_DIR, since: str | None = None) -> str:
    state_path = Path(state_dir) / STATE_FILE
    portfolio = PaperPortfolio.load(state_path)
    history = portfolio.get_history()
    if since is not None and not history.empty:
        history = history.loc[history["date"] >= since]
    if history.empty:
        return "No paper trading state found."
    latest = history.iloc[-1]
    return (
        f"date={latest['date']} equity={latest['equity']:.2f} "
        f"cum_pnl={latest['cum_pnl']:.2f} target_pos={latest['target_pos']:.6f}"
    )


def _load_portfolio(path: Path, *, capital: float) -> PaperPortfolio:
    if path.exists():
        loaded = PaperPortfolio.load(path)
        return PaperPortfolio(
            capital=capital,
            cost_per_rt=DEFAULT_COST_PER_RT,
            target_vol=DEFAULT_TARGET_VOL,
            max_leverage=DEFAULT_MAX_LEVERAGE,
            history=loaded.get_history(),
        )
    return PaperPortfolio(
        capital=capital,
        cost_per_rt=DEFAULT_COST_PER_RT,
        target_vol=DEFAULT_TARGET_VOL,
        max_leverage=DEFAULT_MAX_LEVERAGE,
    )


def _resolve_fdm(state_dir: Path, fdm: float | None) -> float:
    if fdm is not None:
        return float(fdm)
    config_path = state_dir / CONFIG_FILE
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if "fdm" in config:
            return float(config["fdm"])
    return DEFAULT_FDM


def _write_latest_signals(path: Path, signals: DailySignals) -> None:
    path.write_text(json.dumps(signals.to_dict(), indent=2), encoding="utf-8")


def _write_config(path: Path, *, fdm: float, capital: float) -> None:
    config = {
        "fdm": fdm,
        "capital": capital,
        "cost_per_round_trip": DEFAULT_COST_PER_RT,
        "target_vol": DEFAULT_TARGET_VOL,
        "vol_lookback": DEFAULT_VOL_LOOKBACK,
        "periods_per_year": DEFAULT_PERIODS_PER_YEAR,
        "max_leverage": DEFAULT_MAX_LEVERAGE,
        "forecast_cap": DEFAULT_FORECAST_CAP,
        "data_update_mode": "manual",
        "feishu_push_enabled": False,
        "feishu_push_chat_id": "",
    }
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _summary_line(state: PositionState) -> str:
    return (
        f"{state.date}: equity={state.equity:.2f}, daily_pnl={state.daily_pnl:.6f}, "
        f"target_pos={state.target_position:.6f}, change={state.position_change:.6f}"
    )
