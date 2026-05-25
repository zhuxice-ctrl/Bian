# H-301 SIG_TREND_FAST Baseline Backtest

## Signal
- Description: EWMAC(8,32) fast trend forecast.
- Parameters: `fast_span=8, slow_span=32, normalization=expanding`
- Forecast source: `trading_learning.signals.forecast_library`
- Prior note: H-301 is the fast trend baseline from the H-213 signal set.

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
| Net Sharpe | 0.377674 |
| Gross Sharpe | 0.546407 |
| CAGR | 4.64% |
| Max DD | -16.09% |
| Sortino | 0.562184 |
| Calmar | 0.287614 |
| Win Rate | 49.51% |
| Profit Factor | 1.073728 |
| Annual Turnover | 12.548408 |
| Total Cost Drag | 4.20% |
| Cost Sharpe Drag | 0.168734 |
| Total Return | 7.87% |
| Annual Volatility | 14.91% |

## BTC Buy-and-Hold Comparison
| Metric | Signal | BTC B&H |
|---|---:|---:|
| Net Sharpe | 0.377674 | 0.466468 |
| Gross Sharpe | 0.546407 | 0.466468 |
| CAGR | 4.64% | 11.53% |
| Max DD | -16.09% | -49.53% |
| Sortino | 0.562184 | 0.687652 |
| Calmar | 0.287614 | 0.232334 |
| Win Rate | 49.51% | 50.49% |
| Profit Factor | 1.073728 | 1.072105 |
| Annual Turnover | 12.548408 | 0.000000 |
| Total Cost Drag | 4.20% | 0.00% |
| Cost Sharpe Drag | 0.168734 | 0.000000 |
| Total Return | 7.87% | 20.00% |
| Annual Volatility | 14.91% | 45.03% |

## Pass/Fail
- Standard: net Sharpe >= 0.30
- Observed net Sharpe: 0.377674
- Result: PASS

## Known Limitations
- Funding-rate cost is not included.
- This is a single BTCUSDT 1d window, not a walk-forward or multi-market validation.
- No signal selection recommendation is made here; signal combination is deferred to H-310.
