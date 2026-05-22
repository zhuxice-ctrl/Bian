from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from trading_learning.strategy.indicators import atr, ema, rsi


@dataclass(frozen=True)
class MTFTrendConfig:
    trend_tf: str = "1h"
    pullback_tf: str = "15m"
    trigger_tf: str = "5m"
    ema_long: int = 200
    ema_short: int = 20
    rsi_period: int = 14
    rsi_oversold: float = 35
    atr_period: int = 14
    risk_per_trade: float = 0.005
    stop_atr_mult: float = 2.0
    profit_atr_mult: float = 3.0


_PHASES = {"6.1": 1, "6.2": 2, "6.3": 3, "6.4": 4, "6.5": 5, "6.6": 6}


def generate_mtf_trend_signals(
    frames: dict[str, pd.DataFrame],
    *,
    config: MTFTrendConfig = MTFTrendConfig(),
    phase: str = "6.6",
) -> pd.DataFrame:
    phase_level = _phase_level(phase)
    trend = _prepare_frame(frames[config.trend_tf])
    trend["ema_short"] = ema(trend["close"], config.ema_short)
    trend["ema_long"] = ema(trend["close"], config.ema_long)
    trend["atr"] = atr(trend["high"], trend["low"], trend["close"], config.atr_period)

    pullback = _prepare_frame(frames.get(config.pullback_tf, trend))
    pullback["rsi"] = rsi(pullback["close"], config.rsi_period)
    trigger = _prepare_frame(frames.get(config.trigger_tf, trend))
    trigger["ema_short"] = ema(trigger["close"], max(2, min(config.ema_short, len(trigger))))

    rows: list[dict[str, Any]] = []
    for index in range(1, len(trend)):
        current = trend.iloc[index]
        previous = trend.iloc[index - 1]
        if pd.isna(current["ema_short"]) or pd.isna(previous["ema_short"]):
            continue
        baseline_buy = current["close"] > current["ema_short"] and current["close"] > previous["close"]
        if not baseline_buy:
            continue
        reasons = ["1h MA pull-through baseline"]
        if phase_level >= 2:
            if pd.isna(current["ema_long"]) or current["close"] <= current["ema_long"]:
                continue
            reasons.append("above EMA200 trend filter")
        risk_fraction = 1.0
        if phase_level >= 3:
            if pd.isna(current["atr"]) or current["atr"] <= 0:
                continue
            risk_fraction = min(1.0, config.risk_per_trade / ((current["atr"] * config.stop_atr_mult) / current["close"]))
            reasons.append("ATR position sizing")
        if phase_level >= 4:
            recent_pullback = pullback[pullback["opened_at"] <= current["opened_at"]].tail(max(config.rsi_period, 6))
            if recent_pullback.empty:
                continue
            pullback_rsi = recent_pullback["rsi"].min(skipna=True)
            has_price_pullback = recent_pullback["close"].min() < recent_pullback["close"].iloc[-1]
            if not (pd.notna(pullback_rsi) and pullback_rsi <= config.rsi_oversold) and not has_price_pullback:
                continue
            reasons.append("15m RSI pullback")
        if phase_level >= 5:
            latest_trigger = trigger[trigger["opened_at"] <= current["opened_at"]].tail(1)
            if latest_trigger.empty:
                continue
            trigger_row = latest_trigger.iloc[0]
            if pd.isna(trigger_row["ema_short"]) or trigger_row["close"] <= trigger_row["ema_short"]:
                continue
            reasons.append("5m trigger confirmation")
        stop_loss = None
        take_profit = None
        if phase_level >= 6:
            stop_loss = float(current["close"] - current["atr"] * config.stop_atr_mult)
            take_profit = float(current["close"] + current["atr"] * config.profit_atr_mult)
            reasons.append("ATR stop/take-profit")
        rows.append(
            {
                "opened_at": current["opened_at"],
                "action": "BUY",
                "phase": phase,
                "price": float(current["close"]),
                "risk_fraction": float(risk_fraction),
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "reason": "; ".join(reasons),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["opened_at", "action", "phase", "price", "risk_fraction", "stop_loss", "take_profit", "reason"],
    )


def mtf_trend_strategy_factory(params: dict[str, Any]):
    config = MTFTrendConfig(
        ema_long=int(params.get("ema_long", MTFTrendConfig.ema_long)),
        ema_short=int(params.get("ema_short", MTFTrendConfig.ema_short)),
        rsi_period=int(params.get("rsi_period", MTFTrendConfig.rsi_period)),
        rsi_oversold=float(params.get("rsi_oversold", MTFTrendConfig.rsi_oversold)),
        atr_period=int(params.get("atr_period", MTFTrendConfig.atr_period)),
        risk_per_trade=float(params.get("risk_per_trade", MTFTrendConfig.risk_per_trade)),
        stop_atr_mult=float(params.get("stop_atr_mult", MTFTrendConfig.stop_atr_mult)),
        profit_atr_mult=float(params.get("profit_atr_mult", MTFTrendConfig.profit_atr_mult)),
    )
    phase = str(params.get("phase", "6.1"))

    def run(frame: pd.DataFrame) -> pd.Series:
        prepared = _prepare_frame(frame)
        short = ema(prepared["close"], max(2, min(config.ema_short, len(prepared))))
        returns = prepared["close"].pct_change().fillna(0)
        short_mask = (prepared["close"] > short).shift(1)
        position = short_mask.where(short_mask.notna(), False).astype(bool).astype(float)
        if _phase_level(phase) >= 2:
            long = ema(prepared["close"], max(2, min(config.ema_long, len(prepared))))
            long_mask = (prepared["close"] > long).shift(1)
            position = position * long_mask.where(long_mask.notna(), False).astype(bool).astype(float)
        if _phase_level(phase) >= 3:
            trend_atr = atr(
                prepared["high"],
                prepared["low"],
                prepared["close"],
                max(2, min(config.atr_period, len(prepared))),
            )
            risk_fraction = (config.risk_per_trade / ((trend_atr * config.stop_atr_mult) / prepared["close"])).clip(0, 1).fillna(0)
            position = position * risk_fraction.shift(1).fillna(0)
        return (returns * position).fillna(0)

    return run


def _prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["opened_at"] = pd.to_datetime(result["opened_at"], utc=True)
    for column in ("open", "high", "low", "close", "volume"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result.sort_values("opened_at").reset_index(drop=True)


def _phase_level(phase: str) -> int:
    if phase not in _PHASES:
        raise ValueError(f"unknown MTF Trend phase: {phase}")
    return _PHASES[phase]
