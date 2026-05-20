import pytest

from trading_learning.backtest.report import summarize_backtest
from trading_learning.models import BacktestResult, Side, Trade
from datetime import datetime, timezone


def trade(side: Side, quantity: float, price: float, fee: float, hour: int) -> Trade:
    return Trade(
        external_id=f"trade-{side.value}-{hour}",
        symbol="BTCUSDT",
        side=side,
        quantity=quantity,
        price=price,
        fee=fee,
        timestamp=datetime(2026, 5, 1, hour, tzinfo=timezone.utc),
        reason="test",
    )


def test_summarize_backtest_reports_realized_metrics():
    result = BacktestResult(
        symbol="BTCUSDT",
        starting_cash=1000.0,
        ending_cash=1020.0,
        position_quantity=0.0,
        trade_count=4,
        trades=(
            trade(Side.BUY, 1.0, 100.0, 0.1, 0),
            trade(Side.SELL, 1.0, 110.0, 0.1, 1),
            trade(Side.BUY, 1.0, 120.0, 0.1, 2),
            trade(Side.SELL, 1.0, 115.0, 0.1, 3),
        ),
    )

    metrics = summarize_backtest(result)

    assert metrics.symbol == "BTCUSDT"
    assert metrics.trade_count == 4
    assert metrics.round_trips == 2
    assert metrics.win_count == 1
    assert metrics.loss_count == 1
    assert metrics.win_rate == pytest.approx(0.5)
    assert metrics.realized_pnl == pytest.approx(20.0)
    assert metrics.total_fees == pytest.approx(0.4)
