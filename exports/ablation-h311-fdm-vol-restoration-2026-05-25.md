# H-311 FDM Vol Restoration

## Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Window: 2024-09-19 ~ 2026-05-22
- Rows: 611
- Signals: SIG_TREND_FAST, SIG_MOMENTUM, SIG_MEAN_REV, SIG_VOL_REGIME
- FDM formula: `1 / sqrt(w' @ rho @ w)`
- Forecast cap after FDM: +/-2.0
- Capital: 100,000
- Vol target: 20.00%
- Vol lookback: 60
- Cost: 0.20% round trip
- Max leverage: 2.0x

## FDM
- FDM value: 2.753598

## Forecast Pearson Correlation Matrix
| | SIG_TREND_FAST | SIG_MOMENTUM | SIG_MEAN_REV | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | 0.781296 | -0.661856 | -0.258973 |
| SIG_MOMENTUM | 0.781296 | 1.000000 | -0.389234 | -0.430854 |
| SIG_MEAN_REV | -0.661856 | -0.389234 | 1.000000 | 0.014709 |
| SIG_VOL_REGIME | -0.258973 | -0.430854 | 0.014709 | 1.000000 |

## Metric Comparison
| Metric | H-310 No FDM | H-311 FDM | BTC B&H |
|---|---:|---:|---:|
| Net Sharpe | 0.625799 | 0.625799 | 0.466468 |
| Gross Sharpe | 0.998668 | 0.998668 | 0.466468 |
| CAGR | 2.71% | 7.13% | 11.53% |
| Max DD | -3.95% | -10.61% | -49.53% |
| Sortino | 0.930058 | 0.930058 | 0.687652 |
| Calmar | 0.683401 | 0.670368 | 0.232334 |
| Win Rate | 51.15% | 51.15% | 50.49% |
| Profit Factor | 1.117769 | 1.117769 | 1.072105 |
| Annual Turnover | 8.279067 | 22.797226 | 0.000000 |
| Total Cost Drag | 2.77% | 7.63% | 0.00% |
| Cost Sharpe Drag | 0.372869 | 0.372869 | 0.000000 |
| Total Return | 4.56% | 12.19% | 20.00% |
| Annual Volatility | 4.42% | 12.16% | 45.03% |

## Vol Restoration
- Standard: annual volatility >= 12.00%
- Observed: 12.16%
- Result: PASS

## Sharpe Preservation
- Standard: net Sharpe >= 0.575799 (H-310 net Sharpe - 0.05)
- Observed: 0.625799
- Result: PASS

## Pass/Fail
- Overall result: PASS

## Interpretation
- H-310 is retained as the no-FDM baseline.
- H-311 tests whether forecast scaling restores risk usage after signal cancellation.
- No signal add/remove/reweight decision is made in this card.
