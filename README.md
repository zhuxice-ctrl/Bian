# Trading Learning

Local low-frequency crypto trading learning system.

Phase 1 supports:

- SQLite local storage
- Historical CSV loading
- Binance Spot public K-line download
- Moving-average backtests
- Backtest metrics: round trips, win rate, realized PnL, fees
- Daily review and learning records
- Local Codex-compatible draft assistant
- JSONL and Markdown ZIP export

Phase 1 does not place live orders.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Initialize Database

```powershell
trading-learning init-db
```

## Download Binance Klines

This uses Binance Spot public market data through `https://data-api.binance.vision` and does not require an API key.

```powershell
trading-learning download-klines --symbol BTCUSDT --interval 1h --limit 500 --output data/local/BTCUSDT-1h.csv
```

## Run Backtest

```powershell
trading-learning backtest-ma --csv tests/fixtures/btcusdt_1h_sample.csv --symbol BTCUSDT --short-window 2 --long-window 3
```

The backtest stores simulated trades in SQLite and prints summary metrics.

## Add Daily Review

```powershell
trading-learning review-add --date 2026-05-20 --symbols BTCUSDT,ETHUSDT --trade-count 2 --plan-followed yes --pnl 12.5 --mistake-tags late_entry --emotion-note "calm" --lesson "wait for planned entries"
```

## Create Local Codex Review Draft

The assistant endpoint is local-only. The client rejects non-loopback hosts.

```powershell
$env:LOCAL_CODEX_BASE_URL="http://127.0.0.1:61771/v1"
$env:LOCAL_CODEX_MODEL="gpt-5.4-mini"
$env:LOCAL_CODEX_API_KEY="your-local-only-key"
trading-learning ai-review-draft --source-external-id review-2026-05-20 --review-text "review body"
```

## Export Data

```powershell
trading-learning export --output exports/trading-learning-export.zip
```
