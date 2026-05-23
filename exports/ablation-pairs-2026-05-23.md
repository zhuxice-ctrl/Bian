# C2 Pairs Trading Ablation Report · 2026-05-23

## Data Gate
- Required: synchronized BTCUSDT + ETHUSDT 1h data for at least 2 years.
- Available: 1000 synchronized hourly bars.
- Range: 2026-04-11 03:00 UTC to 2026-05-22 18:00 UTC.
- Result: all H-200 through H-204 walk-forward experiments deferred.

## Available-Sample Diagnostics
- Pair: BTCUSDT / ETHUSDT
- Static beta: 0.2315
- Cointegration p-value: 0.5000
- Half-life: 139.49 periods
- Latest z-score: -1.7408
- Interpretation: the short sample fails the p <= 0.05 cointegration gate and is far below the minimum data length.

## Ablation Table

| Hypothesis | Pair | Variable Changed | Result | Reason |
|---|---|---|---|---|
| H-200 | BTCUSDT/ETHUSDT | Static beta baseline | deferred | insufficient 2-year synchronized data; available-sample p=0.5000 |
| H-201 | BTCUSDT/ETHUSDT | Add |z| > 3.5 stop | deferred | baseline cannot run honestly |
| H-202 | BTCUSDT/ETHUSDT | Add half-life <= 240 filter | deferred | no valid walk-forward windows |
| H-203 | BTCUSDT/ETHUSDT | Rolling beta | deferred | no valid walk-forward windows |
| H-204 | BTCUSDT/ETHUSDT | Cointegration recheck | deferred | available-sample p-value fails gate |
| H-205A | BTCUSDT/BNBUSDT | Extend to BTC/BNB | deferred | BNBUSDT 1h data missing |
| H-205B | BTCUSDT/SOLUSDT | Extend to BTC/SOL | deferred | SOLUSDT 1h data missing |
| H-205C | BNBUSDT/SOLUSDT | Extend to BNB/SOL | deferred | BNBUSDT and SOLUSDT 1h data missing |

## Anti Cherry-Picking Notes
- No alternate pairs were searched after the BTC/ETH gate failed.
- H-205 pairs are listed individually and marked deferred rather than omitted.
- No portfolio aggregation was performed.
- No thresholds were changed after seeing the data gate result.

## Next Action
Collect at least 2 years of synchronized 1h BTCUSDT and ETHUSDT data, then rerun H-200 unchanged before any further ablation.
