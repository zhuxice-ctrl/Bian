from dataclasses import dataclass


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    order_type: str
    quantity: float | None = None
    quote_order_qty: float | None = None


@dataclass(frozen=True)
class RiskConfig:
    daily_order_limit: int = 5
    max_quote_order_qty: float = 100.0
    allowed_symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


class ExecutionRiskGuard:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def check_order(self, intent: OrderIntent, orders_today: int) -> RiskDecision:
        if orders_today >= self.config.daily_order_limit:
            return RiskDecision(False, "daily order limit reached")
        if intent.symbol not in self.config.allowed_symbols:
            return RiskDecision(False, "symbol not allowed")
        if intent.side not in ("BUY", "SELL"):
            return RiskDecision(False, "invalid side")
        if intent.order_type not in ("MARKET", "LIMIT"):
            return RiskDecision(False, "invalid order type")
        if intent.quantity is None and intent.quote_order_qty is None:
            return RiskDecision(False, "size required")
        if (
            intent.quote_order_qty is not None
            and intent.quote_order_qty > self.config.max_quote_order_qty
        ):
            return RiskDecision(False, "max quote order quantity exceeded")
        return RiskDecision(True, "allowed")
