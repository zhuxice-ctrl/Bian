# H-102 ATR Position Sizing

- Parent: H-101
- Change: add ATR risk-based position sizing
- Decision: inconclusive
- Reason: The parent filter produced no OOS trades, so ATR sizing has no independent evidence yet.

## Description

Scale exposure by ATR stop distance and fixed risk per trade.

## Predicted

```json
{
  "max_drawdown": -0.01,
  "oos_sharpe": 0.05,
  "trade_count": 300
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
  "p_value_vs_parent": 1.0,
  "sharpe_diff_vs_parent": 0.0,
  "total_return": 0.0,
  "windows": 6
}
```

## Hindsight Notes

Recounted with corrected trade_count semantic and cost model on 2026-05-23. This phase needs a parent variant that actually trades.
