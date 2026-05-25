# H-312 Signal Subset Optimization

## Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Common aligned window: 2024-09-19 ~ 2026-05-22
- Rows: 611
- Combination: equal weights + FDM, then clip to [-2, 2]
- Capital: 100,000
- Vol target: 20.00%
- Vol lookback: 60
- Cost: 0.20% round trip
- Max leverage: 2.0x

## Subsets
| Label | Description | Signals |
|---|---|---|
| A | MOMENTUM + VOL_REGIME | SIG_MOMENTUM, SIG_VOL_REGIME |
| B | TREND_FAST + MOMENTUM + VOL_REGIME | SIG_TREND_FAST, SIG_MOMENTUM, SIG_VOL_REGIME |
| C | MOMENTUM + VOL_REGIME + MEAN_REV_SLOW | SIG_MOMENTUM, SIG_VOL_REGIME, SIG_MEAN_REV_SLOW |
| D | TREND_FAST + MOMENTUM + VOL_REGIME + MEAN_REV_SLOW | SIG_TREND_FAST, SIG_MOMENTUM, SIG_VOL_REGIME, SIG_MEAN_REV_SLOW |
| E | H-311 original four-signal FDM baseline | SIG_TREND_FAST, SIG_MOMENTUM, SIG_MEAN_REV, SIG_VOL_REGIME |

## Seven-Column Metric Comparison
| Metric | A | B | C | D | E | BTC B&H | pysystemtrade EWMAC |
|---|---:|---:|---:|---:|---:|---:|---:|
| Net Sharpe | 0.520039 | 0.555775 | -0.176755 | 0.322803 | 0.625799 | 0.466468 | 0.617000 |
| Gross Sharpe | 0.755927 | 0.755756 | 0.061088 | 0.555568 | 0.998668 | 0.466468 | n/a |
| CAGR | 6.08% | 7.13% | -2.96% | 3.43% | 7.13% | 11.53% | 12.31% |
| Max DD | -11.00% | -14.07% | -15.83% | -12.42% | -10.61% | -49.53% | -17.50% |
| Sortino | 0.772253 | 0.854685 | -0.251158 | 0.469174 | 0.930058 | 0.687652 | n/a |
| Calmar | 0.551618 | 0.505536 | -0.186452 | 0.275276 | 0.670368 | 0.232334 | n/a |
| Win Rate | 50.82% | 50.33% | 50.66% | 51.31% | 51.15% | 50.49% | n/a |
| Profit Factor | 1.094397 | 1.110873 | 0.970768 | 1.058715 | 1.117769 | 1.072105 | n/a |
| Annual Turnover | 15.136823 | 14.132914 | 14.904245 | 15.196518 | 22.797226 | 0.000000 | n/a |
| Total Cost Drag | 5.07% | 4.73% | 4.99% | 5.09% | 7.63% | 0.00% | n/a |
| Cost Sharpe Drag | 0.235888 | 0.199982 | 0.237844 | 0.232766 | 0.372869 | 0.000000 | n/a |
| Total Return | 10.37% | 12.19% | -4.89% | 5.79% | 12.19% | 20.00% | n/a |
| Annual Volatility | 12.93% | 14.16% | 12.52% | 13.05% | 12.16% | 45.03% | 19.94% |

## FDM, Turnover, Cost, and Realized Vol
| Subset | FDM | Annual Turnover | Total Cost Drag | Realized Vol |
|---|---:|---:|---:|---:|
| A | 1.874577 | 15.136823 | 5.07% | 12.93% |
| B | 1.681540 | 14.132914 | 4.73% | 14.16% |
| C | 2.517120 | 14.904245 | 4.99% | 12.52% |
| D | 3.045044 | 15.196518 | 5.09% | 13.05% |
| E | 2.753598 | 22.797226 | 7.63% | 12.16% |

## MEAN_REV Speed Comparison
| Signal | Window | Net Sharpe | Annual Turnover | Total Cost Drag | Realized Vol |
|---|---:|---:|---:|---:|---:|
| SIG_MEAN_REV | 20 | -0.631104 | 37.172195 | 12.45% | 13.22% |
| SIG_MEAN_REV_SLOW | 120 | -0.883633 | 14.849058 | 4.97% | 13.69% |

## Rank by Net Sharpe
| Rank | Subset | Net Sharpe | Annual Turnover | Realized Vol |
|---:|---|---:|---:|---:|
| 1 | E | 0.625799 | 22.797226 | 12.16% |
| 2 | B | 0.555775 | 14.132914 | 14.16% |
| 3 | A | 0.520039 | 15.136823 | 12.93% |
| 4 | D | 0.322803 | 15.196518 | 13.05% |
| 5 | C | -0.176755 | 14.904245 | 12.52% |

## Pass/Fail
- At least one subset Net Sharpe > E baseline (0.625799): FAIL
- At least one subset Annual Turnover < E baseline (22.797226): PASS
- Overall result: FAIL

## Mechanical Best Eligible Subset
- Highest net Sharpe among subsets with turnover < 15x: subset B (Net Sharpe 0.555775, Annual Turnover 14.132914).

## Known Limitations
- This is in-sample only.
- The measurement covers one symbol and one BTCUSDT market cycle.
- Funding-rate cost is not included.
- This card ranks observed subset metrics but does not make a final signal inclusion or exclusion recommendation.
