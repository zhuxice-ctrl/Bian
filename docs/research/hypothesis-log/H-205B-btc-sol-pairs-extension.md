# H-205B · BTC/SOL Pairs Extension

## Predicted (事前)
- Cointegration p-value: uncertain, likely regime-dependent
- Half-life: 60-280 periods if cointegrated
- OOS Sharpe: 0.0-0.5
- Win rate: 50-62%
- Trade count: 20-45/year
- Reasoning: SOL beta to BTC can drift materially across market regimes, so H-204 gating may matter more than for BTC/ETH.

## Setup
- Pair: BTCUSDT / SOLUSDT
- Timeframe: 1h
- Base variant: H-204 rules
- Evaluation rule: independent hypothesis, no portfolio aggregation

## Actual (事后)
- Available BTCUSDT 1h data: 1000 bars
- Available SOLUSDT 1h data: missing
- Required data: at least 2 years synchronized data for both legs
- OOS Sharpe: not run
- Win rate: not run
- Trade count: not run

## Decision
deferred

## Hindsight
- 哪里和预测一致：SOL requires an independent card and was not cherry-picked.
- 哪里出乎意料：No SOLUSDT local 1h data exists.
- 学到了什么：Missing data is a valid research outcome when the preregistered rule says defer.
- 下一个假设的灵感：Collect SOLUSDT first, then rerun without changing thresholds.
