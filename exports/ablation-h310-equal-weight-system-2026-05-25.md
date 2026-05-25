# H-310 Equal-Weight Four-Signal System

## Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Window: 2024-09-19 ~ 2026-05-22
- Rows: 611
- Combined forecast: mean(SIG_TREND_FAST, SIG_MOMENTUM, SIG_MEAN_REV, SIG_VOL_REGIME)
- Capital: 100,000
- Vol target: 20.00%
- Vol lookback: 60
- Cost: 0.20% round trip
- Max leverage: 2.0x

## Six-Column Metric Comparison
| Metric | SIG_TREND_FAST | SIG_MOMENTUM | SIG_MEAN_REV | SIG_VOL_REGIME | EQUAL_WEIGHT_SYSTEM | BTC B&H |
|---|---:|---:|---:|---:|---:|---:|
| Net Sharpe | 0.377674 | 0.533913 | -0.631104 | -0.099460 | 0.625799 | 0.466468 |
| Gross Sharpe | 0.546407 | 0.783991 | -0.068178 | 0.040878 | 0.998668 | 0.466468 |
| CAGR | 4.64% | 6.12% | -8.82% | -2.27% | 2.71% | 11.53% |
| Max DD | -16.09% | -12.51% | -18.71% | -21.62% | -3.95% | -49.53% |
| Sortino | 0.562184 | 0.833074 | -0.838497 | -0.135911 | 0.930058 | 0.687652 |
| Calmar | 0.287614 | 0.488199 | -0.470894 | -0.104666 | 0.683401 | 0.232334 |
| Win Rate | 49.51% | 49.02% | 46.72% | 50.82% | 51.15% | 50.49% |
| Profit Factor | 1.073728 | 1.103089 | 0.891063 | 0.983137 | 1.117769 | 1.072105 |
| Annual Turnover | 12.548408 | 15.616324 | 37.172195 | 9.577354 | 8.279067 | 0.000000 |
| Total Cost Drag | 4.20% | 5.23% | 12.45% | 3.21% | 2.77% | 0.00% |
| Cost Sharpe Drag | 0.168734 | 0.250078 | 0.562926 | 0.140339 | 0.372869 | 0.000000 |
| Total Return | 7.87% | 10.43% | -14.30% | -3.76% | 4.56% | 20.00% |
| Annual Volatility | 14.91% | 12.57% | 13.22% | 13.65% | 4.42% | 45.03% |

## pysystemtrade EWMAC Comparison
| Metric | H-310 Equal Weight | pysystemtrade EWMAC |
|---|---:|---:|
| Sharpe | 0.625799 | 0.617000 |
| CAGR | 2.71% | 12.31% |
| Max DD | -3.95% | -17.50% |
| Vol | 4.42% | 19.94% |

## Pass/Fail
| Criterion | Observed | Result |
|---|---|---|
| Net Sharpe >= 0.4 | 0.625799 >= 0.400000 | PASS |
| Net Sharpe > best single signal | 0.625799 > 0.533913 | PASS |
| Max DD less severe than BTC B&H | -3.95% vs -49.53% | PASS |
- Overall result: PASS

## Cost and Turnover
- Combination annual turnover: 8.279067
- Combination total cost drag: 2.77%
- Combination cost Sharpe drag: 0.372869

## Known Limitations
- Funding-rate cost is not included.
- The measurement covers only one BTCUSDT bull/bear cycle.
- The four-signal set contains redundant trend plus momentum exposure.
- No recommendation is made here to add, remove, or reweight signals.
