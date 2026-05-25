# H-320 Walk-Forward Validation

## Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Full aligned window: 2024-09-19 ~ 2026-05-22
- Full rows: 611
- Split rule: `len // 2`
- Train FDM is estimated on Train and frozen for Test.
- Capital: 100,000
- Vol target: 20.00%
- Vol lookback: 60
- Cost: 0.20% round trip
- Max leverage: 2.0x

## Train/Test Windows
| Split | Start | End | Rows |
|---|---|---|---:|
| Train | 2024-09-19 | 2025-07-20 | 305 |
| Test | 2025-07-21 | 2026-05-22 | 306 |

## FDM Drift
- FDM_train: 2.581871
- FDM_test: 3.275401
- Drift: 26.86%

## Metric Comparison
| Metric | Train System | Test System | Train B&H | Test B&H |
|---|---:|---:|---:|---:|
| Net Sharpe | 0.693865 | 0.443084 | 1.847503 | -0.977409 |
| Gross Sharpe | 1.064955 | 0.838377 | 1.847503 | -0.977409 |
| CAGR | 8.16% | 4.33% | 111.06% | -40.99% |
| Max DD | -6.63% | -6.06% | -28.10% | -49.53% |
| Sortino | 1.000022 | 0.681158 | 3.000840 | -1.314571 |
| Calmar | 1.225806 | 0.711945 | 3.934537 | -0.825463 |
| Win Rate | 51.97% | 50.49% | 52.96% | 47.87% |
| Profit Factor | 1.129080 | 1.082885 | 1.319804 | 0.864671 |
| Annual Turnover | 22.989990 | 21.652755 | 0.000000 | 0.000000 |
| Total Cost Drag | 3.84% | 3.63% | 0.00% | 0.00% |
| Cost Sharpe Drag | 0.371090 | 0.395292 | 0.000000 | 0.000000 |
| Total Return | 6.75% | 3.61% | 86.29% | -35.65% |
| Annual Volatility | 12.37% | 10.86% | 46.00% | 43.87% |

## Sharpe Decay
- Train net Sharpe: 0.693865
- Test net Sharpe: 0.443084
- Test / Train Sharpe: 0.638574

## Pass/Fail
| Criterion | Observed | Result |
|---|---|---|
| Test Net Sharpe > 0.0 | 0.443084 > 0.000000 | PASS |
| Test Net Sharpe > -0.3 | 0.443084 > -0.300000 | PASS |
| FDM drift < 30% | 26.86% < 30.00% | PASS |
- Overall result: PASS

## Known Limitations
- This is one train/test split, not k-fold or repeated walk-forward validation.
- The test period is a specific regime: BTC bull-market top plus correction.
- FDM is the only frozen fitted parameter; signal parameters are theory-driven and not fitted in this card.
- No system modification recommendation is made here.
