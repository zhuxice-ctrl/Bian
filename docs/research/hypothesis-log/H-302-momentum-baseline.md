# H-302 Momentum Baseline

## Nature
This card is a single-signal baseline backtest hypothesis.

It tests whether the BTCUSDT daily 60-day momentum forecast has standalone value after volatility targeting and a simple trading cost model.

## Signal
- Name: `SIG_MOMENTUM`
- Definition: `momentum_forecast(price, lookback=60, normalization="expanding")`
- Forecast range: normalized to `[-1, 1]`
- Source module: `trading_learning.signals.forecast_library`

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

## Prior Measurement Note
H-214 reported standalone Sharpe for this signal as regime-dependent: first half `1.50`, second half `-0.21`.

## Pass Standard
Pass if net Sharpe is at least `0.3`.

## Output
Report path:

`exports/ablation-h302-momentum-2026-05-25.md`

The report must include:
- Signal description and parameters
- Backtest window and row count
- Net and gross performance metrics
- BTC buy-and-hold comparison
- Pass/fail result
- Known limitation: funding-rate cost is not included

## Scope
- Do not modify H-200 through H-214 cards or reports.
- Do not modify signal definitions.
- Do not make signal selection decisions; defer selection to H-310 and later cards.
