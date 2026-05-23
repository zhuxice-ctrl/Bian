# C2 Pairs Trading Ablation Rerun 2 · H-207 Methodology Correction · 2026-05-23

## 报告定位

本报告是 H-207 方法论修正（methodology correction）的产出。
- 唯一变化：ADF p-value 实现从 4 桶分类升级为连续值
- 数据未变：沿用 H-206 backfill 的 17520 根 1h 数据
- 阈值未变：协整 gate 仍为 p ≤ 0.05、half-life ≤ 240
- H 卡未变：H-200~H-205 卡正文全部保留

本报告**不**是新研究结论。
若新工具下 BTC/ETH 仍 fail，与 rerun.md 的结论一致；
若新工具下 BTC/ETH 出现边界 pass，也不构成做单依据——
那种情况需开新研究分支（H-208）独立评估，不在本报告范围内。

## Data Source
- Source: H-206 backfill tooling.
- Interval: 1h.
- Data rows per file: 17520.
- Range for all four symbols: 2024-05-23 09:00 UTC to 2026-05-23 08:00 UTC.

## Methodology Change
- Previous ADF p-value output: bucket mapping `0.01 / 0.049 / 0.10 / 0.50`.
- H-207 ADF p-value output: continuous MacKinnon-style interpolation calibrated to the same critical-value region.
- Bucket p-value remains reported for auditability.

## Walk-Forward Gate
- Train window: 365 days.
- Test window: 90 days.
- Step: 90 days.
- Purge: 5 days.
- Walk-forward only runs after the preregistered pair gate passes.

## Ablation Results

| Hypothesis | Pair | ADF stat | Continuous p-value | Prior bucket p-value | Half-life | Sharpe | Max DD | Trade Count | Result | Reason |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| H-200 | BTCUSDT/ETHUSDT | -1.7545 | 0.6481 | 0.5000 | 3431.18 | n/a | n/a | n/a | fail | Gate failed under continuous p-value and half-life |
| H-201 | BTCUSDT/ETHUSDT | -1.7545 | 0.6481 | 0.5000 | 3431.18 | n/a | n/a | n/a | not_applicable | H-200 BTC/ETH gate failed, so downstream ablation was not run |
| H-202 | BTCUSDT/ETHUSDT | -1.7545 | 0.6481 | 0.5000 | 3431.18 | n/a | n/a | n/a | not_applicable | H-200 BTC/ETH gate failed, so downstream ablation was not run |
| H-203 | BTCUSDT/ETHUSDT | -1.7545 | 0.6481 | 0.5000 | 3431.18 | n/a | n/a | n/a | not_applicable | H-200 BTC/ETH gate failed, so downstream ablation was not run |
| H-204 | BTCUSDT/ETHUSDT | -1.7545 | 0.6481 | 0.5000 | 3431.18 | n/a | n/a | n/a | not_applicable | H-200 BTC/ETH gate failed, so downstream ablation was not run |
| H-205A | BTCUSDT/BNBUSDT | -1.5412 | 0.7617 | 0.5000 | 2590.33 | n/a | n/a | n/a | fail | Independent pair gate failed |
| H-205B | BTCUSDT/SOLUSDT | -1.5892 | 0.7546 | 0.5000 | 3482.02 | n/a | n/a | n/a | fail | Independent pair gate failed |
| H-205C | BNBUSDT/SOLUSDT | -1.7098 | 0.6819 | 0.5000 | 2178.08 | n/a | n/a | n/a | fail | Independent pair gate failed |

## Anti Cherry-Picking Statement
- No alternate pairs were searched after the gate.
- Multi-pair extensions listed individually.
- No portfolio aggregation.
- No thresholds changed after seeing results.

## Observed
- BTC/ETH remains fail under continuous p-value: 0.6481.
- The H-207 continuous p-values are more expressive than the prior 0.5000 bucket, but no pair moved near the p ≤ 0.05 gate.
- Half-life remains far above 240 periods for every evaluated pair.
- This report is a methodology correction output, not a basis for new trading conclusions.
