# H-330 Paper Trading Infrastructure

## Nature
This card is an engineering task, not a strategy hypothesis or alpha test.

It creates the Bian v1 paper-trading infrastructure for daily signal generation, position tracking, and hypothetical PnL logging. It does not modify the strategy rules validated in H-311/H-320.

## Background
H-320 completed the minimum train/test walk-forward validation for the H-311 system:

- Four equal-weight signals
- FDM-adjusted combined forecast
- Volatility-targeted position sizing
- Cost model included

The next step is to collect live out-of-sample observations without placing real orders. H-330 creates a daily paper-trading pipeline that reads the locally maintained BTCUSDT 1d CSV, computes the current signal set, calculates the target position, and records hypothetical PnL.

## Scope
Included:

- `src/trading_learning/paper_trading/signal_generator.py`
- `src/trading_learning/paper_trading/position_tracker.py`
- `src/trading_learning/paper_trading/daily_runner.py`
- `scripts/paper_trade.py`
- `data/paper_trading/config.json`
- `data/paper_trading/latest_signals.json`
- `data/paper_trading/portfolio_state.csv`

Excluded:

- No strategy modification.
- No automatic data fetching.
- No exchange connectivity.
- No live order routing.
- No funding-rate cost model change.

## Data Flow
`BTCUSDT-1d.csv -> signal_generator -> position_tracker -> portfolio_state.csv`

## Default Configuration
- Symbol: BTCUSDT
- Interval: 1d
- Price source: `data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Paper state directory: `data/paper_trading/`
- Capital: `100,000`
- Cost: `0.2%` round trip
- Target volatility: `20%`
- Vol lookback: `60`
- Max leverage: `2x`
- Forecast cap: `[-2, 2]`
- Default FDM: `2.753598`, from H-311

## CLI
Normal daily run:

`python scripts/paper_trade.py`

Initialize from historical aligned window:

`python scripts/paper_trade.py --backfill`

Print current status:

`python scripts/paper_trade.py --status`

Print records since a date:

`python scripts/paper_trade.py --since 2026-05-01`

## Acceptance Criteria
- `python scripts/paper_trade.py --backfill` runs successfully.
- Backfill final equity aligns with the H-311 FDM backtest within the required tolerance.
- `python scripts/paper_trade.py --status` prints the latest equity, cumulative PnL, and target position.
- `pytest -q` passes.

## Current Backfill Snapshot
The initialized backfill contains `611` daily rows over the H-311 aligned window.

Latest state:

- Date: `2026-05-22`
- Equity: `112191.29`
- Cumulative PnL: `12191.29`
- Target position: `0.215879`

This matches the H-311 total-return scale of approximately `12.19%`.

## Operating Notes
- The user manually updates `BTCUSDT-1d.csv`.
- The daily command appends one new paper state row based on the latest available local data.
- If no explicit `--fdm` is provided, the runner uses `data/paper_trading/config.json` when present, otherwise the H-311 default FDM.
- The paper portfolio assumes perfect execution at daily close and records cost as `abs(position_change) * cost_per_round_trip`.
