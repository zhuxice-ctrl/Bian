# H-202 · BTC/ETH Add Half-Life Filter

## Predicted (事前)
- Cointegration p-value: < 0.05 in tradable windows
- Half-life threshold: skip windows above 240 periods
- OOS Sharpe: higher than H-201 if slow spreads are filtered out
- Win rate: similar or slightly higher than H-201
- Trade count: lower than H-201
- Reasoning: A spread that reverts too slowly is unlikely to overcome two-leg costs at 1h frequency.

## Setup
- Pair: BTCUSDT / ETHUSDT
- Timeframe: 1h
- Hedge ratio: static OLS
- Z-score window: 96
- Entry/Exit/Stop: |z| > 2 / |z| < 0.3 / |z| > 3.5
- Half-life filter: skip training windows with half-life > 240 periods
- Variable changed from H-201: half-life filter only

## Actual (事后)
- Available synchronized data: 1000 hourly bars
- Data range: 2026-04-11 03:00 UTC to 2026-05-22 18:00 UTC
- Available-sample half-life: 139.49 periods
- Required data: at least 2 years
- OOS Sharpe: not run
- Average trade expectancy: not run
- Trade count: not run

## Decision
deferred

## Hindsight
- 哪里和预测一致：The half-life estimator works on synthetic OU data and the available BTC/ETH sample.
- 哪里出乎意料：The available-sample half-life would pass, but cointegration and data length fail.
- 学到了什么：A half-life pass alone is not a research decision.
- 下一个假设的灵感：Keep this filter unchanged after data collection and only compare against H-201.

## 2026-05-23 重跑结果
- 数据：见 ablation-pairs-2026-05-23-rerun.md
- 状态：not_applicable
- 关键指标：BTC/ETH H-200 entry gate failed first (cointegration p=0.5000; half-life=3431.18 periods), so half-life-filter ablation was not run.
