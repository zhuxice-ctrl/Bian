# H-341 Funding Rate Cost Estimation

## Setup
- Symbol: BTCUSDT perpetual
- Interval: 1d system positions, 8h funding observations
- Price data: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Funding data: `F:/Bian/data/local/market_data/BTCUSDT/funding/BTCUSDT-funding-rate.csv`
- Funding source path: data_archive_fallback
- System window: 2024-09-19 ~ 2026-05-22
- Rows: 611
- H-311 FDM: 2.753598
- Funding adjustment: `funding_pnl = -position * daily_funding_rate`

## Funding Rate Data Statistics
| Item | Value |
|---|---:|
| Rows | 1821 |
| First Timestamp | 2024-09-01T00:00:00+00:00 |
| Last Timestamp | 2026-04-30T16:00:00+00:00 |
| Mean 8h Funding | 0.0047% (0.47 bp) |
| Median 8h Funding | 0.0046% (0.46 bp) |
| Std 8h Funding | 0.0061% (0.61 bp) |
| Positive Ratio | 81.55% |
| Negative Ratio | 18.45% |
| Mean Daily Funding | 0.0142% (1.42 bp) |

## Data Coverage
- Required coverage: 2024-09-19 00:00 UTC through 2026-05-22 16:00 UTC
- Observed coverage: 2024-09-01T00:00:00+00:00 through 2026-04-30T16:00:00+00:00
- Coverage result: FAIL

## Funding Cost Impact
- Average absolute system position: 0.237719
- Average daily funding cost: 0.0005% (0.05 bp)
- Annualized funding drag: 0.17%
- Total funding drag over window: 0.28%

## Metric Comparison
| Metric | H-311 Original | H-311 + Trading Cost + Funding | BTC B&H |
|---|---:|---:|---:|
| Net Sharpe | 0.625799 | 0.612242 | 0.466468 |
| CAGR | 7.13% | 6.95% | 11.53% |
| Max DD | -10.61% | -10.22% | -49.53% |
| Sortino | 0.930058 | 0.907868 | 0.687652 |
| Calmar | 0.670368 | 0.678807 | 0.232334 |
| Win Rate | 51.15% | 50.82% | 50.49% |
| Profit Factor | 1.117769 | 1.115094 | 1.072105 |
| Annual Turnover | 22.797226 | 22.797226 | 0.000000 |
| Total Trading Cost Drag | 7.63% | 7.63% | 0.00% |
| Total Return | 12.19% | 11.88% | 20.00% |
| Annual Volatility | 12.16% | 12.16% | 45.03% |

## Metric Changes
| Metric | H-311 Original | Funding Adjusted | Difference |
|---|---:|---:|---:|
| Sharpe | 0.625799 | 0.612242 | -0.013557 |
| CAGR | 7.13% | 6.95% | -0.18% |
| Max DD | -10.61% | -10.22% | 0.39% |

## Pass/Fail
- Data coverage: FAIL
- Funding-adjusted net Sharpe > 0.3: 0.612242 > 0.3 => PASS
- Overall result: FAIL

## Interpretation
- Funding is treated strictly as a cost/income adjustment, not as a predictive input.
- The funding-adjusted Sharpe test passes on the available Binance funding data.
- The overall card remains failed because this environment could not retrieve May 2026 funding rows from the REST endpoint, and Binance's public archive has only closed months through 2026-04.
- Do not make a funding-aware system change from this partial-coverage result alone; rerun through VPN or another reachable Binance REST path to complete the pass standard.
