from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from trading_learning.backtest.walk_forward import StrategyRunResult
from trading_learning.strategy.pairs_trading.cointegration import engle_granger_test
from trading_learning.strategy.pairs_trading.half_life import estimate_half_life
from trading_learning.strategy.pairs_trading.hedge_ratio import rolling_hedge_ratio
from trading_learning.strategy.pairs_trading.spread import compute_spread, rolling_zscore


@dataclass(frozen=True)
class PairsTradingConfig:
    asset_a: str = "BTCUSDT"
    asset_b: str = "ETHUSDT"
    timeframe: str = "1h"
    hedge_ratio_mode: str = "static"
    hedge_ratio_window: int = 240
    zscore_window: int = 96
    entry_threshold: float = 2.0
    exit_threshold: float = 0.3
    stop_threshold: float | None = 3.5
    min_cointegration_p_value: float = 0.05
    max_half_life_periods: int | None = 240
    capital_per_trade: float = 100.0
    risk_per_trade: float = 0.005
    fee_rate: float = 0.0008
    slippage_rate: float = 0.0005
    latency_rate: float = 0.0002
    order_type: str = "market"


@dataclass
class PairsSignal:
    timestamp: datetime
    direction: str
    asset_a_action: str
    asset_b_action: str
    asset_a_qty: float
    asset_b_qty: float
    z_score: float
    spread: float
    rationale: dict[str, Any]


class PairsTradingStrategy:
    def __init__(self, config: PairsTradingConfig):
        self.config = config
        self.training_stats: dict[str, Any] = {}

    def fit_on_training(self, df_a: pd.DataFrame, df_b: pd.DataFrame) -> dict[str, Any]:
        pair = _align_pair(df_a, df_b)
        if pair.empty:
            self.training_stats = _disabled_stats("missing_pair_data")
            return self.training_stats
        coint = engle_granger_test(pair["close_a"], pair["close_b"])
        spread = compute_spread(pair["close_a"], pair["close_b"], coint["alpha"], coint["beta"])
        half_life = estimate_half_life(spread)
        latest_zscore = rolling_zscore(spread, self.config.zscore_window).dropna()
        enabled = bool(coint["adf_p_value"] <= self.config.min_cointegration_p_value)
        if self.config.max_half_life_periods is not None:
            enabled = enabled and half_life <= self.config.max_half_life_periods
        self.training_stats = {
            "alpha": float(coint["alpha"]),
            "beta": float(coint["beta"]),
            "coint_p": float(coint["adf_p_value"]),
            "is_cointegrated": bool(coint["is_cointegrated"]),
            "half_life": float(half_life),
            "is_enabled": enabled,
            "latest_zscore": float(latest_zscore.iloc[-1]) if not latest_zscore.empty else float("nan"),
            "latest_spread": float(spread.iloc[-1]) if not spread.empty else float("nan"),
        }
        return self.training_stats

    def generate_signal(self, df_a: pd.DataFrame, df_b: pd.DataFrame, current_position: dict[str, Any]) -> PairsSignal:
        pair = _align_pair(df_a, df_b)
        if pair.empty:
            return self._signal(None, "flat", "hold", "hold", 0.0, 0.0, 0.0, 0.0, {"skip_reason": "missing_pair_data"})
        if not self.training_stats:
            self.fit_on_training(df_a, df_b)
        latest = pair.iloc[-1]
        alpha = float(self.training_stats.get("alpha", 0.0))
        beta = self._current_beta(pair)
        spread = compute_spread(pair["close_a"], pair["close_b"], alpha, beta)
        zscores = rolling_zscore(spread, self.config.zscore_window).dropna()
        z_score = float(self.training_stats.get("latest_zscore")) if "latest_zscore" in self.training_stats else float("nan")
        if np.isnan(z_score) and not zscores.empty:
            z_score = float(zscores.iloc[-1])
        latest_spread = float(spread.iloc[-1]) if not spread.empty else 0.0
        rationale = {
            "coint_p": float(self.training_stats.get("coint_p", 1.0)),
            "half_life": float(self.training_stats.get("half_life", float("inf"))),
            "hedge_ratio": beta,
        }
        if not bool(self.training_stats.get("is_enabled", False)):
            rationale["skip_reason"] = "cointegration_or_half_life_filter"
            return self._signal(latest["opened_at"], "flat", "hold", "hold", 0.0, 0.0, z_score, latest_spread, rationale)

        position_direction = current_position.get("direction", "flat") if current_position else "flat"
        asset_a_qty, asset_b_qty = self._quantities(float(latest["close_a"]), float(latest["close_b"]), beta)
        if position_direction != "flat" and self.config.stop_threshold is not None and abs(z_score) > self.config.stop_threshold:
            return self._signal(latest["opened_at"], "stop", "hold", "hold", 0.0, 0.0, z_score, latest_spread, rationale)
        if position_direction != "flat" and abs(z_score) < self.config.exit_threshold:
            return self._signal(latest["opened_at"], "exit", "hold", "hold", 0.0, 0.0, z_score, latest_spread, rationale)
        if position_direction == "flat" and z_score <= -self.config.entry_threshold:
            return self._signal(latest["opened_at"], "long_spread", "buy", "sell", asset_a_qty, asset_b_qty, z_score, latest_spread, rationale)
        if position_direction == "flat" and z_score >= self.config.entry_threshold:
            return self._signal(latest["opened_at"], "short_spread", "sell", "buy", asset_a_qty, asset_b_qty, z_score, latest_spread, rationale)
        return self._signal(latest["opened_at"], "flat", "hold", "hold", 0.0, 0.0, z_score, latest_spread, rationale)

    def round_trip_cost(self, *, asset_a_price: float, asset_b_price: float, asset_a_qty: float, asset_b_qty: float) -> float:
        one_way = self._one_way_cost()
        notional = asset_a_price * asset_a_qty + asset_b_price * asset_b_qty
        return 2.0 * notional * one_way

    def _current_beta(self, pair: pd.DataFrame) -> float:
        if self.config.hedge_ratio_mode == "rolling":
            beta_series = rolling_hedge_ratio(np.log(pair["close_a"]), np.log(pair["close_b"]), self.config.hedge_ratio_window).dropna()
            if not beta_series.empty:
                return float(beta_series.iloc[-1])
        return float(self.training_stats.get("beta", 0.0))

    def _quantities(self, asset_a_price: float, asset_b_price: float, beta: float) -> tuple[float, float]:
        capital = min(self.config.capital_per_trade, self.config.capital_per_trade * max(0.0, self.config.risk_per_trade) / 0.005)
        asset_a_qty = capital / 2.0 / asset_a_price if asset_a_price > 0 else 0.0
        hedge_notional = abs(beta) * capital / 2.0
        asset_b_qty = hedge_notional / asset_b_price if asset_b_price > 0 else 0.0
        return float(asset_a_qty), float(asset_b_qty)

    def _one_way_cost(self) -> float:
        slippage = 0.0 if self.config.order_type == "limit" else self.config.slippage_rate
        latency = 0.0 if self.config.order_type == "limit" else self.config.latency_rate
        return self.config.fee_rate + slippage + latency

    @staticmethod
    def _signal(
        timestamp: Any,
        direction: str,
        asset_a_action: str,
        asset_b_action: str,
        asset_a_qty: float,
        asset_b_qty: float,
        z_score: float,
        spread: float,
        rationale: dict[str, Any],
    ) -> PairsSignal:
        if timestamp is None:
            timestamp = pd.Timestamp.utcnow()
        return PairsSignal(
            timestamp=pd.Timestamp(timestamp).to_pydatetime(),
            direction=direction,
            asset_a_action=asset_a_action,
            asset_b_action=asset_b_action,
            asset_a_qty=float(asset_a_qty),
            asset_b_qty=float(asset_b_qty),
            z_score=float(z_score),
            spread=float(spread),
            rationale=rationale,
        )


def pairs_strategy_factory(params: dict[str, Any]):
    config = PairsTradingConfig(
        asset_a=str(params.get("asset_a", PairsTradingConfig.asset_a)),
        asset_b=str(params.get("asset_b", PairsTradingConfig.asset_b)),
        timeframe=str(params.get("timeframe", PairsTradingConfig.timeframe)),
        hedge_ratio_mode=str(params.get("hedge_ratio_mode", PairsTradingConfig.hedge_ratio_mode)),
        hedge_ratio_window=int(params.get("hedge_ratio_window", PairsTradingConfig.hedge_ratio_window)),
        zscore_window=int(params.get("zscore_window", PairsTradingConfig.zscore_window)),
        entry_threshold=float(params.get("entry_threshold", PairsTradingConfig.entry_threshold)),
        exit_threshold=float(params.get("exit_threshold", PairsTradingConfig.exit_threshold)),
        stop_threshold=params.get("stop_threshold", PairsTradingConfig.stop_threshold),
        min_cointegration_p_value=float(params.get("min_cointegration_p_value", PairsTradingConfig.min_cointegration_p_value)),
        max_half_life_periods=params.get("max_half_life_periods", PairsTradingConfig.max_half_life_periods),
        capital_per_trade=float(params.get("capital_per_trade", PairsTradingConfig.capital_per_trade)),
        risk_per_trade=float(params.get("risk_per_trade", PairsTradingConfig.risk_per_trade)),
        fee_rate=float(params.get("fee_rate", PairsTradingConfig.fee_rate)),
        slippage_rate=float(params.get("slippage_rate", PairsTradingConfig.slippage_rate)),
        latency_rate=float(params.get("latency_rate", PairsTradingConfig.latency_rate)),
        order_type=str(params.get("order_type", PairsTradingConfig.order_type)),
    )
    phase = str(params.get("phase", "H-200"))
    if phase == "H-200":
        config = replace(config, stop_threshold=None, max_half_life_periods=None)
    elif phase == "H-201":
        config = replace(config, max_half_life_periods=None)
    elif phase in {"H-203", "H-204", "H-205", "H-205A", "H-205B", "H-205C"}:
        config = replace(config, hedge_ratio_mode="rolling")

    def run(frames: dict[str, pd.DataFrame] | pd.DataFrame) -> StrategyRunResult:
        if not isinstance(frames, dict) or config.asset_a not in frames or config.asset_b not in frames:
            frame = frames if isinstance(frames, pd.DataFrame) else pd.DataFrame()
            return StrategyRunResult(returns=np.zeros(len(frame), dtype="float64"), trade_count=0, metadata={"deferred": True, "reason": "missing_pair_data"})
        strategy = PairsTradingStrategy(config)
        stats = strategy.fit_on_training(frames[config.asset_a], frames[config.asset_b])
        pair = _align_pair(frames[config.asset_a], frames[config.asset_b])
        if pair.empty:
            return StrategyRunResult(returns=np.zeros(0, dtype="float64"), trade_count=0, metadata={"deferred": True, "reason": "missing_pair_data"})
        returns, trade_count = _simulate_pair_returns(pair, strategy, stats)
        return StrategyRunResult(
            returns=returns,
            trade_count=trade_count,
            metadata={
                "deferred": not bool(stats.get("is_enabled", False)),
                "pair": f"{config.asset_a}-{config.asset_b}",
                "training_stats": stats,
                "cost_model": {
                    "fee_rate": config.fee_rate,
                    "slippage_rate": 0.0 if config.order_type == "limit" else config.slippage_rate,
                    "latency_rate": 0.0 if config.order_type == "limit" else config.latency_rate,
                    "order_type": config.order_type,
                },
            },
        )

    return run


def _simulate_pair_returns(pair: pd.DataFrame, strategy: PairsTradingStrategy, stats: dict[str, Any]) -> tuple[np.ndarray, int]:
    config = strategy.config
    if not bool(stats.get("is_enabled", False)):
        return np.zeros(len(pair), dtype="float64"), 0
    beta = float(stats.get("beta", 0.0))
    if config.hedge_ratio_mode == "rolling":
        beta_series = rolling_hedge_ratio(np.log(pair["close_a"]), np.log(pair["close_b"]), config.hedge_ratio_window)
    else:
        beta_series = pd.Series(beta, index=pair.index)
    spread = compute_spread(pair["close_a"], pair["close_b"], float(stats["alpha"]), beta)
    zscores = rolling_zscore(spread, config.zscore_window)
    returns = np.zeros(len(pair), dtype="float64")
    direction = "flat"
    entry_spread = 0.0
    trade_count = 0
    one_way_cost = strategy._one_way_cost()

    for index in range(1, len(pair)):
        z = zscores.iloc[index]
        if pd.isna(z):
            continue
        current_spread = float(spread.iloc[index])
        if direction != "flat":
            pnl_sign = 1.0 if direction == "long_spread" else -1.0
            returns[index] += pnl_sign * (current_spread - float(spread.iloc[index - 1]))
            should_exit = abs(float(z)) < config.exit_threshold
            should_stop = config.stop_threshold is not None and abs(float(z)) > config.stop_threshold
            if should_exit or should_stop or index == len(pair) - 1:
                returns[index] -= 2.0 * one_way_cost
                direction = "flat"
        if direction == "flat":
            beta = float(beta_series.iloc[index]) if pd.notna(beta_series.iloc[index]) else beta
            del beta
            if float(z) <= -config.entry_threshold:
                returns[index] -= 2.0 * one_way_cost
                direction = "long_spread"
                entry_spread = current_spread
                trade_count += 1
            elif float(z) >= config.entry_threshold:
                returns[index] -= 2.0 * one_way_cost
                direction = "short_spread"
                entry_spread = current_spread
                trade_count += 1
    del entry_spread
    return returns, trade_count


def _align_pair(df_a: pd.DataFrame, df_b: pd.DataFrame) -> pd.DataFrame:
    a = _prepare_frame(df_a).rename(columns={"close": "close_a"})
    b = _prepare_frame(df_b).rename(columns={"close": "close_b"})
    if a.empty or b.empty:
        return pd.DataFrame()
    merged = pd.merge(a[["opened_at", "close_a"]], b[["opened_at", "close_b"]], on="opened_at", how="inner")
    return merged.sort_values("opened_at").reset_index(drop=True)


def _prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    result["opened_at"] = pd.to_datetime(result["opened_at"], utc=True)
    result["close"] = pd.to_numeric(result["close"], errors="coerce")
    return result.dropna(subset=["opened_at", "close"]).sort_values("opened_at").reset_index(drop=True)


def _disabled_stats(reason: str) -> dict[str, Any]:
    return {"is_enabled": False, "coint_p": 1.0, "half_life": float("inf"), "skip_reason": reason}
