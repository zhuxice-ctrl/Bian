# H-341 Funding Rate Cost Estimation

## Nature
This card is a cost-estimation task, not signal development.

It estimates how Binance BTCUSDT perpetual funding rates would have affected the H-311 four-signal FDM system. It does not modify the H-311 system, the backtest engine, paper trading, or any signal definition.

## Background
H-211 and H-211B were blocked by API reachability. Binance access is now available, so H-341 fetches actual BTCUSDT perpetual funding-rate history and applies it as an additional daily return adjustment to the H-311 position series.

Funding sign convention:

- Long position plus positive funding: cost.
- Long position plus negative funding: income.
- Short position plus positive funding: income.
- Short position plus negative funding: cost.

## Data
- Symbol: BTCUSDT perpetual.
- Source: Binance USD-M funding-rate public endpoint.
- Raw frequency: 8h funding events.
- Local file: `data/local/market_data/BTCUSDT/funding/BTCUSDT-funding-rate.csv`
- Required system window: `2024-09-19 ~ 2026-05-22`

## Method
1. Backfill funding-rate rows from Binance.
2. Aggregate 8h rows to daily funding by summing all events in each UTC day.
3. Recompute the H-311 combined forecast and backtest positions without changing the strategy.
4. Compute daily funding PnL return as `-position * daily_funding_rate`.
5. Add funding PnL return to the H-311 trading-cost-adjusted daily returns.
6. Recalculate Sharpe, CAGR, max drawdown, and related diagnostics.

## Report
Output path:

`exports/ablation-h341-funding-cost-estimation-2026-05-25.md`

The report must include:

- Funding-rate data statistics: mean, median, standard deviation, positive proportion, negative proportion.
- Average daily funding cost based on the system positions.
- Annualized funding drag.
- A three-column comparison table: H-311 original, H-311 plus trading cost plus funding, BTC buy-and-hold.
- Sharpe, CAGR, and max drawdown changes.
- Pass/fail result.

## Pass Standard
H-341 passes only if both conditions hold:

1. Funding CSV is non-empty and covers the H-311 system window `2024-09-19 ~ 2026-05-22`.
2. Funding-adjusted net Sharpe is greater than `0.3`.

If H-341 fails, the next engineering task is to add funding-aware position adjustment to the system.

## Scope Guardrails
- Do not modify H-311 system logic.
- Do not modify the backtest engine.
- Do not modify paper trading.
- Do not treat funding as a new signal in this card.
