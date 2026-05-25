# H-312 Signal Subset Optimization

## Nature
This card is an in-sample signal subset measurement under the H-311 FDM framework.

It is not a final signal selection decision and does not make a recommendation to add, remove, or permanently reweight signals.

## Background
H-311 added FDM and restored realized volatility from the H-310 no-FDM level of `4.42%` to above the H-311 `12%` restoration threshold.

H-312 measures whether alternative subsets improve the FDM-adjusted system while addressing two known issues:

- `SIG_TREND_FAST` and `SIG_MOMENTUM` are strongly correlated in prior signal-structure work.
- `SIG_MEAN_REV(20d)` has very high turnover and was cost-dominated in the single-signal backtest.

## Tested Subsets
All subsets use equal weights, FDM, the same volatility-targeting engine, and the same cost model.

| Label | Signals | Purpose |
|---|---|---|
| A | `SIG_MOMENTUM`, `SIG_VOL_REGIME` | Maximum simplicity and removal of trend/momentum duplication |
| B | `SIG_TREND_FAST`, `SIG_MOMENTUM`, `SIG_VOL_REGIME` | Retain trend duplication to test whether it still adds value |
| C | `SIG_MOMENTUM`, `SIG_VOL_REGIME`, `SIG_MEAN_REV_SLOW` | Combine three different signal logics with slower mean reversion |
| D | `SIG_TREND_FAST`, `SIG_MOMENTUM`, `SIG_VOL_REGIME`, `SIG_MEAN_REV_SLOW` | Keep all four broad roles but replace fast mean reversion with slow mean reversion |
| E | `SIG_TREND_FAST`, `SIG_MOMENTUM`, `SIG_MEAN_REV`, `SIG_VOL_REGIME` | H-311 original four-signal FDM baseline |

## MEAN_REV_SLOW Definition
`SIG_MEAN_REV_SLOW` is `mean_reversion_forecast(price, window=120, normalization="expanding")` renamed for reporting.

It is intended to measure whether slower mean reversion reduces turnover versus the 20-day version. This card does not decide whether it should be used in production.

## Backtest Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data source: `data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Window: common aligned window across all H-312 signals
- Capital: `100,000`
- Vol target: `20%`
- Vol lookback: `60`
- Max leverage: `2x`
- Cost model: `0.2%` round trip
- Forecast combination: equal weights plus FDM, clipped to `[-2, 2]`
- Benchmark: BTC buy-and-hold over the same aligned window

## Pass Standard
H-312 passes if both are true:

1. At least one subset has net Sharpe greater than the H-311 baseline subset E.
2. At least one subset has annual turnover lower than the H-311 baseline subset E.

The best subset is identified mechanically as the highest net Sharpe among subsets with annual turnover below `15x`. This is an in-sample rank only, not a final adoption decision.

## Output
Report path:

`exports/ablation-h312-signal-subset-optimization-2026-05-25.md`

The report must include:
- Seven-column metric comparison: A, B, C, D, E, BTC buy-and-hold, and known pysystemtrade EWMAC.
- FDM, annual turnover, total cost drag, and realized volatility for each subset.
- `SIG_MEAN_REV(20d)` versus `SIG_MEAN_REV_SLOW(120d)` turnover comparison.
- Subset rank by net Sharpe.
- Known limitations: in-sample only, one instrument, one cycle, and no funding-rate cost.
- No final signal inclusion or exclusion recommendation.

## Scope
- Do not modify H-200 through H-311 cards or reports.
- Do not download new data.
- Do not modify strategy or cointegration code.
