# H-311 FDM Vol Restoration

## Nature
This card is a methodology and system correction.

It does not delete, modify, or backfill H-310. H-310 remains the no-FDM equal-weight baseline. H-311 produces a separate report that tests whether adding a Forecast Diversification Multiplier restores realized volatility toward the intended risk budget.

## Background
H-310 passed its system-level criteria, but the equal-weight four-signal system realized only `4.42%` annual volatility against a `20%` target.

The likely mechanism is forecast cancellation. The combined forecast was:

`mean(SIG_TREND_FAST, SIG_MOMENTUM, SIG_MEAN_REV, SIG_VOL_REGIME)`

When forecasts with partially offsetting signs are averaged directly, the combined forecast can spend most of its time near zero. The downstream volatility-targeting engine then receives a small forecast and produces low exposure, even though the portfolio risk budget is higher.

## FDM Method
Forecast Diversification Multiplier:

`FDM = 1 / sqrt(w' @ rho @ w)`

Where:
- `w` is the forecast weight vector.
- `rho` is the Pearson correlation matrix of forecast time series.
- The H-311 test uses equal weights across the four H-310 signals.

Adjusted combined forecast:

`combined_forecast = clip(raw_equal_weight_forecast * FDM, -2, 2)`

The `[-2, 2]` cap is retained because the local forecast library uses a small normalized forecast scale rather than Carver's `[-20, 20]` scale.

## Backtest Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data source: `data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Window: H-213/H-310 expanding aligned window, `2024-09-19 ~ 2026-05-22`
- Capital: `100,000`
- Vol target: `20%`
- Vol lookback: `60`
- Max leverage: `2x`
- Cost model: `0.2%` round trip
- Benchmark: BTC buy-and-hold over the same window

## Pass Standard
H-311 passes only if both are true:

1. Realized annual volatility after FDM is at least `12%`.
2. Net Sharpe is not materially below H-310, defined as no worse than `0.05` below H-310 net Sharpe.

Using the H-310 no-FDM net Sharpe of `0.625799`, the Sharpe preservation threshold is `0.575799`.

## Output
Report path:

`exports/ablation-h311-fdm-vol-restoration-2026-05-25.md`

The report must include:
- FDM calculation value.
- Four-signal forecast Pearson correlation matrix.
- Three-column metric comparison: H-310 no FDM, H-311 with FDM, and BTC buy-and-hold.
- Vol restoration result.
- Sharpe preservation result.
- Overall pass/fail.

## Scope
- Do not modify H-200 through H-310 cards or reports.
- Do not modify `forecast_library`.
- Do not download new data.
