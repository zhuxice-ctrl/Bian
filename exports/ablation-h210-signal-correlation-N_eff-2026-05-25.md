# H-210 Signal Dimension Effective N Measurement

## Metadata
- Measurement type: methodology measurement, not alpha hypothesis
- Symbol: BTCUSDT
- Interval: 1d
- Price source: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Price window: 2024-05-23 ~ 2026-05-22
- Price rows: 730
- Aligned forecast window: 2025-12-06 ~ 2026-05-22
- Aligned forecast rows: 168
- Output: `F:/Bian/exports/ablation-h210-signal-correlation-N_eff-2026-05-25.md`

## Signal Set
- SIG_TREND_FAST
- SIG_TREND_SLOW
- SIG_BREAKOUT
- SIG_MEAN_REV
- SIG_MOMENTUM
- SIG_VOL_REGIME

## Pearson Correlation Matrix
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | 0.046045 | 0.778733 | -0.631954 | 0.799755 | -0.602829 |
| SIG_TREND_SLOW | 0.046045 | 1.000000 | -0.081368 | 0.147499 | 0.182711 | -0.683555 |
| SIG_BREAKOUT | 0.778733 | -0.081368 | 1.000000 | -0.563207 | 0.781126 | -0.488551 |
| SIG_MEAN_REV | -0.631954 | 0.147499 | -0.563207 | 1.000000 | -0.401295 | 0.181576 |
| SIG_MOMENTUM | 0.799755 | 0.182711 | 0.781126 | -0.401295 | 1.000000 | -0.783009 |
| SIG_VOL_REGIME | -0.602829 | -0.683555 | -0.488551 | 0.181576 | -0.783009 | 1.000000 |

## Spearman Correlation Matrix
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | -0.003377 | 0.825135 | -0.630347 | 0.797701 | -0.656866 |
| SIG_TREND_SLOW | -0.003377 | 1.000000 | -0.203433 | 0.167133 | 0.298063 | -0.554590 |
| SIG_BREAKOUT | 0.825135 | -0.203433 | 1.000000 | -0.671077 | 0.640178 | -0.457242 |
| SIG_MEAN_REV | -0.630347 | 0.167133 | -0.671077 | 1.000000 | -0.378444 | 0.150455 |
| SIG_MOMENTUM | 0.797701 | 0.298063 | 0.640178 | -0.378444 | 1.000000 | -0.863985 |
| SIG_VOL_REGIME | -0.656866 | -0.554590 | -0.457242 | 0.150455 | -0.863985 | 1.000000 |

## Equal-Weight Effective N
- Equal weights: SIG_TREND_FAST=1/6, SIG_TREND_SLOW=1/6, SIG_BREAKOUT=1/6, SIG_MEAN_REV=1/6, SIG_MOMENTUM=1/6, SIG_VOL_REGIME=1/6
- N_eff: 10.703608

## Three Lowest Absolute Pearson Correlation Pairs
| Rank | Signal A | Signal B | Pearson | Abs Pearson |
|---:|---|---|---:|---:|
| 1 | SIG_TREND_FAST | SIG_TREND_SLOW | 0.046045 | 0.046045 |
| 2 | SIG_TREND_SLOW | SIG_BREAKOUT | -0.081368 | 0.081368 |
| 3 | SIG_TREND_SLOW | SIG_MEAN_REV | 0.147499 | 0.147499 |

## Interpretation
The six BTCUSDT forecast dimensions have mean absolute Pearson correlation 0.477, which produces an equal-weight N_eff of 10.70 versus six nominal signals. The least-overlapping pairs by absolute Pearson correlation are SIG_TREND_FAST/SIG_TREND_SLOW, SIG_TREND_SLOW/SIG_BREAKOUT, SIG_TREND_SLOW/SIG_MEAN_REV. This describes the measured signal-dimension structure only; it does not evaluate expected returns, transaction costs, capacity, or whether any signal should be traded.
