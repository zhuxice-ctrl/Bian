from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Candle:
    symbol: str
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Signal:
    symbol: str
    timestamp: datetime
    action: SignalAction
    reason: str


@dataclass(frozen=True)
class Trade:
    external_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    fee: float
    timestamp: datetime
    reason: str


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    starting_cash: float
    ending_cash: float
    position_quantity: float
    trade_count: int
    trades: tuple[Trade, ...]
