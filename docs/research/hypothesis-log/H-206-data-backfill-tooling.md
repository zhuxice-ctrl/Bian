# H-206 · Data Backfill Tooling

## Status
tooling

## Purpose
H-200 through H-205 were deferred because the local market-data cache did not satisfy the required two years of synchronized 1h data. This tooling adds a manual, explicit backfill path so those hypotheses can be rerun unchanged after data is collected.

## Scope
- Adds a paginated kline backfill module for user-specified symbols and ranges.
- Adds a dataset writer that uses the existing market-data catalog path layout.
- Adds backups for existing CSV files before replacement.
- Adds a dry-run CLI mode that prints the download plan without sending requests.

## Non-Goals
- This commit does not download real market data.
- This commit does not change H-200 through H-205 conclusions.
- This commit does not add BNBUSDT or SOLUSDT to `DEFAULT_ALLOWED_SYMBOLS`.
- This commit does not connect Brain slash commands.

## Link To Prior Report
`exports/ablation-pairs-2026-05-23.md` lists the next action as collecting at least two years of synchronized 1h BTCUSDT and ETHUSDT data, then rerunning H-200 unchanged before further ablation. H-206 exists only to make that data collection explicit and reproducible.

## Validation
- Dry-run mode is the expected verification path for this task.
- Real API calls remain a manual follow-up action.
