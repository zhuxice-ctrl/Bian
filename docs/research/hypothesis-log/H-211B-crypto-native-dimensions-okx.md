# H-211B Crypto Native Dimensions - OKX Funding Fallback

## Nature
This card records a blocked measurement stage for the OKX funding-rate fallback path. It is not an alpha result.

The goal was to replace the blocked Binance funding source from H-211 with OKX public funding-rate history for `BTC-USDT-SWAP`, then measure whether crypto-native funding signals add an independent dimension beyond price-only BTC trend signals.

## Stage A: Tooling Delivered
Status: `DELIVERED`

The local market-data tooling now has an OKX funding path:

- API client: `trading_learning.market_data.okx_data.fetch_funding_rate_history(symbol, start_ms, end_ms, max_pages=None)`
- Endpoint path: `GET https://www.okx.com/api/v5/public/funding-rate-history`
- OKX instrument mapping: `BTCUSDT` -> `BTC-USDT-SWAP`
- Pagination: uses `after=<oldest fundingTime from previous page>` to request older history
- CSV writer fields: `exchange`, `fundingTime`, `fundingRate`, `markPrice`, `instId`, `realizedRate`
- Catalog path: `data/local/market_data/{symbol}/funding/{symbol}-funding-okx.csv`
- Backfill CLI: `scripts/backfill_klines.py --exchange okx --data-type funding`
- Mock coverage: `tests/test_market_data_okx_funding.py`

Missing OKX fields are preserved as empty CSV cells rather than fabricated values.

## Stage B: Backfill Status
Status: `BLOCKED`

Attempted command:

`py scripts/backfill_klines.py --exchange okx --symbols BTCUSDT --data-type funding --years 2`

Requested window from the run:

- Start: `2024-05-25T06:00:00+00:00`
- End: `2026-05-25T06:00:00+00:00`
- Target file: `data/local/market_data/BTCUSDT/funding/BTCUSDT-funding-okx.csv`

Observed failure:

- HTTP status: `403 Forbidden`
- Response body: `error code: 1010`

No OKX funding CSV was generated, and no substitute or synthetic data was written.

## Stage C: Measurement Status
Status: `BLOCKED`

Planned signals remain the same as H-211:

- `SIG_FUNDING_LEVEL`: funding-rate z-score
- `SIG_FUNDING_MOMENTUM`: 7-day funding-rate change

The measurement stage must remain blocked until valid BTC-USDT-SWAP funding-rate history is present at:

`data/local/market_data/BTCUSDT/funding/BTCUSDT-funding-okx.csv`

## Third Path Recommendation
Treat the OKX failure as an environment/API-edge access block, not a data-quality result. The next path should be one of:

- Retry OKX from a server/network that can access `www.okx.com` public API without `403` / `1010`.
- Add another exchange funding source as H-211C, with mock-first coverage before implementation.
- Use a paid or archived market-data provider only if its raw funding rows include exchange, instrument, timestamp, and realized funding rate.

Any third path must still write raw 8h funding rows and must not infer funding data from price candles.
