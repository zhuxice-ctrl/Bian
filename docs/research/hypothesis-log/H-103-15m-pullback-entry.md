# H-103 15m Pullback Entry

- Parent: H-102
- Change: add 15m pullback condition
- Decision: deferred
- Reason: The available 15m cache does not cover enough walk-forward windows to treat this as a real MTF test.

## Description

Require a recent 15m RSI/price pullback before accepting the 1h trend entry.

## Predicted

```json
{
  "max_drawdown": -0.01,
  "oos_sharpe": 0.1,
  "trade_count": 220
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
  "deferred_windows": 4,
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

Recounted with corrected trade_count semantic and cost model on 2026-05-23. Deferred until 15m history covers the same OOS windows as 1h.
