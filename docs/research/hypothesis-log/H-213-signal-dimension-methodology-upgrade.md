# H-213 Signal Dimension Methodology Upgrade

## Nature
This card is a methodology correction, not an alpha hypothesis.

H-210 remains part of the audit trail. Its card and report are not deleted, rewritten, or backfilled. H-213 produces an independent upgraded report that should be treated as the more credible measurement version for signal-dimension structure.

## Background
H-210 reported an equal-weight signed-correlation `N_eff` of 10.7 for six BTCUSDT price-derived forecasts. Review found two methodology problems:

1. Signed `N_eff` can be inflated by structural negative correlation.
2. The aligned sample was only 168 days because 252-day rolling normalization burned a large part of the two-year data window.

These issues do not mean the H-210 code path was broken. They mean the method was too fragile for interpreting signal dimensionality.

## Why Signed N_eff Distorts Under Negative Correlation
The standard equal-weight effective N formula uses `w' Corr w` in the denominator. Negative off-diagonal correlations reduce that denominator. If the denominator becomes very small, the implied `N_eff` can exceed the number of nominal signals.

That can be useful when measuring a hedged risk portfolio, but it is misleading as a count of independent signal ideas. For example, a mean-reversion signal is partly constructed as the inverse of recent price extension, so it can appear negatively correlated with trend-style forecasts by design. Treating that negative correlation as additional independent "alpha breadth" overstates signal diversity.

H-213 therefore reports both:

- Signed `N_eff`: preserves hedge effects.
- Absolute-correlation `N_eff`: replaces `rho` with `|rho|` to estimate diversification while ignoring hedge sign.

## Why the 168-Day H-210 Window Is Insufficient
H-210 used two years of BTCUSDT daily prices, but every forecast also required a 252-day rolling absolute-mean normalization window. Signals with long internal lookbacks then aligned only from late 2025 onward, leaving 168 common observations.

That short sample happened to cover the BTC 2025 late-cycle top and reversal window. In that regime, trend and mean-reversion style forecasts can show strong non-stationary negative correlation. A short, regime-specific window is too fragile for a methodology measurement intended to describe signal-dimension structure.

## Methodology Upgrade
H-213 keeps the H-210 signal definitions but changes normalization for the upgraded measurement:

- Default forecast normalization becomes expanding.
- Expanding normalization starts after 60 observations of the raw signal.
- Rolling normalization remains available for H-210 reproduction.
- The scaling formula is unchanged: divide by rolling or expanding mean absolute signal, cap to `[-2, 2]`, then rescale to `[-1, 1]`.

## Measurement Outputs
The independent H-213 report will include:

- Pearson and Spearman correlation matrices under expanding normalization.
- Signed equal-weight `N_eff`.
- Absolute-correlation equal-weight `N_eff`.
- PCA explained variance ratios.
- Effective dimension threshold at 90% cumulative variance.
- Standalone Sharpe for each signal using forecast times next daily return, with no cost model.
- Side-by-side comparison against the H-210 published number.

## Interpretation Rules
This card measures structure only. It must not recommend dropping or keeping any signal.

The report must distinguish risk diversification from alpha diversification:

- Risk diversification can benefit from negative correlation because it reduces portfolio variance.
- Alpha diversification should not count a mechanically inverted forecast as a new independent idea without separate evidence of standalone alpha.

Signal selection decisions are deferred to later H cards.

## Scope
- Do not delete or modify H-210 card or report.
- Do not modify H-209 or H-212 cards or reports.
- Do not modify H-300, strategy, or cointegration code.
- Do not download new data.
