# H-211 Crypto Native Dimensions

## Nature
This card is a methodology measurement plan with a blocked measurement stage, not an alpha hypothesis.

The goal is to measure whether crypto-native dimensions such as funding rate provide independent information versus BTC price-trend forecasts. The required funding-rate data could not be acquired from the specified Binance Futures API in this environment, so the measurement stage is blocked rather than filled with substitute data.

## Background
- H-209 showed that adding crypto instruments alone produced low effective diversification.
- H-210 moved diversification measurement from instrument dimension to signal dimension.
- This card tests whether crypto-native data can add another independent dimension beyond price-only signals.

## Stage A: Tooling Delivered
The local market data tooling now supports funding-rate history:

- API client: `fetch_funding_rate_history(symbol, start_ms, end_ms)`
- Endpoint path: `GET /fapi/v1/fundingRate`
- CSV writer fields: `fundingTime`, `fundingRate`, `markPrice`
- Catalog path: `data/local/market_data/{symbol}/funding/{symbol}-funding.csv`
- Backfill CLI: `scripts/backfill_klines.py --data-type funding`
- Mock test coverage: `tests/test_market_data_funding.py`

Funding data remains at its original 8h frequency. Any later comparison to daily price signals should forward-fill funding forecasts to the daily price index.

## Stage B: Backfill Status
Status: `BLOCKED`

Attempted command:

`py -3 scripts/backfill_klines.py --symbols BTCUSDT --data-type funding --years 2 --no-backup`

Requested window from the run:

- Start: `2024-05-25T05:00:00+00:00`
- End: `2026-05-25T05:00:00+00:00`

Observed failure:

`HTTP Error 451`

No funding CSV was generated, and no substitute or synthetic data was written.

## Stage C: Measurement Status
Status: `BLOCKED`

Planned signals:

- `SIG_FUNDING_LEVEL`: funding rate z-score
- `SIG_FUNDING_MOMENTUM`: 7-day funding-rate change

Planned measurement:

- Correlation of `SIG_FUNDING_LEVEL` with H-210 `SIG_TREND_FAST` and `SIG_TREND_SLOW`
- Equal-weight `N_eff` across all H-210 signals plus the two funding signals

This stage must remain blocked until a valid BTCUSDT funding-rate history is present at:

`data/local/market_data/BTCUSDT/funding/BTCUSDT-funding.csv`

## Scope
- Do not hard-code funding data.
- Do not infer funding history from price data.
- Do not resample funding data to daily storage; keep 8h raw rows.
- Basis data is intentionally out of scope for this card.
