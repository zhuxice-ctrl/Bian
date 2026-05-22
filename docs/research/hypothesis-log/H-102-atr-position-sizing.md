# H-102 ATR Position Sizing

- Parent: H-101
- Change: add ATR risk-based position sizing
- Decision: inconclusive
- Reason: The run produced no incremental OOS improvement over the EMA200 risk-control variant.

## Description

Scale exposure by ATR stop distance and fixed risk per trade.

## Predicted

```json
{
  "oos_sharpe": 0.05,
  "max_drawdown": -0.01,
  "trade_count": 300
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
