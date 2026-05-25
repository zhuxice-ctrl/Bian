# H-212 Cross-Lookback Effective N Measurement

## Nature
This card is a methodology measurement, not an alpha hypothesis.

The goal is to measure how much diversification is produced by using multiple EWMAC speeds inside the same signal family.

## Background
- Carver-style trend systems often combine multiple EWMAC speeds, for example EWMAC(8,32), EWMAC(16,64), and EWMAC(64,256).
- H-210 measured cross-signal diversification on BTCUSDT using six different signal families.
- This card measures whether cross-lookback diversification within EWMAC alone produces comparable independent dimensions.

## Research Question
For BTCUSDT 1d over the most recent two years, how correlated are six EWMAC speed forecasts, and what equal-weight effective N do they provide?

## Data
- Symbol: BTCUSDT
- Interval: 1d
- Window: most recent two years available in local data
- Source: `data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- No new data download

## Signal Set
Each signal reuses the H-210 parameterized EWMAC forecast implementation and emits a normalized forecast in `[-1, 1]`.

- `EWMAC_2_8`
- `EWMAC_4_16`
- `EWMAC_8_32`
- `EWMAC_16_64`
- `EWMAC_32_128`
- `EWMAC_64_256`

## Measurement
1. Build the six EWMAC forecast time series.
2. Align forecasts on common non-null dates.
3. Compute the six-speed Pearson correlation matrix.
4. Compute equal-weight `N_eff` for all six speeds.
5. Compute equal-weight `N_eff` for the Carver classic three-speed subset: `EWMAC_8_32`, `EWMAC_16_64`, `EWMAC_64_256`.
6. Compare the six-speed EWMAC `N_eff` with the H-210 six-signal `N_eff` under the same BTCUSDT data window.

## Output
Report path:

`exports/ablation-h212-cross-lookback-N_eff-2026-05-25.md`

The report must include:
- Six-speed Pearson correlation matrix
- Equal-weight `N_eff` for all six speeds
- Equal-weight `N_eff` for the Carver three-speed subset
- Comparison against H-210 `N_eff` with a structural interpretation only

## Scope
- Do not modify H-200 through H-211 cards or reports.
- Do not modify strategy or cointegration code.
- Do not download new data.
- Do not draw alpha or trading conclusions from this card.
