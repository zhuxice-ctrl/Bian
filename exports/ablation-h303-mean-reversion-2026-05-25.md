# H-303 SIG_MEAN_REV Baseline Backtest

## Signal
- Description: -1 times 20-day price z-score mean-reversion forecast.
- Parameters: `window=20, normalization=expanding`
- Forecast source: `trading_learning.signals.forecast_library`
- Prior note: H-214 showed this as the only candidate with positive standalone Sharpe in both halves.

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
| Net Sharpe | -0.631104 |
| Gross Sharpe | -0.068178 |
| CAGR | -8.82% |
| Max DD | -18.71% |
| Sortino | -0.838497 |
| Calmar | -0.470894 |
| Win Rate | 46.72% |
| Profit Factor | 0.891063 |
| Annual Turnover | 37.172195 |
| Total Cost Drag | 12.45% |
| Cost Sharpe Drag | 0.562926 |
| Total Return | -14.30% |
| Annual Volatility | 13.22% |

## BTC Buy-and-Hold Comparison
| Metric | Signal | BTC B&H |
|---|---:|---:|
| Net Sharpe | -0.631104 | 0.466468 |
| Gross Sharpe | -0.068178 | 0.466468 |
| CAGR | -8.82% | 11.53% |
| Max DD | -18.71% | -49.53% |
| Sortino | -0.838497 | 0.687652 |
| Calmar | -0.470894 | 0.232334 |
| Win Rate | 46.72% | 50.49% |
| Profit Factor | 0.891063 | 1.072105 |
| Annual Turnover | 37.172195 | 0.000000 |
| Total Cost Drag | 12.45% | 0.00% |
| Cost Sharpe Drag | 0.562926 | 0.000000 |
| Total Return | -14.30% | 20.00% |
| Annual Volatility | 13.22% | 45.03% |

## Pass/Fail
- Standard: net Sharpe >= 0.10
- Observed net Sharpe: -0.631104
- Result: FAIL

## Known Limitations
- Funding-rate cost is not included.
- This is a single BTCUSDT 1d window, not a walk-forward or multi-market validation.
- No signal selection recommendation is made here; signal combination is deferred to H-310.
