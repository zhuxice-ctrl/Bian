# H-320 Walk-Forward Validation

## Nature
This card is an out-of-sample robustness check for the H-311 four-signal FDM system.

It does not modify the H-311 system definition, any existing reports, or any existing research cards.

## Background
H-311 measured the four-signal equal-weight system with FDM on the full aligned BTCUSDT sample and reported net Sharpe of `0.625799`.

That result is in-sample because the same full window is used to estimate the forecast correlation matrix and therefore the FDM. H-320 performs the minimum walk-forward check:

- Train: first half of the H-213/H-311 aligned window, matching the H-214 first-half split.
- Test: second half of the same aligned window, matching the H-214 second-half split.
- Estimate FDM on Train.
- Freeze the Train FDM and apply it to Test.

The signal definitions use expanding normalization and are generated across the full window. This does not introduce look-ahead because expanding normalization only uses past observations at each timestamp. The volatility estimator in `backtest_forecast()` is also rolling/expanding through EWM state. The only fitted value in this card is FDM.

## System Definition
Signals:

- `SIG_TREND_FAST`: EWMAC(8,32), expanding normalization
- `SIG_MOMENTUM`: 60-day momentum, expanding normalization
- `SIG_MEAN_REV`: 20-day mean reversion, expanding normalization
- `SIG_VOL_REGIME`: 60-day volatility regime, expanding normalization

Train FDM:

`fdm_train = compute_fdm(train_forecasts)`

Test forecast:

`clip((test_forecasts @ equal_weights) * fdm_train, -2, 2)`

## Backtest Setup
- Symbol: BTCUSDT
- Interval: 1d
- Data source: `data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Full aligned window: H-213/H-311 window, `2024-09-19 ~ 2026-05-22`
- Split: `len // 2`
- Capital: `100,000`
- Vol target: `20%`
- Vol lookback: `60`
- Max leverage: `2x`
- Cost model: `0.2%` round trip
- Benchmarks: BTC buy-and-hold over the train and test windows

## Pass Standard
H-320 passes if all three are true:

1. Test period net Sharpe is greater than `0.0`.
2. Test period net Sharpe is greater than `-0.3`.
3. FDM drift is below `30%`, calculated as `abs(fdm_train - fdm_test) / fdm_train`.

If the card passes, the system has basic out-of-sample robustness and can be considered for paper trading.

If the card fails, the system needs more conservative parameters or a different FDM estimation window before paper trading.

## Output
Report path:

`exports/ablation-h320-walk-forward-2026-05-25.md`

The report must include:
- Train and test date ranges and row counts.
- `fdm_train` and `fdm_test`.
- Four-column metric table: Train System, Test System, Train B&H, Test B&H.
- Train-to-test Sharpe decay ratio: `test_sharpe / train_sharpe`.
- Pass/fail result for each criterion.
- Known limitations: one split only, test period is a specific regime, and FDM is the only frozen fitted parameter.
- No system modification recommendation.

## Scope
- Do not modify any existing modules.
- Do not modify any existing cards or reports.
- Do not download new data.
