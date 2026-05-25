# H-214 Signal Relation Temporal Stability

## Nature
This card is a methodology robustness check, not an alpha hypothesis.

The goal is to test whether the H-213 six-signal relationship structure looks similar across two chronological subwindows. This card measures temporal consistency only. It does not decide whether the overall structure is stable or unstable, and it does not accept, reject, remove, or merge any signal.

## Background
H-213 upgraded H-210 by using expanding normalization, producing a 611-row aligned BTCUSDT 1d forecast window from `2024-09-19` through `2026-05-22`.

H-213 reported:

- Pearson and Spearman correlation matrices.
- Signed and absolute-correlation effective N.
- PCA explained variance and 90% component threshold.
- Standalone Sharpe diagnostics for each signal.

Those measurements were computed over one full period. H-214 splits that full period into two chronological halves and compares whether the same relationships have similar measured values in each half.

## Data
- Symbol: BTCUSDT
- Interval: 1d
- Source: `data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`
- Signal definitions: same six expanding-normalized H-213 signals
- Full aligned window: `2024-09-19 ~ 2026-05-22`
- Expected full aligned rows: 611
- Subwindow split: first 305 rows and last 306 rows
- No new data download

## Measurement
For each of the first-half, second-half, and full H-213 windows:

1. Pearson correlation matrix.
2. Spearman correlation matrix.
3. Equal-weight signed `N_eff`.
4. Equal-weight absolute-correlation `N_eff`.
5. PCA explained variance.
6. 90% PCA effective dimension threshold.
7. Standalone Sharpe per signal, using forecast times next daily return before costs.

The report also computes pairwise absolute changes in Pearson correlation:

`abs(first_half_corr - second_half_corr)`

## Output
Report path:

`exports/ablation-h214-temporal-stability-2026-05-25.md`

The report must include:

- Three Pearson matrices for first half, second half, and full H-213 window.
- Pairwise correlation difference table.
- Standalone Sharpe first-half versus second-half versus full comparison.
- PCA explained variance first-half versus second-half versus full comparison.
- Interpretation listing lower-drift and higher-drift signal-pair candidates, without making an overall stability conclusion.

## Scope
- Do not modify H-200 through H-213 cards or reports.
- Do not modify `forecast_library`, `dimension_analysis`, or `standalone_sharpe`.
- Do not modify strategy or cointegration code.
- Do not download new data.
