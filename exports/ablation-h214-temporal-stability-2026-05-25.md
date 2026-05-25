# H-214 Signal Relation Temporal Stability

## Metadata
- Measurement type: methodology robustness check, not alpha hypothesis
- Symbol: BTCUSDT
- Interval: 1d
- Signal set: H-213 six expanding-normalized forecasts
- Data policy: local data only; no new data downloaded
- Price source: `F:/Bian/data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Price window: 2024-05-23 ~ 2026-05-22
- Full aligned window: 2024-09-19 ~ 2026-05-22
- Full aligned rows: 611
- First half: 2024-09-19 ~ 2025-07-20 (305 rows)
- Second half: 2025-07-21 ~ 2026-05-22 (306 rows)
- Output: `F:/Bian/exports/ablation-h214-temporal-stability-2026-05-25.md`

## Summary Metrics
| Window | Rows | Start | End | Signed N_eff | Absolute-Corr N_eff | PCA 90% Components |
|---|---:|---|---|---:|---:|---:|
| First Half | 305 | 2024-09-19 | 2025-07-20 | 6.548543 | 2.106446 | 4 |
| Second Half | 306 | 2025-07-21 | 2026-05-22 | 6.668203 | 1.731973 | 3 |
| Full H-213 Window | 611 | 2024-09-19 | 2026-05-22 | 5.197223 | 1.818016 | 4 |

## Pearson Matrices
### First Half
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | -0.097744 | 0.752120 | -0.697212 | 0.707486 | -0.143793 |
| SIG_TREND_SLOW | -0.097744 | 1.000000 | 0.073499 | 0.194661 | 0.181490 | -0.192293 |
| SIG_BREAKOUT | 0.752120 | 0.073499 | 1.000000 | -0.549964 | 0.737695 | -0.550870 |
| SIG_MEAN_REV | -0.697212 | 0.194661 | -0.549964 | 1.000000 | -0.355079 | -0.007407 |
| SIG_MOMENTUM | 0.707486 | 0.181490 | 0.737695 | -0.355079 | 1.000000 | -0.303887 |
| SIG_VOL_REGIME | -0.143793 | -0.192293 | -0.550870 | -0.007407 | -0.303887 | 1.000000 |

### Second Half
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | 0.160147 | 0.708561 | -0.605567 | 0.750878 | -0.410914 |
| SIG_TREND_SLOW | 0.160147 | 1.000000 | 0.642755 | 0.143851 | 0.409048 | -0.821921 |
| SIG_BREAKOUT | 0.708561 | 0.642755 | 1.000000 | -0.367091 | 0.713152 | -0.634819 |
| SIG_MEAN_REV | -0.605567 | 0.143851 | -0.367091 | 1.000000 | -0.326043 | 0.017682 |
| SIG_MOMENTUM | 0.750878 | 0.409048 | 0.713152 | -0.326043 | 1.000000 | -0.680340 |
| SIG_VOL_REGIME | -0.410914 | -0.821921 | -0.634819 | 0.017682 | -0.680340 | 1.000000 |

### Full H-213 Window
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | 0.234300 | 0.784283 | -0.661856 | 0.781296 | -0.258973 |
| SIG_TREND_SLOW | 0.234300 | 1.000000 | 0.560831 | 0.043720 | 0.462251 | -0.491923 |
| SIG_BREAKOUT | 0.784283 | 0.560831 | 1.000000 | -0.480107 | 0.800756 | -0.505810 |
| SIG_MEAN_REV | -0.661856 | 0.043720 | -0.480107 | 1.000000 | -0.389234 | 0.014709 |
| SIG_MOMENTUM | 0.781296 | 0.462251 | 0.800756 | -0.389234 | 1.000000 | -0.430854 |
| SIG_VOL_REGIME | -0.258973 | -0.491923 | -0.505810 | 0.014709 | -0.430854 | 1.000000 |

## Spearman Matrices
### First Half
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | -0.004824 | 0.771869 | -0.696545 | 0.721358 | -0.098223 |
| SIG_TREND_SLOW | -0.004824 | 1.000000 | 0.078015 | 0.204315 | 0.220033 | -0.223107 |
| SIG_BREAKOUT | 0.771869 | 0.078015 | 1.000000 | -0.667540 | 0.704893 | -0.445314 |
| SIG_MEAN_REV | -0.696545 | 0.204315 | -0.667540 | 1.000000 | -0.364036 | 0.011017 |
| SIG_MOMENTUM | 0.721358 | 0.220033 | 0.704893 | -0.364036 | 1.000000 | -0.271745 |
| SIG_VOL_REGIME | -0.098223 | -0.223107 | -0.445314 | 0.011017 | -0.271745 | 1.000000 |

### Second Half
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | 0.135892 | 0.743049 | -0.610646 | 0.753009 | -0.410307 |
| SIG_TREND_SLOW | 0.135892 | 1.000000 | 0.502302 | 0.151829 | 0.391752 | -0.863389 |
| SIG_BREAKOUT | 0.743049 | 0.502302 | 1.000000 | -0.470092 | 0.726391 | -0.634192 |
| SIG_MEAN_REV | -0.610646 | 0.151829 | -0.470092 | 1.000000 | -0.321159 | -0.018618 |
| SIG_MOMENTUM | 0.753009 | 0.391752 | 0.726391 | -0.321159 | 1.000000 | -0.651700 |
| SIG_VOL_REGIME | -0.410307 | -0.863389 | -0.634192 | -0.018618 | -0.651700 | 1.000000 |

### Full H-213 Window
| Signal | SIG_TREND_FAST | SIG_TREND_SLOW | SIG_BREAKOUT | SIG_MEAN_REV | SIG_MOMENTUM | SIG_VOL_REGIME |
|---|---:|---:|---:|---:|---:|---:|
| SIG_TREND_FAST | 1.000000 | 0.258343 | 0.806749 | -0.669345 | 0.796246 | -0.232173 |
| SIG_TREND_SLOW | 0.258343 | 1.000000 | 0.563983 | 0.045504 | 0.481190 | -0.466405 |
| SIG_BREAKOUT | 0.806749 | 0.563983 | 1.000000 | -0.533272 | 0.800458 | -0.481697 |
| SIG_MEAN_REV | -0.669345 | 0.045504 | -0.533272 | 1.000000 | -0.400622 | 0.006397 |
| SIG_MOMENTUM | 0.796246 | 0.481190 | 0.800458 | -0.400622 | 1.000000 | -0.412487 |
| SIG_VOL_REGIME | -0.232173 | -0.466405 | -0.481697 | 0.006397 | -0.412487 | 1.000000 |

## Pairwise Pearson Correlation Difference
| Pair | First Pearson | Second Pearson | Second - First | Abs Delta |
|---|---:|---:|---:|---:|
| SIG_TREND_SLOW / SIG_VOL_REGIME | -0.192293 | -0.821921 | -0.629628 | 0.629628 |
| SIG_TREND_SLOW / SIG_BREAKOUT | 0.073499 | 0.642755 | 0.569256 | 0.569256 |
| SIG_MOMENTUM / SIG_VOL_REGIME | -0.303887 | -0.680340 | -0.376453 | 0.376453 |
| SIG_TREND_FAST / SIG_VOL_REGIME | -0.143793 | -0.410914 | -0.267121 | 0.267121 |
| SIG_TREND_FAST / SIG_TREND_SLOW | -0.097744 | 0.160147 | 0.257891 | 0.257891 |
| SIG_TREND_SLOW / SIG_MOMENTUM | 0.181490 | 0.409048 | 0.227558 | 0.227558 |
| SIG_BREAKOUT / SIG_MEAN_REV | -0.549964 | -0.367091 | 0.182872 | 0.182872 |
| SIG_TREND_FAST / SIG_MEAN_REV | -0.697212 | -0.605567 | 0.091645 | 0.091645 |
| SIG_BREAKOUT / SIG_VOL_REGIME | -0.550870 | -0.634819 | -0.083949 | 0.083949 |
| SIG_TREND_SLOW / SIG_MEAN_REV | 0.194661 | 0.143851 | -0.050810 | 0.050810 |
| SIG_TREND_FAST / SIG_BREAKOUT | 0.752120 | 0.708561 | -0.043559 | 0.043559 |
| SIG_TREND_FAST / SIG_MOMENTUM | 0.707486 | 0.750878 | 0.043391 | 0.043391 |
| SIG_MEAN_REV / SIG_MOMENTUM | -0.355079 | -0.326043 | 0.029035 | 0.029035 |
| SIG_MEAN_REV / SIG_VOL_REGIME | -0.007407 | 0.017682 | 0.025088 | 0.025088 |
| SIG_BREAKOUT / SIG_MOMENTUM | 0.737695 | 0.713152 | -0.024543 | 0.024543 |

## Standalone Sharpe Comparison
| Item | First Half | Second Half | Full H-213 Window |
|---|---:|---:|---:|
| SIG_TREND_FAST | 1.023101 | 0.071780 | 0.564111 |
| SIG_TREND_SLOW | 0.556612 | -0.581295 | 0.025071 |
| SIG_BREAKOUT | 0.928528 | 0.160953 | 0.550528 |
| SIG_MEAN_REV | 0.103911 | 0.154135 | 0.128900 |
| SIG_MOMENTUM | 1.502561 | -0.205714 | 0.705570 |
| SIG_VOL_REGIME | -0.867160 | 1.396636 | 0.183381 |

## PCA Explained Variance Comparison
| Item | First Half | Second Half | Full H-213 Window |
|---|---:|---:|---:|
| PC1 | 0.508348 | 0.585697 | 0.569626 |
| PC2 | 0.230691 | 0.256994 | 0.229109 |
| PC3 | 0.132993 | 0.075189 | 0.087182 |
| PC4 | 0.080168 | 0.048347 | 0.066513 |
| PC5 | 0.026800 | 0.024240 | 0.027075 |
| PC6 | 0.021001 | 0.009534 | 0.020495 |

## Interpretation
This robustness check reports subwindow differences without making an overall stable/unstable call. The lowest Pearson absolute-delta relationship candidates are SIG_BREAKOUT / SIG_MOMENTUM (0.025), SIG_MEAN_REV / SIG_VOL_REGIME (0.025), SIG_MEAN_REV / SIG_MOMENTUM (0.029). The highest Pearson absolute-delta relationship candidates are SIG_TREND_SLOW / SIG_VOL_REGIME (0.630), SIG_TREND_SLOW / SIG_BREAKOUT (0.569), SIG_MOMENTUM / SIG_VOL_REGIME (0.376). Use the tables above for Cascade review of whether those differences are economically meaningful; this card does not accept, reject, or modify any signal.
