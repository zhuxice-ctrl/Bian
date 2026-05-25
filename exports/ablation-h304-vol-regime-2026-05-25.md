# H-304 SIG_VOL_REGIME Baseline Backtest

## Signal
- Description: Expanding-normalized rolling 60-day volatility-regime forecast.
- Parameters: `vol_window=60, normalization=expanding`
- Forecast source: `trading_learning.signals.forecast_library`
- Prior note: H-214 showed this signal flipping sign: first half -0.87, second half +1.40.

## Backtest Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Window: 2024-09-19 ~ 2026-05-22
- Rows: 611
- Capital: 100,000
- Vol target: 20.00%
- Vol lookback: 60
- Cost: 0.20% round trip
- Max leverage: 2.0x
- Benchmark: BTC buy-and-hold over the same window

## Metrics
| Metric | Signal |
|---|---:|
| Net Sharpe | -0.099460 |
| Gross Sharpe | 0.040878 |
| CAGR | -2.27% |
| Max DD | -21.62% |
| Sortino | -0.135911 |
| Calmar | -0.104666 |
| Win Rate | 50.82% |
| Profit Factor | 0.983137 |
| Annual Turnover | 9.577354 |
| Total Cost Drag | 3.21% |
| Cost Sharpe Drag | 0.140339 |
| Total Return | -3.76% |
| Annual Volatility | 13.65% |

## BTC Buy-and-Hold Comparison
| Metric | Signal | BTC B&H |
|---|---:|---:|
| Net Sharpe | -0.099460 | 0.466468 |
| Gross Sharpe | 0.040878 | 0.466468 |
| CAGR | -2.27% | 11.53% |
| Max DD | -21.62% | -49.53% |
| Sortino | -0.135911 | 0.687652 |
| Calmar | -0.104666 | 0.232334 |
| Win Rate | 50.82% | 50.49% |
| Profit Factor | 0.983137 | 1.072105 |
| Annual Turnover | 9.577354 | 0.000000 |
| Total Cost Drag | 3.21% | 0.00% |
| Cost Sharpe Drag | 0.140339 | 0.000000 |
| Total Return | -3.76% | 20.00% |
| Annual Volatility | 13.65% | 45.03% |

## Pass/Fail
- Standard: net Sharpe >= 0.00
- Observed net Sharpe: -0.099460
- Result: FAIL

## Known Limitations
- Funding-rate cost is not included.
- This is a single BTCUSDT 1d window, not a walk-forward or multi-market validation.
- No signal selection recommendation is made here; signal combination is deferred to H-310.
