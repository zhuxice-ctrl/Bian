# H-105 ATR Dynamic Stop Take Profit

- Parent: H-104
- Change: add ATR stop-loss and take-profit bands
- Decision: inconclusive
- Reason: Stop/take-profit metadata is implemented, but the current vectorized OOS runner does not yet simulate intrabar exits.

## Description

Attach ATR-based stop-loss and take-profit levels to each MTF Trend signal.

## Predicted

```json
{
  "oos_sharpe": 0.15,
  "max_drawdown": -0.008,
  "trade_count": 160
}
```

## Actual

```json
{
  "consistency_score": 0.0,
  "max_drawdown": 0.0,
  "oos_sharpe": 0.0,
  "oos_trade_count": 582,
  "p_value_vs_parent": 1.0,
  "sharpe_diff_vs_parent": 0.0,
  "total_return": 0.0,
  "windows": 6
}
```
