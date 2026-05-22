# Phase 31-38 Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the cleaned local prototype into a clearer daily-use quant learning workstation without enabling real trading.

**Architecture:** Reuse the existing SQLite, Brain, dashboard, runner, and production gate layers. Add small service helpers where behavior must be shared between CLI, Brain, and dashboard, and keep all write actions local, deterministic, and explicit.

**Tech Stack:** Python standard library, SQLite, existing `trading_learning` modules, vanilla dashboard JavaScript/CSS, pytest.

---

### Task 1: Workspace Reset And Provenance

**Files:**
- Create: `src/trading_learning/workspace.py`
- Modify: `src/trading_learning/cli.py`
- Modify: `src/trading_learning/brain/commands.py`
- Modify: `src/trading_learning/dashboard/data.py`
- Test: `tests/test_workspace_reset.py`

- [ ] Add a workspace helper that reports table counts, source counts, empty-state next steps, and safely clears local business tables after creating a backup.
- [ ] Add CLI `reset-workspace --confirm RESET_LOCAL_WORKSPACE --backup-dir data/backups`.
- [ ] Add Brain `/workspace-status` and `/workspace-reset confirm=RESET_LOCAL_WORKSPACE`.
- [ ] Add `workspace_state` to dashboard overview/control console payloads.
- [ ] Verify with `pytest tests/test_workspace_reset.py tests/test_dashboard.py tests/test_brain_workspace.py -q`.

### Task 2: Market Data Center Metadata

**Files:**
- Modify: `src/trading_learning/market_data/catalog.py`
- Modify: `src/trading_learning/brain/commands.py`
- Modify: `src/trading_learning/dashboard/data.py`
- Test: `tests/test_market_data_catalog.py`
- Test: `tests/test_brain_market_status.py`

- [ ] Extend default intervals to `1m,5m,15m,1h,4h,1d`.
- [ ] Return inventory entries for missing datasets with `exists=false`, plus cached dataset metadata with `source=binance_public_cache`.
- [ ] Add Brain `/market-status` summary text.
- [ ] Verify with targeted market-data tests.

### Task 3: Local Backtest Action

**Files:**
- Create: `src/trading_learning/actions.py`
- Modify: `src/trading_learning/dashboard/service.py`
- Modify: `src/trading_learning/dashboard/data.py`
- Test: `tests/test_dashboard_actions.py`

- [ ] Add a shared `run_local_ma_backtest_action()` that validates allowed symbols and `data/local` paths, stores a strategy experiment, stores trades with the experiment id as source, and returns summary metrics.
- [ ] Add dashboard POST `/api/actions/backtest-ma`.
- [ ] Keep the endpoint local-only by relying on dashboard loopback binding and no credential use.
- [ ] Verify persistence and invalid input behavior with tests.

### Task 4: Learning Loop Actions

**Files:**
- Modify: `src/trading_learning/actions.py`
- Modify: `src/trading_learning/dashboard/service.py`
- Modify: `src/trading_learning/dashboard/data.py`
- Test: `tests/test_dashboard_actions.py`

- [ ] Add POST `/api/actions/experiment-review` to persist a deterministic review draft.
- [ ] Add POST `/api/actions/experiment-review-commit` to commit draft content to learning records through existing Brain behavior.
- [ ] Add `next_review_actions` to control console for experiments with no committed daily review.
- [ ] Verify generated records and response payloads.

### Task 5: Remote Task Status Polish

**Files:**
- Modify: `src/trading_learning/brain/commands.py`
- Test: `tests/test_brain_remote_tasks.py`

- [ ] Format `/task-status` with concise Chinese-readable lines.
- [ ] Include state, type, runner, result summary, and error message where present.
- [ ] Verify queued/succeeded/failed summaries.

### Task 6: Coach Daily Flow

**Files:**
- Create: `src/trading_learning/learning/daily_coach.py`
- Modify: `src/trading_learning/brain/commands.py`
- Modify: `src/trading_learning/dashboard/data.py`
- Test: `tests/test_ai_coach.py`

- [ ] Add deterministic daily coach branches for empty workspace, missing data, data-ready, and experiment-ready states.
- [ ] Add Brain `/coach-daily`.
- [ ] Surface plan in dashboard control console.
- [ ] Verify branch behavior.

### Task 7: Dashboard Application Shell

**Files:**
- Modify: `src/trading_learning/dashboard/static/index.html`
- Modify: `src/trading_learning/dashboard/static/app.js`
- Modify: `src/trading_learning/dashboard/static/styles.css`
- Test: `tests/test_dashboard.py`

- [ ] Add top navigation anchors for console, data, backtest, review, knowledge, reports, and safety.
- [ ] Add empty-state guidance that points users to refresh market data and run the first real backtest.
- [ ] Add backtest form controls and action handlers.
- [ ] Verify static markers and JavaScript syntax.

### Task 8: Safety Boundary

**Files:**
- Modify: `src/trading_learning/production_gate.py`
- Modify: `src/trading_learning/brain/commands.py`
- Modify: `src/trading_learning/dashboard/data.py`
- Test: `tests/test_production_gate.py`

- [ ] Add explicit kill-switch status in production readiness payload.
- [ ] Add Brain `/kill-switch-status` and `/kill-switch-enable`.
- [ ] Prove real trading remains blocked after both commands.
- [ ] Verify dashboard safety payload.

### Task 9: Final Verification And Publish

**Files:**
- Modify: `README.md`
- Modify: `docs/operations/daily-use-zh.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] Run `pytest -q`.
- [ ] Run `node --check src/trading_learning/dashboard/static/app.js`.
- [ ] Run `git diff --check`.
- [ ] Run a sensitive information scan.
- [ ] If all pass, commit and push to `main`.
