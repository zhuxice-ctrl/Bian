# H-203 · BTC/ETH Dynamic Hedge Ratio

## Predicted (事前)
- Cointegration p-value: < 0.05 in enabled windows
- Half-life: below 240 periods in enabled windows
- OOS Sharpe: 50/50 versus H-202
- Win rate: similar to H-202
- Trade count: similar to H-202
- Reasoning: Rolling beta may help during beta drift, but BTC/ETH beta changes can be small enough that added noise hurts.

## Setup
- Pair: BTCUSDT / ETHUSDT
- Timeframe: 1h
- Hedge ratio: rolling OLS, 240-period target window
- Z-score window: 96
- Entry/Exit/Stop: |z| > 2 / |z| < 0.3 / |z| > 3.5
- Half-life filter: half-life <= 240 periods
- Variable changed from H-202: rolling beta only

## Actual (事后)
- Available synchronized data: 1000 hourly bars
- Data range: 2026-04-11 03:00 UTC to 2026-05-22 18:00 UTC
- Required data: at least 2 years
- OOS Sharpe: not run
- Win rate: not run
- Trade count: not run

## Decision
deferred

## Hindsight
- 哪里和预测一致：Rolling beta functionality is covered by synthetic-data tests.
- 哪里出乎意料：No valid OOS windows exist to evaluate whether dynamic beta helps.
- 学到了什么：Dynamic hedge ratio should not be evaluated on one short continuous sample.
- 下一个假设的灵感：After H-202 is valid, test rolling beta without changing z-score or filters.
