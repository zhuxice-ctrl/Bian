# H-101 EMA200 Trend Filter

- Parent: H-100
- Change: add EMA200 trend filter
- Decision: rejected
- Reason: The filter avoided the weak baseline but over-filtered to zero OOS trades, so it is not a usable strategy variant.

## Description

Only allow long exposure when the 1h close is above EMA200.

## Predicted

```json
{
  "max_drawdown": -0.035,
  "oos_sharpe": 0.35,
  "trade_count": 350
}
```

## Actual

```json
{
  "bar_count": 582,
  "consistency_score": 0.0,
  "cost_model": {
    "fee_rate": 0.0008,
    "latency_rate": 0.0002,
    "order_type": "market",
    "slippage_rate": 0.0005
  },
  "deferred_windows": 0,
  "max_drawdown": 0.0,
  "oos_bar_count": 582,
  "oos_sharpe": 0.0,
  "oos_trade_count": 0,
  "p_value_vs_parent": 0.2072510069,
  "sharpe_diff_vs_parent": 0.8298682652,
  "total_return": 0.0,
  "windows": 6
}
```

## Hindsight Notes

Recounted with corrected trade_count semantic and cost model on 2026-05-23. Zero OOS trades means this cannot be kept as a real variant.
