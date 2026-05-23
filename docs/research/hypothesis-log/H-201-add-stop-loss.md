# H-201 · BTC/ETH Add Stop Loss

## Predicted (事前)
- Cointegration p-value: < 0.05
- Half-life: 50-200 periods
- OOS Sharpe: similar to H-200
- Win rate: slightly below H-200
- Max drawdown: materially better than H-200
- Trade count: similar to H-200
- Reasoning: |z| > 3.5 exits should cut broken-spread tails but may close some trades near local extremes.

## Setup
- Pair: BTCUSDT / ETHUSDT
- Timeframe: 1h
- Hedge ratio: static OLS
- Z-score window: 96
- Entry/Exit: |z| > 2 / |z| < 0.3
- Stop loss: |z| > 3.5
- Variable changed from H-200: add stop loss only

## Actual (事后)
- Available synchronized data: 1000 hourly bars
- Data range: 2026-04-11 03:00 UTC to 2026-05-22 18:00 UTC
- Required data: at least 2 years
- OOS Sharpe: not run
- Max drawdown: not run
- Win rate: not run
- Trade count: not run

## Decision
deferred

## Hindsight
- 哪里和预测一致：Stop-loss behavior is implemented and unit-tested, including open-position stop triggering.
- 哪里出乎意料：No valid OOS windows exist, so risk-reduction claims would be cherry-picking.
- 学到了什么：Risk-control ablations still require the same data threshold as alpha variants.
- 下一个假设的灵感：Once H-200 can run, compare drawdown and Sharpe without changing thresholds.

## 2026-05-23 重跑结果
- 数据：见 ablation-pairs-2026-05-23-rerun.md
- 状态：not_applicable
- 关键指标：BTC/ETH H-200 entry gate failed first (cointegration p=0.5000; half-life=3431.18 periods), so stop-loss ablation was not run.
