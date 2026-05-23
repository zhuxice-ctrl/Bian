# H-200 · BTC/ETH Static Pairs Baseline

## Predicted (事前)
- Cointegration p-value: < 0.05
- Half-life: 50-200 periods
- OOS Sharpe: 0.3-0.6
- Win rate: 55-65%
- Trade count: 20-40/year
- Reasoning: BTC/ETH historical correlation is high, but 1h spread edge is expected to be weak after real two-leg costs.

## Setup
- Pair: BTCUSDT / ETHUSDT
- Timeframe: 1h
- Hedge ratio: static OLS on the in-sample training window
- Z-score window: 96
- Entry/Exit: |z| > 2 / |z| < 0.3
- Stop loss: disabled
- Half-life filter: disabled
- Walk-forward target: 365d train / 90d test / 90d step / 5d purge

## Actual (事后)
- Available synchronized data: 1000 hourly bars
- Data range: 2026-04-11 03:00 UTC to 2026-05-22 18:00 UTC
- Required data: at least 2 years of synchronized 1h BTCUSDT + ETHUSDT
- Cointegration p-value on available sample: 0.5000
- Half-life on available sample: 139.49 periods
- OOS Sharpe: not run
- Win rate: not run
- Trade count: not run

## Decision
deferred

## Hindsight
- 哪里和预测一致：BTC/ETH spread half-life landed inside the expected range on the short sample.
- 哪里出乎意料：Available data is only about 42 days, so the required walk-forward research cannot start honestly.
- 学到了什么：Data sufficiency must be checked before any pair result is interpreted.
- 下一个假设的灵感：After collecting at least 2 years, rerun this unchanged baseline before any ablation.
