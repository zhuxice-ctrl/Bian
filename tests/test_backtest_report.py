from datetime import datetime, timezone

import pytest

from trading_learning.backtest.report import build_backtest_report
from trading_learning.backtest.report import summarize_backtest
from trading_learning.models import BacktestResult, Side, Trade


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


def test_build_backtest_report_returns_round_trips_equity_and_drawdown():
    result = BacktestResult(
        symbol="BTCUSDT",
        starting_cash=1000.0,
        ending_cash=1004.6,
        position_quantity=0.0,
        trade_count=4,
        trades=(
            trade(Side.BUY, 1.0, 100.0, 0.5, 0),
            trade(Side.SELL, 1.0, 110.0, 0.5, 1),
            trade(Side.BUY, 1.0, 120.0, 0.6, 2),
            trade(Side.SELL, 1.0, 116.0, 0.4, 3),
        ),
    )

    report = build_backtest_report(result)

    assert report["metrics"] == {
        "symbol": "BTCUSDT",
        "trade_count": 4,
        "round_trips": 2,
        "win_count": 1,
        "loss_count": 1,
        "win_rate": pytest.approx(0.5),
        "realized_pnl": pytest.approx(4.6),
        "total_fees": pytest.approx(2.0),
        "max_drawdown": pytest.approx(-5.0),
        "max_drawdown_pct": pytest.approx(-0.0049554013875),
    }
    assert report["round_trips"] == [
        {
            "entry_trade_id": "trade-BUY-0",
            "exit_trade_id": "trade-SELL-1",
            "entry_time": "2026-05-01T00:00:00+00:00",
            "exit_time": "2026-05-01T01:00:00+00:00",
            "quantity": 1.0,
            "entry_price": 100.0,
            "exit_price": 110.0,
            "fees": pytest.approx(1.0),
            "pnl": pytest.approx(9.0),
            "pnl_pct": pytest.approx(0.09),
        },
        {
            "entry_trade_id": "trade-BUY-2",
            "exit_trade_id": "trade-SELL-3",
            "entry_time": "2026-05-01T02:00:00+00:00",
            "exit_time": "2026-05-01T03:00:00+00:00",
            "quantity": 1.0,
            "entry_price": 120.0,
            "exit_price": 116.0,
            "fees": pytest.approx(1.0),
            "pnl": pytest.approx(-5.0),
            "pnl_pct": pytest.approx(-0.041666666667),
        },
    ]
    assert report["equity_curve"] == [
        {"time": "2026-05-01T00:00:00+00:00", "equity": 1000.0},
        {"time": "2026-05-01T01:00:00+00:00", "equity": pytest.approx(1009.0)},
        {"time": "2026-05-01T03:00:00+00:00", "equity": pytest.approx(1004.0)},
    ]
