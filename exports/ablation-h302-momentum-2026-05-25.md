# H-302 SIG_MOMENTUM Baseline Backtest

## Signal
- Description: Past 60-day return momentum forecast.
- Parameters: `lookback=60, normalization=expanding`
- Forecast source: `trading_learning.signals.forecast_library`
- Prior note: H-214 showed this signal as regime-dependent: first half 1.50, second half -0.21.

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
| Net Sharpe | 0.533913 |
| Gross Sharpe | 0.783991 |
| CAGR | 6.12% |
| Max DD | -12.51% |
| Sortino | 0.833074 |
| Calmar | 0.488199 |
| Win Rate | 49.02% |
| Profit Factor | 1.103089 |
| Annual Turnover | 15.616324 |
| Total Cost Drag | 5.23% |
| Cost Sharpe Drag | 0.250078 |
| Total Return | 10.43% |
| Annual Volatility | 12.57% |

## BTC Buy-and-Hold Comparison
| Metric | Signal | BTC B&H |
|---|---:|---:|
| Net Sharpe | 0.533913 | 0.466468 |
| Gross Sharpe | 0.783991 | 0.466468 |
| CAGR | 6.12% | 11.53% |
| Max DD | -12.51% | -49.53% |
| Sortino | 0.833074 | 0.687652 |
| Calmar | 0.488199 | 0.232334 |
| Win Rate | 49.02% | 50.49% |
| Profit Factor | 1.103089 | 1.072105 |
| Annual Turnover | 15.616324 | 0.000000 |
| Total Cost Drag | 5.23% | 0.00% |
| Cost Sharpe Drag | 0.250078 | 0.000000 |
| Total Return | 10.43% | 20.00% |
| Annual Volatility | 12.57% | 45.03% |

## Pass/Fail
- Standard: net Sharpe >= 0.30
- Observed net Sharpe: 0.533913
- Result: PASS

## Known Limitations
- Funding-rate cost is not included.
- This is a single BTCUSDT 1d window, not a walk-forward or multi-market validation.
- No signal selection recommendation is made here; signal combination is deferred to H-310.
