# C2 Pairs Trading Ablation Rerun · 2026-05-23

## Data Source
- Source: H-206 backfill tooling.
- Interval: 1h.
- Files: `data/local/market_data/<SYMBOL>/<SYMBOL>-1h.csv`.
- CSV lines per file: 17521 including header.
- Data rows per file: 17520.
- Range for all four symbols: 2024-05-23 09:00 UTC to 2026-05-23 08:00 UTC.

| Symbol | Rows | First opened_at | Last opened_at |
|---|---:|---|---|
| BTCUSDT | 17520 | 2024-05-23T09:00:00+00:00 | 2026-05-23T08:00:00+00:00 |
| ETHUSDT | 17520 | 2024-05-23T09:00:00+00:00 | 2026-05-23T08:00:00+00:00 |
| BNBUSDT | 17520 | 2024-05-23T09:00:00+00:00 | 2026-05-23T08:00:00+00:00 |
| SOLUSDT | 17520 | 2024-05-23T09:00:00+00:00 | 2026-05-23T08:00:00+00:00 |

## Walk-Forward Configuration
- Train window: 365 days.
- Test window: 90 days.
- Step: 90 days.
- Purge: 5 days.
- Trigger rule: only run walk-forward after the pair passes the preregistered entry gate.

## BTC/ETH Diagnostics
- Pair: BTCUSDT / ETHUSDT.
- Synchronized rows: 17520.
- Static beta: 0.3833.
- Cointegration p-value: 0.5000.
- Half-life: 3431.18 periods.
- Entry gate: fail.
- Gate reasons: p-value > 0.05 and half-life > 240 periods.

### ADF Implementation Disclosure
Current ADF/cointegration p-values in this report use a 4-bucket MacKinnon-style threshold mapping: `0.01 / 0.049 / 0.10 / 0.50`. The value `p=0.5000` means the ADF statistic did not reach any significance threshold in this implementation. It should be read as a classification result, not as a precise continuous p-value. The half-life value is continuous and independently supports the gate failure.

### BTC/ETH Z-Score Distribution
- Window: 96.
- Count: 17425.
- Mean: 0.0446.
- Std: 1.4060.
- Min: -5.7919.
- 25%: -1.0371.
- Median: 0.0743.
- 75%: 1.1217.
- Max: 5.6369.

## Pair Gate Diagnostics

| Pair | Static beta | Cointegration p-value | Half-life | Gate |
|---|---:|---:|---:|---|
| BTCUSDT/ETHUSDT | 0.3833 | 0.5000 | 3431.18 | fail |
| BTCUSDT/BNBUSDT | 0.7681 | 0.5000 | 2590.33 | fail |
| BTCUSDT/SOLUSDT | 0.4047 | 0.5000 | 3482.02 | fail |
| BNBUSDT/SOLUSDT | 0.2176 | 0.5000 | 2178.08 | fail |

## Ablation Results

| Hypothesis | Pair | Variable Changed | Sharpe | Max DD | Trade Count | Result | Reason |
|---|---|---|---:|---:|---:|---|---|
| H-200 | BTCUSDT/ETHUSDT | Static beta baseline | n/a | n/a | n/a | fail | Entry gate failed: p=0.5000, half-life=3431.18 |
| H-201 | BTCUSDT/ETHUSDT | Add stop loss | n/a | n/a | n/a | not_applicable | H-200 BTC/ETH gate failed, so downstream ablation was not run |
| H-202 | BTCUSDT/ETHUSDT | Add half-life filter | n/a | n/a | n/a | not_applicable | H-200 BTC/ETH gate failed, so downstream ablation was not run |
| H-203 | BTCUSDT/ETHUSDT | Rolling beta | n/a | n/a | n/a | not_applicable | H-200 BTC/ETH gate failed, so downstream ablation was not run |
| H-204 | BTCUSDT/ETHUSDT | Cointegration recheck | n/a | n/a | n/a | not_applicable | H-200 BTC/ETH gate failed, so downstream ablation was not run |
| H-205A | BTCUSDT/BNBUSDT | Extend to BTC/BNB | n/a | n/a | n/a | fail | Independent pair gate failed: p=0.5000, half-life=2590.33 |
| H-205B | BTCUSDT/SOLUSDT | Extend to BTC/SOL | n/a | n/a | n/a | fail | Independent pair gate failed: p=0.5000, half-life=3482.02 |
| H-205C | BNBUSDT/SOLUSDT | Extend to BNB/SOL | n/a | n/a | n/a | fail | Independent pair gate failed: p=0.5000, half-life=2178.08 |

## Anti Cherry-Picking Statement
- No alternate pairs were searched after the gate.
- Multi-pair extensions listed individually.
- No portfolio aggregation.
- No thresholds changed after seeing results.

## Observed
- The data-length gate now passes for BTCUSDT, ETHUSDT, BNBUSDT, and SOLUSDT.
- The preregistered statistical gates fail for every tested pair.
- No walk-forward results were produced because no pair reached the entry condition required before trading evaluation.
