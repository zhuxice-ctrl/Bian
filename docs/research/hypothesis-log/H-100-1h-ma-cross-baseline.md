# H-100 1h MA Cross Baseline

- Parent: baseline
- Change: single 1h MA cross reference model
- Decision: kept
- Reason: Kept as the reference baseline only; corrected cost-aware OOS result is weak and not tradable.

## Description

Use a single-timeframe 1h moving-average pull-through baseline before adding any MTF filters.

## Predicted

```json
{
  "max_drawdown": -0.05,
  "oos_sharpe": 0.2,
  "trade_count": 500
}
```

## Actual

```json
{
  "bar_count": 582,
  "consistency_score": 0.3333333333,
  "cost_model": {
    "fee_rate": 0.0008,
    "latency_rate": 0.0002,
    "order_type": "market",
    "slippage_rate": 0.0005
  },
  "deferred_windows": 0,
  "max_drawdown": -0.1000116449,
  "oos_bar_count": 582,
  "oos_sharpe": -0.8298682652,
  "oos_trade_count": 28,
  "total_return": -0.0671656142,
  "windows": 6
}
```

## Hindsight Notes

Recounted with corrected trade_count semantic and cost model on 2026-05-23. Old actual used OOS bar count as trade count.
