# Phase 8 History Replay Experiments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Brain commands that let the local trading brain download public historical K-lines, run moving-average replay tests from CSV, and persist each experiment for later review.

**Architecture:** Reuse the existing Binance public K-line client, CSV loader, moving-average strategy, backtest engine, and trade persistence. Add one storage table for backtest experiment summaries, then expose narrow Brain commands that never place orders and never require exchange keys.

**Tech Stack:** Python, SQLite, existing `BrainCommandHandler`, existing market data/backtest modules, pytest.

---

### Task 1: Storage For Strategy Experiments

**Files:**
- Modify: `src/trading_learning/storage/schema.sql`
- Modify: `src/trading_learning/export_import/exporter.py`
- Test: `tests/test_storage.py`
- Test: `tests/test_exporter.py`

- [ ] Add `strategy_experiments` with `external_id`, strategy name, symbol, interval, source CSV, parameters JSON, metrics JSON, note, timestamps.
- [ ] Add tests proving schema initialization creates the table.
- [ ] Include the table in export JSONL output.

### Task 2: Brain Commands For History And Replay

**Files:**
- Modify: `src/trading_learning/brain/commands.py`
- Test: `tests/test_brain_history_replay.py`

- [ ] Add `/history-download symbol=BTCUSDT interval=1h limit=100 output=data/local/BTCUSDT-1h.csv`.
- [ ] Add `/backtest-ma csv=... symbol=BTCUSDT interval=1h short=2 long=3 starting_cash=1000 quote_amount=100 fee=0.001 daily_limit=5 note=...`.
- [ ] Add `/experiment-summary limit=5`.
- [ ] Inject the public K-line fetcher into `BrainCommandHandler` so tests can run without network.
- [ ] Keep all three commands low-risk and non-trading.

### Task 3: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] Document the new Brain commands.
- [ ] Mark Phase 8 completed after local smoke and full test verification.
- [ ] Run `py -m pytest -q`, `git diff --check`, secret scan, and local Brain command smoke before committing.
