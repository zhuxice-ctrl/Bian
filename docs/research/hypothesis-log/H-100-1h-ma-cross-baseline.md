# H-100 1h MA Cross Baseline

- Parent: baseline
- Change: single 1h MA cross reference model
- Decision: kept
- Reason: Kept as the reference baseline only; OOS Sharpe is weak and not tradable.

## Description

Use a single-timeframe 1h moving-average pull-through baseline before adding any MTF filters.

## Predicted

```json
{
  "oos_sharpe": 0.2,
  "max_drawdown": -0.05,
  "trade_count": 500
}
```

## Actual

```json
{
  "consistency_score": 0.5,
  "max_drawdown": -0.0479134288,
  "oos_sharpe": 0.1669923438,
  "oos_trade_count": 582,
  "total_return": 0.0116637343,
  "windows": 6
}
```
