# H-340 Data Pipeline Automation

## Nature
This card is an engineering task, not a strategy hypothesis or alpha test.

It automates the daily BTCUSDT 1d data refresh required by H-330 paper trading. It does not change the H-311/H-320 strategy definition, signal formulas, backtest logic, or paper-trading position model.

## Background
H-330 created the paper-trading infrastructure, but the daily workflow still depended on manually updating:

`data/local/market_data/BTCUSDT/1d/BTCUSDT-1d.csv`

H-340 adds an automated local pipeline:

`Binance public klines API -> incremental CSV append -> paper_trade daily run -> status print`

The local CSV keeps the existing project schema:

`opened_at,open,high,low,close,volume`

## Scope
Included:

- `src/trading_learning/market_data/binance_klines.py`
- `scripts/daily_update.py`
- `tests/test_binance_klines.py`
- `tests/test_daily_update.py`

Excluded:

- No strategy changes.
- No paper-trading model changes.
- No backtest or forecast-library changes.
- No live exchange order routing.
- No API key or private Binance endpoint.

## Data Update Behavior
`update_csv()` reads the local CSV, detects the timestamp column, and fetches Binance rows after the latest local timestamp.

For the current BTCUSDT 1d dataset, the timestamp column is `opened_at`. New rows are appended using the same column order, so existing historical rows are not rewritten.

If the CSV is missing, the updater creates a loader-compatible CSV with the project schema and the latest 1000 Binance candles.

## CLI
Update data only:

`python scripts/daily_update.py`

Update data and run paper trading:

`python scripts/daily_update.py --trade`

Update data, run paper trading, and print status:

`python scripts/daily_update.py --trade --status`

## Error Handling
If Binance is unreachable through the current network path, or Binance returns HTTP `403` or `451`, the script prints:

`Binance API blocked, try VPN`

The script exits with code `1` and does not run paper trading after the failed update.

## Verification Note
On 2026-05-25, the local Codex environment reached the blocked-network path for:

`py -3.11 scripts/daily_update.py --trade --status`

Output:

`Binance API blocked, try VPN`

The command exited with code `1`, as designed for Binance API blocks. VPN validation is still required outside this blocked environment.

## Acceptance Criteria
- `python scripts/daily_update.py --trade --status` runs successfully when Binance is reachable.
- If Binance is blocked, the command exits cleanly with `Binance API blocked, try VPN` and can be verified again through VPN.
- `pytest -q` passes.
- Existing BTCUSDT CSV historical rows are not overwritten or reformatted.
- `git status --short` is clean after the implementation commits.
