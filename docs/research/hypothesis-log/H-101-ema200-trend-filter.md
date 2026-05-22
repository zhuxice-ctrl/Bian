# H-101 EMA200 Trend Filter

- Parent: H-100
- Change: add EMA200 trend filter
- Decision: risk_reduction_kept
- Reason: The filter removed drawdown in this short local OOS sample, but Sharpe improvement was not statistically convincing.

## Description

Only allow long exposure when the 1h close is above EMA200.

## Predicted

```json
{
  "oos_sharpe": 0.35,
  "max_drawdown": -0.035,
  "trade_count": 350
}
```

## Actual

```json
{
  "consistency_score": 0.0,
  "max_drawdown": 0.0,
  "oos_sharpe": 0.0,
  "oos_trade_count": 582,
  "p_value_vs_parent": 0.7996653497,
  "sharpe_diff_vs_parent": -0.1669923438,
  "total_return": 0.0,
  "windows": 6
}
```
