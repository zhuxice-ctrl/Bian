# H-300 Donchian 趋势策略 Ablation 报告

## 卡片元信息
- Symbol：BTCUSDT
- Interval：1d
- 时间窗口：2024-05-23 ~ 2026-05-22
- 数据条数：730
- 参数族：N=20, N=40, N=60

## Donchian 参数族 Metrics
| 参数 | Sharpe | Sortino | Calmar | Max DD | CAGR | Volatility | Win Rate | Profit Factor | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N=20 | -0.016585 | -0.023960 | -0.014098 | -46.26% | -0.65% | 39.02% | 35.48% | 0.985750 | 31 |
| N=40 | -0.411673 | -0.581138 | -0.255637 | -78.46% | -20.06% | 39.97% | 28.57% | 0.650331 | 21 |
| N=60 | 0.285591 | 0.421211 | 0.356785 | -26.35% | 9.40% | 35.88% | 55.56% | 1.765560 | 9 |

## Buy-and-Hold Benchmark
| Benchmark | Sharpe | Sortino | Calmar | Max DD | CAGR | Volatility | Win Rate | Profit Factor | Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| simple | 0.082104 | 0.116521 | 0.075051 | -49.53% | 3.72% | 46.83% | 100.00% | inf | 1 |
| compounded | 0.285209 | 0.420710 | 0.075051 | -49.53% | 3.72% | 38.01% | 100.00% | inf | 1 |

## Pass/Fail 判定
| 参数 | Sharpe ≥ 0.3 | Max DD ≤ 60% | Trades ≥ 10 | PF ≥ 1.2 | Overall |
|---|---|---|---|---|---|
| N=20 | Fail | Pass | Pass | Fail | Fail |
| N=40 | Fail | Fail | Pass | Fail | Fail |
| N=60 | Fail | Pass | Fail | Pass | Fail |

总体结论：Fail

阈值未调整，判定按 H-300 卡片机械执行。
