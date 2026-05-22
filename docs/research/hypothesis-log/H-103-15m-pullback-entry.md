# H-103 15m Pullback Entry

- Parent: H-102
- Change: add 15m pullback condition
- Decision: inconclusive
- Reason: The current local 1h walk-forward runner cannot prove incremental value for the 15m pullback filter yet.

## Description

Require a recent 15m RSI/price pullback before accepting the 1h trend entry.

## Predicted

```json
{
  "oos_sharpe": 0.1,
  "max_drawdown": -0.01,
  "trade_count": 220
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
