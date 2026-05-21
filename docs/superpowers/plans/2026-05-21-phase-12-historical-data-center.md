# Phase 12 Historical Data Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local BTC/ETH historical K-line data center with batch refresh and dashboard dataset selection.

**Architecture:** Add a focused market data catalog module that owns dataset paths, inventory, and batch refresh. Expose that catalog through CLI, Brain, and read-only dashboard APIs. Keep all files under `data/local`, use public Binance data only, and preserve the existing symbol allowlist.

**Tech Stack:** Python stdlib, existing SQLite/Brain/CLI/dashboard modules, existing vanilla JS dashboard with Lightweight Charts.

---

### Task 1: Market Data Catalog

**Files:**
- Create: `src/trading_learning/market_data/catalog.py`
- Test: `tests/test_market_data_catalog.py`

- [ ] Add dataset path helpers for `data/local/market_data/{SYMBOL}/{SYMBOL}-{INTERVAL}.csv`.
- [ ] Add inventory scanning with row count, first candle, and last candle.
- [ ] Add batch refresh that calls the existing `fetch_klines` function and writes CSV files.
- [ ] Test path safety, allowlist enforcement, inventory shape, and refresh calls.

### Task 2: CLI And Brain Refresh Commands

**Files:**
- Modify: `src/trading_learning/cli.py`
- Modify: `src/trading_learning/brain/commands.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_brain_history_replay.py`

- [ ] Add `refresh-market-data` CLI command with default symbols `BTCUSDT,ETHUSDT` and intervals `1m,5m,15m,1h`.
- [ ] Add `/market-refresh` Brain command using the same defaults and allowlist.
- [ ] Keep unsupported symbols blocked before network calls.
- [ ] Test successful refresh payloads and unsupported symbol rejection.

### Task 3: Dashboard Dataset API

**Files:**
- Modify: `src/trading_learning/dashboard/data.py`
- Modify: `src/trading_learning/dashboard/service.py`
- Modify: `src/trading_learning/cli.py`
- Modify: `tests/test_dashboard.py`

- [ ] Add `/api/datasets`.
- [ ] Return local dataset inventory with symbol, interval, path, row count, first candle, last candle.
- [ ] Pass configured allowed symbols into dashboard data.
- [ ] Test API response and path safety remains unchanged.

### Task 4: Dashboard Dataset Picker

**Files:**
- Modify: `src/trading_learning/dashboard/static/index.html`
- Modify: `src/trading_learning/dashboard/static/app.js`
- Modify: `src/trading_learning/dashboard/static/styles.css`
- Modify: `tests/test_dashboard.py`

- [ ] Add a read-only historical data panel.
- [ ] Populate a dataset picker from `/api/datasets`.
- [ ] Load selected dataset into the existing Lightweight Charts replay chart without requiring a strategy experiment.
- [ ] Show dataset inventory rows and preserve existing experiment replay.

### Task 5: Verification And Plan Update

**Files:**
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] Run targeted tests.
- [ ] Run full test suite.
- [ ] Restart dashboard and smoke test `/api/datasets` plus browser load.
- [ ] Mark Phase 12 acceptance criteria complete if verification passes.
