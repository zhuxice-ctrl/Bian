# H-104 5m Trigger Confirmation

- Parent: H-103
- Change: add 5m trigger confirmation
- Decision: deferred
- Reason: The available 5m cache does not cover any full walk-forward OOS window in this run.

## Description

Require the 5m trigger timeframe to confirm upward momentum before entry.

## Predicted

```json
{
  "max_drawdown": -0.01,
  "oos_sharpe": 0.12,
  "trade_count": 180
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
  "deferred_windows": 6,
  "max_drawdown": 0.0,
  "oos_bar_count": 582,
  "oos_sharpe": 0.0,
  "oos_trade_count": 0,
  "p_value_vs_parent": 1.0,
  "sharpe_diff_vs_parent": 0.0,
  "total_return": 0.0,
  "windows": 6
}
```

## Hindsight Notes

Recounted with corrected trade_count semantic and cost model on 2026-05-23. Deferred until 5m history covers the same OOS windows as 1h/15m.
