# H-205C · BNB/SOL Pairs Extension

## Predicted (事前)
- Cointegration p-value: uncertain and likely unstable
- Half-life: 80-360 periods if cointegrated
- OOS Sharpe: -0.1 to 0.4
- Win rate: 48-60%
- Trade count: 15-40/year
- Reasoning: BNB and SOL have different fundamental drivers, so this is more exploratory and likely weaker than BTC/ETH.

## Setup
- Pair: BNBUSDT / SOLUSDT
- Timeframe: 1h
- Base variant: H-204 rules
- Evaluation rule: independent hypothesis, no portfolio aggregation

## Actual (事后)
- Available BNBUSDT 1h data: missing
- Available SOLUSDT 1h data: missing
- Required data: at least 2 years synchronized data for both legs
- OOS Sharpe: not run
- Win rate: not run
- Trade count: not run

## Decision
deferred

## Hindsight
- 哪里和预测一致：The pair was listed explicitly instead of hidden because data was unavailable.
- 哪里出乎意料：Both legs are missing locally.
- 学到了什么：H-205 remains deferred until every independent pair has sufficient data.
- 下一个假设的灵感：Only add this pair after both datasets exist at the required length.
