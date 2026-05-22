# Hypothesis Log

This folder stores human-readable research cards for preregistered strategy changes.

Each card must include:

- `Predicted`: the before-run forecast.
- `Actual`: numeric results from the run.
- `Decision`: one of `kept`, `rejected`, `inconclusive`, `risk_reduction_kept`.
- `Reason`: one sentence explaining the decision.

CLI:

```powershell
trading-learning hypothesis-create --title "Add EMA200 trend filter" --change-summary "+EMA200" --predicted "{\"sharpe\":0.85}" --decision-rule "Keep if OOS improves"
trading-learning hypothesis-resolve H-001 --actual "{\"sharpe\":0.80}" --decision risk_reduction_kept --reason "Drawdown improved."
trading-learning hypothesis-list
trading-learning hypothesis-tree
```
