# H-212 Cross-Lookback Effective N Measurement

## Metadata
- Measurement type: methodology measurement, not alpha hypothesis
- Symbol: BTCUSDT
- Interval: 1d
- Price source: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Price window: 2024-05-23 ~ 2026-05-22
- Price rows: 730
- EWMAC aligned forecast window: 2025-10-11 ~ 2026-05-22
- EWMAC aligned forecast rows: 224
- H-210 comparison window: 2025-12-06 ~ 2026-05-22
- H-210 comparison rows: 168
- Output: `F:/Bian/exports/ablation-h212-cross-lookback-N_eff-2026-05-25.md`

## Six-Speed Pearson Correlation Matrix
| Signal | EWMAC_2_8 | EWMAC_4_16 | EWMAC_8_32 | EWMAC_16_64 | EWMAC_32_128 | EWMAC_64_256 |
|---|---:|---:|---:|---:|---:|---:|
| EWMAC_2_8 | 1.000000 | 0.853547 | 0.529325 | 0.210809 | -0.157573 | -0.383000 |
| EWMAC_4_16 | 0.853547 | 1.000000 | 0.840335 | 0.503505 | 0.008747 | -0.439879 |
| EWMAC_8_32 | 0.529325 | 0.840335 | 1.000000 | 0.854145 | 0.394399 | -0.282840 |
| EWMAC_16_64 | 0.210809 | 0.503505 | 0.854145 | 1.000000 | 0.770182 | 0.046221 |
| EWMAC_32_128 | -0.157573 | 0.008747 | 0.394399 | 0.770182 | 1.000000 | 0.616195 |
| EWMAC_64_256 | -0.383000 | -0.439879 | -0.282840 | 0.046221 | 0.616195 | 1.000000 |

## Equal-Weight Effective N
- Six EWMAC speeds: 2.444285
- Carver classic three-speed subset (EWMAC_8_32, EWMAC_16_64, EWMAC_64_256): 2.125122
- Six EWMAC speeds on the H-210 comparison window: 1.921235
- H-210 six cross-signal dimensions on the same comparison window: 10.703608

## Carver Three-Speed Pearson Correlation Matrix
| Signal | EWMAC_8_32 | EWMAC_16_64 | EWMAC_64_256 |
|---|---:|---:|---:|
| EWMAC_8_32 | 1.000000 | 0.854145 | -0.282840 |
| EWMAC_16_64 | 0.854145 | 1.000000 | 0.046221 |
| EWMAC_64_256 | -0.282840 | 0.046221 | 1.000000 |

## H-210 Comparison
| Measurement | Nominal Signals | N_eff |
|---|---:|---:|
| H-212 six EWMAC speeds | 6 | 2.444285 |
| H-212 Carver three EWMAC speeds | 3 | 2.125122 |
| H-212 six EWMAC speeds on H-210 comparison window | 6 | 1.921235 |
| H-210 six cross-signal dimensions on same comparison window | 6 | 10.703608 |

## Interpretation
On the shared comparison dates, six EWMAC speeds produced N_eff 1.92, while the six H-210 cross-signal dimensions produced N_eff 10.70; the cross-signal H-210 set measured higher diversification than the cross-speed EWMAC set. This is a structural correlation measurement only and does not evaluate returns, costs, capacity, or trading suitability.
