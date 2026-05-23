# H-105 ATR Dynamic Stop Take Profit

- Parent: H-104
- Change: add ATR stop-loss and take-profit bands
- Decision: deferred
- Reason: Stop/take-profit simulation now exists, but this phase depends on deferred 5m trigger data coverage.

## Description

Attach ATR-based stop-loss and take-profit levels to each MTF Trend signal and simulate exits candle by candle on the primary timeframe.

## Predicted

```json
{
  "max_drawdown": -0.008,
  "oos_sharpe": 0.15,
  "trade_count": 160
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

Recounted with corrected trade_count semantic and cost model on 2026-05-23. Deferred until H-104 has valid synchronized 5m coverage.
