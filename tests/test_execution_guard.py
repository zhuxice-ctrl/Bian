from trading_learning.risk.execution_guard import (
    ExecutionRiskGuard,
    OrderIntent,
    RiskConfig,
)


def test_allows_btcusdt_buy_market_quote_order_when_under_limit():
    guard = ExecutionRiskGuard(RiskConfig())

    decision = guard.check_order(
        OrderIntent(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quote_order_qty=25.0,
        ),
        orders_today=0,
    )

    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_rejects_daily_limit():
    guard = ExecutionRiskGuard(RiskConfig(daily_order_limit=2))

    decision = guard.check_order(
        OrderIntent(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quote_order_qty=25.0,
        ),
        orders_today=2,
    )

    assert decision.allowed is False
    assert "daily order limit" in decision.reason


def test_rejects_unsupported_symbol():
    guard = ExecutionRiskGuard(RiskConfig())

    decision = guard.check_order(
        OrderIntent(
            symbol="DOGEUSDT",
            side="BUY",
            order_type="MARKET",
            quote_order_qty=25.0,
        ),
        orders_today=0,
    )

    assert decision.allowed is False
    assert "symbol not allowed" in decision.reason


def test_rejects_invalid_side_and_type():
    guard = ExecutionRiskGuard(RiskConfig())

    invalid_side = guard.check_order(
        OrderIntent(
            symbol="BTCUSDT",
            side="HOLD",
            order_type="MARKET",
            quote_order_qty=25.0,
        ),
        orders_today=0,
    )
    invalid_type = guard.check_order(
        OrderIntent(
            symbol="BTCUSDT",
            side="BUY",
            order_type="STOP",
            quote_order_qty=25.0,
        ),
        orders_today=0,
    )

    assert invalid_side.allowed is False
    assert "invalid side" in invalid_side.reason
    assert invalid_type.allowed is False
    assert "invalid order type" in invalid_type.reason


def test_rejects_missing_size():
    guard = ExecutionRiskGuard(RiskConfig())

    decision = guard.check_order(
        OrderIntent(symbol="BTCUSDT", side="BUY", order_type="MARKET"),
        orders_today=0,
    )

    assert decision.allowed is False
    assert "size required" in decision.reason


def test_rejects_quote_size_above_max():
    guard = ExecutionRiskGuard(RiskConfig(max_quote_order_qty=50.0))

    decision = guard.check_order(
        OrderIntent(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quote_order_qty=51.0,
        ),
        orders_today=0,
    )

    assert decision.allowed is False
    assert "max quote order quantity" in decision.reason
