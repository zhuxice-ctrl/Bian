# Trading Learning

Local low-frequency crypto trading learning system.

Phase 1 supports:

- SQLite local storage
- Historical CSV loading
- Moving-average backtests
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

## Run Backtest

```powershell
trading-learning backtest-ma --csv tests/fixtures/btcusdt_1h_sample.csv --symbol BTCUSDT --short-window 2 --long-window 3
```

## Export Data

```powershell
trading-learning export --output exports/trading-learning-export.zip
```
