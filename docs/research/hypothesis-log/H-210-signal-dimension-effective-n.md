# H-210 Signal Dimension Effective N Measurement

## Nature
This card is a methodology measurement, not an alpha hypothesis.

The goal is to measure whether different signal types on one instrument provide more independent dimensions than adding highly correlated crypto instruments.

## Background
- H-209 measured BTC/ETH/BNB/SOL instrument returns as highly correlated, with equal-weight effective N close to one independent bet.
- Further diversification must therefore be tested at the signal dimension before using it as a portfolio design assumption.
- This measurement uses BTCUSDT daily local data only and does not optimize or judge signal profitability.

## Research Question
For BTCUSDT 1d over the most recent two years, how correlated are common signal families, and how many effective equal-weight bets do six normalized forecasts provide?

## Data
- Symbol: BTCUSDT
- Interval: 1d
- Window: most recent two years available in the local CSV
- Source: `data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- No new data download

## Signal Set
Each signal emits a forecast series normalized to `[-1, 1]`.

- `SIG_TREND_FAST`: EWMAC(8, 32)
- `SIG_TREND_SLOW`: EWMAC(64, 256)
- `SIG_BREAKOUT`: `(price - rolling_mid_120) / (rolling_max_120 - rolling_min_120)`
- `SIG_MEAN_REV`: `-1 * zscore(price, window=20)`
- `SIG_MOMENTUM`: past 60-day return
- `SIG_VOL_REGIME`: z-score of rolling 60-day volatility

Normalization uses rolling 252-day absolute mean scaling, caps the scaled value to `[-2, 2]`, then rescales by 2 so every finite forecast is in `[-1, 1]`.

## Measurement
1. Build the six forecast time series on BTCUSDT 1d.
2. Align forecasts on common non-null dates.
3. Compute Pearson correlation matrix.
4. Compute Spearman correlation matrix.
5. Compute equal-weight effective N of bets from the Pearson matrix.
6. Identify the three lowest absolute pairwise correlations.

## Output
Report path:

`exports/ablation-h210-signal-correlation-N_eff-2026-05-25.md`

The report must include:
- Data window and aligned sample count
- Pearson correlation matrix
- Spearman correlation matrix
- Equal-weight `N_eff`
- Three lowest-correlation signal pairs
- Interpretation of the signal dimension structure without trading conclusions

## Scope
- Do not modify H-200 through H-209 cards or reports.
- Do not modify strategy or cointegration code.
- Do not download new data.
- Do not draw alpha or trading conclusions from this card.
