# H-310 Equal-Weight Four-Signal System

## Nature
This card is a strategy system hypothesis.

It combines the four H-301 through H-304 single-signal forecasts into the first complete Carver-style BTCUSDT system in this repository.

## Background
H-301 through H-304 measured four standalone signals with the same volatility targeting and cost model:

- `SIG_TREND_FAST`
- `SIG_MOMENTUM`
- `SIG_MEAN_REV`
- `SIG_VOL_REGIME`

H-310 tests whether equal-weight forecast combination improves the system-level risk-adjusted result versus the single-signal baselines.

## Combination Logic
Combined forecast:

`mean(SIG_TREND_FAST, SIG_MOMENTUM, SIG_MEAN_REV, SIG_VOL_REGIME)`

The combined forecast is then passed through the same `backtest_forecast()` vol-target and cost pipeline used in H-301 through H-304.

## Backtest Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data source: `data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Window: H-213 expanding aligned window, `2024-09-19 ~ 2026-05-22`
- Capital: `100,000`
- Vol target: `20%`
- Vol lookback: `60`
- Max leverage: `2x`
- Cost model: `0.2%` round trip
- Benchmark: BTC buy-and-hold over the same window

## Pass Standard
H-310 passes only if all three are true:

1. Net Sharpe is at least `0.4`.
2. Net Sharpe is greater than the best of H-301, H-302, H-303, and H-304.
3. Max drawdown is smaller than BTC buy-and-hold max drawdown in absolute severity.

If the system passes, it supports feasibility of a Carver-style signal combination in this crypto window.

If it fails, the four signals in this window are insufficient to produce a combination advantage under this model.

## Output
Report path:

`exports/ablation-h310-equal-weight-system-2026-05-25.md`

The report must include:
- Six-column metric comparison: four single signals, equal-weight system, BTC buy-and-hold.
- Comparison with known pysystemtrade EWMAC metrics.
- Pass/fail result for each criterion.
- Annual turnover and cost drag.
- Known limitations: funding-rate cost is excluded, only one bull/bear cycle, and the four-signal set includes redundant trend plus momentum exposure.
- No recommendation to add, remove, or reweight signals.

## Scope
- Do not modify H-200 through H-304 cards or reports.
- Do not modify backtest engine, forecast library, or other existing modules.
- Do not download new data.
