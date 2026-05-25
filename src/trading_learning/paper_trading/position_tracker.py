from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from trading_learning.paper_trading.signal_generator import DailySignals

DEFAULT_TARGET_VOL = 0.20
DEFAULT_MAX_LEVERAGE = 2.0
STATE_COLUMNS = [
    "date",
    "price",
    "sig_fast",
    "sig_mom",
    "sig_mr",
    "sig_vol",
    "combined",
    "fdm",
    "inst_vol",
    "target_pos",
    "current_pos",
    "change",
    "cost",
    "daily_pnl",
    "cum_pnl",
    "equity",
]


@dataclass(frozen=True)
class PositionState:
    date: str
    target_position: float
    current_position: float
    position_change: float
    estimated_cost: float
    daily_pnl: float
    cumulative_pnl: float
    equity: float

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


class PaperPortfolio:
    def __init__(
        self,
        capital: float = 100_000,
        cost_per_rt: float = 0.002,
        target_vol: float = DEFAULT_TARGET_VOL,
        max_leverage: float = DEFAULT_MAX_LEVERAGE,
        history: pd.DataFrame | None = None,
    ):
        if capital <= 0.0:
            raise ValueError("capital must be positive")
        if cost_per_rt < 0.0:
            raise ValueError("cost_per_rt must be non-negative")
        if target_vol < 0.0:
            raise ValueError("target_vol must be non-negative")
        if max_leverage <= 0.0:
            raise ValueError("max_leverage must be positive")
        self.capital = float(capital)
        self.cost_per_rt = float(cost_per_rt)
        self.target_vol = float(target_vol)
        self.max_leverage = float(max_leverage)
        self._history = _normalize_history(history)

    def update(self, signals: DailySignals) -> PositionState:
        previous = self._history.iloc[-1] if not self._history.empty else None
        current_position = float(previous["target_pos"]) if previous is not None else 0.0
        previous_price = float(previous["price"]) if previous is not None else signals.price
        previous_equity = float(previous["equity"]) if previous is not None else self.capital
        daily_return = 0.0 if previous_price == 0.0 else (signals.price / previous_price) - 1.0
        target_position = _target_position(
            combined_forecast=signals.combined_forecast,
            instrument_vol=signals.instrument_vol,
            target_vol=self.target_vol,
            max_leverage=self.max_leverage,
        )
        position_change = target_position - current_position
        estimated_cost = abs(position_change) * self.cost_per_rt
        daily_pnl = current_position * daily_return - estimated_cost
        equity = previous_equity * (1.0 + daily_pnl)
        cumulative_pnl = equity - self.capital
        state = PositionState(
            date=signals.date,
            target_position=target_position,
            current_position=current_position,
            position_change=position_change,
            estimated_cost=estimated_cost,
            daily_pnl=daily_pnl,
            cumulative_pnl=cumulative_pnl,
            equity=equity,
        )
        record = {
            "date": signals.date,
            "price": signals.price,
            "sig_fast": signals.sig_trend_fast,
            "sig_mom": signals.sig_momentum,
            "sig_mr": signals.sig_mean_rev,
            "sig_vol": signals.sig_vol_regime,
            "combined": signals.combined_forecast,
            "fdm": signals.fdm,
            "inst_vol": signals.instrument_vol,
            "target_pos": state.target_position,
            "current_pos": state.current_position,
            "change": state.position_change,
            "cost": state.estimated_cost,
            "daily_pnl": state.daily_pnl,
            "cum_pnl": state.cumulative_pnl,
            "equity": state.equity,
        }
        if self._history.empty:
            self._history = pd.DataFrame([record], columns=STATE_COLUMNS)
        else:
            self._history = pd.concat([self._history, pd.DataFrame([record], columns=STATE_COLUMNS)], ignore_index=True)
        return state

    def get_history(self) -> pd.DataFrame:
        return self._history.copy()

    def save(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._history.to_csv(output_path, index=False)

    @classmethod
    def load(cls, path: str | Path) -> "PaperPortfolio":
        input_path = Path(path)
        if not input_path.exists():
            return cls()
        history = pd.read_csv(input_path)
        return cls(history=history)


def _target_position(
    *,
    combined_forecast: float,
    instrument_vol: float,
    target_vol: float,
    max_leverage: float,
) -> float:
    if not np.isfinite(instrument_vol) or instrument_vol <= 0.0:
        return 0.0
    raw = combined_forecast * (target_vol / instrument_vol)
    return float(np.clip(raw, -max_leverage, max_leverage))


def _normalize_history(history: pd.DataFrame | None) -> pd.DataFrame:
    if history is None:
        return pd.DataFrame(columns=STATE_COLUMNS)
    normalized = history.copy()
    for column in STATE_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = np.nan
    return normalized.loc[:, STATE_COLUMNS].reset_index(drop=True)
