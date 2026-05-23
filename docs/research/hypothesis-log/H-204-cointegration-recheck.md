# H-204 · BTC/ETH Cointegration Recheck

## Predicted (事前)
- Cointegration p-value: skip windows with p > 0.05
- Half-life: below 240 periods in enabled windows
- OOS Sharpe: kept or risk_reduction_kept versus H-203
- Max drawdown: better than H-203 if regime breaks occur
- Trade count: lower than H-203
- Reasoning: Rechecking cointegration per walk-forward training window should avoid trading after spread relationships break.

## Setup
- Pair: BTCUSDT / ETHUSDT
- Timeframe: 1h
- Hedge ratio: rolling OLS, 240-period target window
- Z-score window: 96
- Entry/Exit/Stop: |z| > 2 / |z| < 0.3 / |z| > 3.5
- Filters: cointegration p <= 0.05 and half-life <= 240 periods per training window
- Variable changed from H-203: explicit cointegration recheck gating only

## Actual (事后)
- Available synchronized data: 1000 hourly bars
- Data range: 2026-04-11 03:00 UTC to 2026-05-22 18:00 UTC
- Cointegration p-value on available sample: 0.5000
- Required data: at least 2 years
- OOS Sharpe: not run
- Max drawdown: not run
- Trade count: not run

## Decision
deferred

## Hindsight
- 哪里和预测一致：The available sample would be skipped by the cointegration gate.
- 哪里出乎意料：The gate failed even before the data-length rule was satisfied.
- 学到了什么：Cointegration recheck is a hard guardrail, not a tunable result-improvement knob.
- 下一个假设的灵感：Do not loosen p-value to force trades; collect enough data first.
