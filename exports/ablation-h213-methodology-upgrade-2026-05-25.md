# H-213 Signal Dimension Methodology Upgrade

## Metadata
- Measurement type: methodology correction, not alpha hypothesis
- Symbol: BTCUSDT
- Interval: 1d
- Data policy: local data only; no new data downloaded
- Price source: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Price window: 2024-05-23 ~ 2026-05-22
- Price rows: 730
- Signal definitions: same six H-210 price-derived forecasts
- Normalization: expanding mean absolute signal, available from day 60
- Aligned forecast window: 2024-09-19 ~ 2026-05-22
- Aligned forecast rows: 611
- H-210 report retained at: `F:/Bian/exports/ablation-h210-signal-correlation-N_eff-2026-05-25.md`
- Output: `F:/Bian/exports/ablation-h213-methodology-upgrade-2026-05-25.md`

## Pearson Correlation Matrix
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | 0.234300 | 0.784283 | -0.661856 | 0.781296 | -0.258973 |
| SIG_TREND_SLOW | 0.234300 | 1.000000 | 0.560831 | 0.043720 | 0.462251 | -0.491923 |
| SIG_BREAKOUT | 0.784283 | 0.560831 | 1.000000 | -0.480107 | 0.800756 | -0.505810 |
| SIG_MEAN_REV | -0.661856 | 0.043720 | -0.480107 | 1.000000 | -0.389234 | 0.014709 |
| SIG_MOMENTUM | 0.781296 | 0.462251 | 0.800756 | -0.389234 | 1.000000 | -0.430854 |
| SIG_VOL_REGIME | -0.258973 | -0.491923 | -0.505810 | 0.014709 | -0.430854 | 1.000000 |

## Spearman Correlation Matrix
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | 0.258343 | 0.806749 | -0.669345 | 0.796246 | -0.232173 |
| SIG_TREND_SLOW | 0.258343 | 1.000000 | 0.563983 | 0.045504 | 0.481190 | -0.466405 |
| SIG_BREAKOUT | 0.806749 | 0.563983 | 1.000000 | -0.533272 | 0.800458 | -0.481697 |
| SIG_MEAN_REV | -0.669345 | 0.045504 | -0.533272 | 1.000000 | -0.400622 | 0.006397 |
| SIG_MOMENTUM | 0.796246 | 0.481190 | 0.800458 | -0.400622 | 1.000000 | -0.412487 |
| SIG_VOL_REGIME | -0.232173 | -0.466405 | -0.481697 | 0.006397 | -0.412487 | 1.000000 |

## Effective N Estimates
- Signed equal-weight N_eff: 5.197223
- Absolute-correlation equal-weight N_eff: 1.818016

## PCA Explained Variance
| Item | Explained Variance |
|---|---:|
| PC1 | 0.569626 |
| PC2 | 0.229109 |
| PC3 | 0.087182 |
| PC4 | 0.066513 |
| PC5 | 0.027075 |
| PC6 | 0.020495 |

## Effective Dimension Threshold
- Threshold: 90% cumulative explained variance
- Components required: 4

## Standalone Sharpe by Signal
| Item | Standalone Sharpe |
|---|---:|
| SIG_TREND_FAST | 0.564111 |
| SIG_TREND_SLOW | 0.025071 |
| SIG_BREAKOUT | 0.550528 |
| SIG_MEAN_REV | 0.128900 |
| SIG_MOMENTUM | 0.705570 |
| SIG_VOL_REGIME | 0.183381 |

## H-210 vs H-213 Comparison
| Measurement | Window | Rows | Estimate Type | Value |
|---|---|---:|---|---:|
| H-210 published | 2025-12-06 ~ 2026-05-22 | 168 | signed N_eff | 10.703608 |
| H-213 upgraded | 2024-09-19 ~ 2026-05-22 | 611 | signed N_eff | 5.197223 |
| H-213 upgraded | 2024-09-19 ~ 2026-05-22 | 611 | absolute-correlation N_eff | 1.818016 |
| H-213 upgraded | 2024-09-19 ~ 2026-05-22 | 611 | PCA 90% components | 4 |

## Interpretation
H-210's 10.7 was pushed up by a negative-correlation artifact: the signed formula counted structural negative correlation as if it were additional independent breadth, especially between trend-like and mean-reversion-like forecasts in a short 168-day reversal window. With expanding normalization, the aligned window is much longer and the signed risk-diversification estimate is 5.20, while the absolute-correlation estimate is 1.82 and PCA needs 4 components to explain 90% of forecast variance. In this upgraded window, the credible structural dimension estimate is therefore not one number: signed risk dimension is 5.20, no-hedge absolute-correlation dimension is 1.82, and PCA 90% dimension is 4. Risk diversification and alpha diversification are different concepts: negative correlation can reduce portfolio risk, but it does not prove that a mechanically opposite forecast is an independent alpha source. Standalone Sharpe is reported only as a descriptive, no-cost alpha diagnostic; no signal is accepted, rejected, or removed by this card.
