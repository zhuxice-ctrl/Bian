from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RealTradingRiskConfig:
    allowed_symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")
    max_quote_order_qty: float = 0.0
    max_daily_loss: float = 0.0
    max_position_quote: float = 0.0
    cooldown_seconds: int = 0


@dataclass(frozen=True)
class RealOrderIntent:
    symbol: str
    side: str
    order_type: str
    quote_order_qty: float


@dataclass(frozen=True)
class RealRiskDecision:
    allowed: bool
    reason: str


def production_readiness_status() -> dict[str, Any]:
    checks = {
        "local_manual_approval": False,
        "risk_limits_configured": False,
        "daily_loss_limit_configured": False,
        "position_limits_configured": False,
        "cooldown_configured": False,
        "dry_run_verified": False,
        "kill_switch_reviewed": False,
        "real_order_tests_passed": False,
        "backup_recent": False,
    }
    missing = [name for name, passed in checks.items() if not passed]
    return {
        "ready": False,
        "real_trading_enabled": False,
        "kill_switch_active": True,
        "kill_switch": {
            "active": True,
            "mode": "locked",
            "message": "Kill switch is active; real trading routes are unavailable.",
        },
        "checks": checks,
        "missing": missing,
        "message": "Real trading is disabled. Complete the local production readiness gate before adding any real order path.",
    }


def evaluate_real_order_risk(
    intent: RealOrderIntent,
    config: RealTradingRiskConfig,
    *,
    daily_loss: float,
    current_position_quote: float,
    seconds_since_last_order: int,
) -> RealRiskDecision:
    symbol = intent.symbol.upper()
    if symbol not in config.allowed_symbols:
        return RealRiskDecision(False, "symbol not allowed")
    if intent.side not in {"BUY", "SELL"}:
        return RealRiskDecision(False, "invalid side")
    if intent.order_type not in {"MARKET", "LIMIT"}:
        return RealRiskDecision(False, "invalid order type")
    if intent.quote_order_qty <= 0:
        return RealRiskDecision(False, "size required")
    if config.max_quote_order_qty <= 0 or intent.quote_order_qty > config.max_quote_order_qty:
        return RealRiskDecision(False, "max quote order quantity exceeded")
    if config.max_daily_loss <= 0 or daily_loss >= config.max_daily_loss:
        return RealRiskDecision(False, "daily loss limit reached")
    if config.max_position_quote <= 0 or current_position_quote + intent.quote_order_qty > config.max_position_quote:
        return RealRiskDecision(False, "position limit exceeded")
    if config.cooldown_seconds <= 0 or seconds_since_last_order < config.cooldown_seconds:
        return RealRiskDecision(False, "cooldown active")
    return RealRiskDecision(True, "allowed")


def build_real_order_dry_run(intent: RealOrderIntent) -> dict[str, Any]:
    gate = production_readiness_status()
    risk = evaluate_real_order_risk(
        intent,
        RealTradingRiskConfig(),
        daily_loss=0.0,
        current_position_quote=0.0,
        seconds_since_last_order=0,
    )
    return {
        "symbol": intent.symbol.upper(),
        "side": intent.side,
        "order_type": intent.order_type,
        "quote_order_qty": intent.quote_order_qty,
        "would_send_order": False,
        "blocked_by_gate": not gate["ready"],
        "risk_decision": {"allowed": risk.allowed, "reason": risk.reason},
        "missing_requirements": gate["missing"],
    }
