# H-205A · BTC/BNB Pairs Extension

## Predicted (事前)
- Cointegration p-value: uncertain, expected weaker than BTC/ETH
- Half-life: 80-300 periods if cointegrated
- OOS Sharpe: 0.0-0.4
- Win rate: 50-60%
- Trade count: 15-35/year
- Reasoning: BNB has exchange-token idiosyncratic risk, so BTC/BNB may not mean-revert as cleanly as BTC/ETH.

## Setup
- Pair: BTCUSDT / BNBUSDT
- Timeframe: 1h
- Base variant: H-204 rules
- Evaluation rule: independent hypothesis, no portfolio aggregation

## Actual (事后)
- Available BTCUSDT 1h data: 1000 bars
- Available BNBUSDT 1h data: missing
- Required data: at least 2 years synchronized data for both legs
- OOS Sharpe: not run
- Win rate: not run
- Trade count: not run

## Decision
deferred

## Hindsight
- 哪里和预测一致：This pair could not be included without its own complete dataset.
- 哪里出乎意料：No BNBUSDT local 1h data exists.
- 学到了什么：H-205 cannot borrow BTC/ETH results or be collapsed into a portfolio.
- 下一个假设的灵感：Ingest BNBUSDT 1h data before registering a runnable extension.

## 2026-05-23 重跑结果
- 数据：见 ablation-pairs-2026-05-23-rerun.md
- 状态：fail
- 关键指标：17520 synchronized 1h bars; cointegration p=0.5000; half-life=2590.33 periods; Sharpe/Max DD/Trade Count not run because pair gate failed.

## 2026-05-23 H-207 方法论修正后重跑
- 数据：见 ablation-pairs-2026-05-23-rerun2-h207-methodology.md
- 状态：fail
- 关键指标：continuous p-value=0.7617; prior bucket p-value=0.5000; ADF stat=-1.5412; half-life=2590.33 periods; pair gate failed and no walk-forward was run.
