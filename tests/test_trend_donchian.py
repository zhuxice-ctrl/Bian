import math
from pathlib import Path

import pandas as pd
import pytest

from trading_learning.trend import (
    donchian_channels,
    donchian_signals,
    generate_h300_report,
    run_donchian_backtest,
    run_h300_ablation,
)


def _prices(
    closes: list[float],
    highs: list[float] | None = None,
    lows: list[float] | None = None,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "opened_at": pd.date_range("2026-01-01", periods=len(closes), freq="D", tz="UTC"),
            "open": closes,
            "high": highs or closes,
            "low": lows or closes,
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


def test_donchian_channels_use_past_n_bars_excluding_today():
    prices = _prices(
        closes=[10, 11, 12, 13, 14],
        highs=[10, 12, 50, 13, 14],
        lows=[9, 8, 7, 6, 1],
    )

    channels = donchian_channels(prices, n=3)

    assert channels["upper"].iloc[:3].isna().all()
    assert channels["lower"].iloc[:3].isna().all()
    assert channels["upper"].iloc[3] == pytest.approx(50)
    assert channels["lower"].iloc[3] == pytest.approx(7)
    assert channels["upper"].iloc[4] == pytest.approx(50)
    assert channels["lower"].iloc[4] == pytest.approx(6)


def test_donchian_channels_do_not_include_today_high_or_low():
    prices = _prices(
        closes=[10, 10, 10, 10],
        highs=[10, 11, 12, 99],
        lows=[10, 9, 8, 1],
    )

    channels = donchian_channels(prices, n=3)

    assert channels["upper"].iloc[3] == pytest.approx(12)
    assert channels["upper"].iloc[3] != prices["high"].iloc[3]
    assert channels["lower"].iloc[3] == pytest.approx(8)
    assert channels["lower"].iloc[3] != prices["low"].iloc[3]


def test_donchian_signals_trigger_only_on_close_breakouts():
    prices = _prices(
        closes=[10, 11, 12, 13, 9, 8],
        highs=[10, 11, 12, 12, 10, 9],
        lows=[10, 10, 10, 10, 10, 9],
    )

    signals = donchian_signals(prices, n=3)

    assert signals.tolist() == [0, 0, 0, 1, -1, -1]


def test_donchian_signals_do_not_trigger_on_equal_channel_value():
    prices = _prices(
        closes=[10, 11, 12, 12, 10],
        highs=[10, 11, 12, 12, 12],
        lows=[10, 10, 10, 10, 10],
    )

    signals = donchian_signals(prices, n=3)

    assert signals.tolist() == [0, 0, 0, 0, 0]


def test_donchian_channels_reject_missing_columns_and_invalid_n():
    prices = pd.DataFrame({"close": [1.0, 2.0, 3.0]})

    with pytest.raises(ValueError, match="high"):
        donchian_channels(prices, n=2)
    with pytest.raises(ValueError, match="n must be positive"):
        donchian_channels(_prices([1.0, 2.0, 3.0]), n=0)


def test_run_donchian_backtest_records_closed_trade_and_linear_returns():
    prices = _prices(
        closes=[10, 11, 12, 13, 11, 8],
        highs=[10, 11, 12, 13, 11, 8],
        lows=[10, 11, 12, 13, 11, 8],
    )

    result = run_donchian_backtest(prices, n=2, exit_n=1)

    assert result["positions"].tolist() == [0, 0, 1, 1, -1, -1]
    assert result["returns"].tolist() == pytest.approx([0.0, 0.0, 0.0, 1.0 / 12.0, -2.0 / 12.0, 3.0 / 11.0])
    assert result["equity_curve"].tolist() == pytest.approx(
        [1.0, 1.0, 1.0, 1.0 + 1.0 / 12.0, 1.0 - 1.0 / 12.0, 1.0 - 1.0 / 12.0 + 3.0 / 11.0]
    )

    trades = result["trades"]
    assert len(trades) == 2
    assert trades.iloc[0]["side"] == "long"
    assert trades.iloc[0]["entry_price"] == pytest.approx(12.0)
    assert trades.iloc[0]["exit_price"] == pytest.approx(11.0)
    assert trades.iloc[0]["pnl"] == pytest.approx(-1.0 / 12.0)
    assert trades.iloc[1]["side"] == "short"
    assert trades.iloc[1]["exit_reason"] == "mark_to_market"
    assert trades.iloc[1]["pnl"] == pytest.approx(3.0 / 11.0)


def test_run_donchian_backtest_reverses_from_long_to_short_on_exit_channel_break():
    prices = _prices(
        closes=[10, 11, 12, 13, 11],
        highs=[10, 11, 12, 13, 11],
        lows=[10, 11, 12, 13, 11],
    )

    result = run_donchian_backtest(prices, n=2, exit_n=1)

    assert result["positions"].iloc[3] == 1
    assert result["positions"].iloc[4] == -1
    assert result["trades"].iloc[0]["exit_reason"] == "reverse_to_short"


def test_run_donchian_backtest_reverses_from_short_to_long_on_exit_channel_break():
    prices = _prices(
        closes=[13, 12, 11, 10, 12],
        highs=[13, 12, 11, 10, 12],
        lows=[13, 12, 11, 10, 12],
    )

    result = run_donchian_backtest(prices, n=2, exit_n=1)

    assert result["positions"].iloc[3] == -1
    assert result["positions"].iloc[4] == 1
    assert result["trades"].iloc[0]["exit_reason"] == "reverse_to_long"


def test_run_donchian_backtest_marks_open_trade_at_final_price():
    prices = _prices(
        closes=[10, 11, 12, 13],
        highs=[10, 11, 12, 13],
        lows=[10, 11, 12, 13],
    )

    result = run_donchian_backtest(prices, n=2, exit_n=1)

    assert result["trades"].iloc[0]["side"] == "long"
    assert result["trades"].iloc[0]["exit_reason"] == "mark_to_market"
    assert result["trades"].iloc[0]["pnl"] == pytest.approx(1.0 / 12.0)


def test_run_donchian_backtest_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="at least one row"):
        run_donchian_backtest(_prices([]), n=2)
    with pytest.raises(ValueError, match="initial_capital"):
        run_donchian_backtest(_prices([1.0, 2.0]), n=2, initial_capital=0.0)


def test_run_donchian_backtest_default_exit_window_is_half_n():
    prices = _prices(
        closes=[10, 11, 12, 13, 11, 8],
        highs=[10, 11, 12, 13, 11, 8],
        lows=[10, 11, 12, 13, 11, 8],
    )

    default_result = run_donchian_backtest(prices, n=2)
    explicit_result = run_donchian_backtest(prices, n=2, exit_n=1)

    assert default_result["positions"].tolist() == explicit_result["positions"].tolist()
    assert default_result["returns"].tolist() == pytest.approx(explicit_result["returns"].tolist())


def test_run_h300_ablation_uses_local_csv_and_mechanical_pass_rules(tmp_path: Path):
    root = tmp_path / "data" / "local"
    data_dir = root / "market_data" / "BTCUSDT" / "1d"
    data_dir.mkdir(parents=True)
    csv_path = data_dir / "BTCUSDT-1d.csv"
    frame = _prices([10, 11, 12, 13, 11, 8, 9, 12])
    frame.to_csv(csv_path, index=False)

    result = run_h300_ablation(
        symbol="BTCUSDT",
        interval="1d",
        parameter_set=[2],
        data_root=root,
    )

    assert result["meta"]["symbol"] == "BTCUSDT"
    assert result["meta"]["interval"] == "1d"
    assert result["meta"]["rows"] == 8
    assert result["meta"]["parameter_set"] == [2]
    assert result["strategies"][2]["metrics"]["trade_count"] >= 1
    assert result["strategies"][2]["pass_fail"]["overall"] is False
    assert "simple" in result["benchmarks"]
    assert "compounded" in result["benchmarks"]


def test_run_h300_ablation_raises_when_local_csv_is_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="BTCUSDT-1d.csv"):
        run_h300_ablation(symbol="BTCUSDT", interval="1d", parameter_set=[20], data_root=tmp_path)


def test_generate_h300_report_writes_metrics_benchmarks_and_pass_fail(tmp_path: Path):
    result = {
        "meta": {
            "symbol": "BTCUSDT",
            "interval": "1d",
            "start": "2026-01-01",
            "end": "2026-01-08",
            "rows": 8,
            "parameter_set": [20],
        },
        "thresholds": {
            "sharpe_ratio": 0.3,
            "max_drawdown": -0.6,
            "trade_count": 10,
            "profit_factor": 1.2,
        },
        "strategies": {
            20: {
                "metrics": {
                    "sharpe_ratio": 0.1,
                    "sortino_ratio": math.nan,
                    "calmar_ratio": -0.2,
                    "max_drawdown": -0.7,
                    "cagr": -0.1,
                    "volatility": 0.3,
                    "win_rate": 0.4,
                    "profit_factor": 0.8,
                    "trade_count": 3,
                },
                "pass_fail": {
                    "sharpe_ratio": False,
                    "max_drawdown": False,
                    "trade_count": False,
                    "profit_factor": False,
                    "overall": False,
                },
            }
        },
        "benchmarks": {
            "simple": {
                "metrics": {
                    "sharpe_ratio": 1.0,
                    "sortino_ratio": 2.0,
                    "calmar_ratio": 3.0,
                    "max_drawdown": -0.1,
                    "cagr": 0.5,
                    "volatility": 0.2,
                    "win_rate": 0.5,
                    "profit_factor": 1.5,
                    "trade_count": 1,
                }
            },
            "compounded": {
                "metrics": {
                    "sharpe_ratio": 1.0,
                    "sortino_ratio": 2.0,
                    "calmar_ratio": 3.0,
                    "max_drawdown": -0.1,
                    "cagr": 0.5,
                    "volatility": 0.2,
                    "win_rate": 0.5,
                    "profit_factor": 1.5,
                    "trade_count": 1,
                }
            },
        },
        "overall_pass": False,
    }
    output_path = tmp_path / "ablation-trend-h300-2026-05-24.md"

    generate_h300_report(result, output_path)

    text = output_path.read_text(encoding="utf-8")
    assert "# H-300 Donchian 趋势策略 Ablation 报告" in text
    assert "| N=20 | 0.100000 | nan | -0.200000 | -70.00% |" in text
    assert "| N=20 | Fail | Fail | Fail | Fail | Fail |" in text
    assert "总体结论：Fail" in text


def test_generate_h300_report_creates_parent_directory(tmp_path: Path):
    result = {
        "meta": {
            "symbol": "BTCUSDT",
            "interval": "1d",
            "start": "2026-01-01",
            "end": "2026-01-02",
            "rows": 2,
            "parameter_set": [],
        },
        "strategies": {},
        "benchmarks": {},
        "overall_pass": True,
    }
    output_path = tmp_path / "nested" / "report.md"

    generate_h300_report(result, output_path)

    assert output_path.exists()
