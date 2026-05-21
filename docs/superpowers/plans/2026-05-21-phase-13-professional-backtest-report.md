# Phase 13 Professional Backtest Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn experiment replay into a professional read-only backtest report workspace.

**Architecture:** Add deterministic report-building helpers in the backtest layer, expose experiment reports through the dashboard API, and render report metrics, equity curve, drawdown, and trade rows in the existing dashboard. The report stays local and read-only.

**Tech Stack:** Python stdlib, SQLite-backed dashboard APIs, existing vanilla JS dashboard, local bundled TradingView Lightweight Charts.

---

### Task 1: Backtest Report Payload

**Files:**
- Modify: `src/trading_learning/backtest/report.py`
- Modify: `tests/test_backtest_report.py`

- [ ] Add realized round-trip rows with entry/exit price, fees, pnl, and pnl percent.
- [ ] Add an equity curve derived from starting cash and closed trades.
- [ ] Add max drawdown from the equity curve.
- [ ] Preserve existing `summarize_backtest` behavior.

### Task 2: Dashboard Report API

**Files:**
- Modify: `src/trading_learning/dashboard/data.py`
- Modify: `src/trading_learning/dashboard/service.py`
- Modify: `tests/test_dashboard.py`

- [ ] Add `DashboardData.backtest_report(experiment_id)`.
- [ ] Add `/api/backtest-report?experiment=...`.
- [ ] Return experiment metadata, metrics, trades, round trips, equity curve, and max drawdown.
- [ ] Keep missing experiment and missing CSV behavior explicit.

### Task 3: Dashboard Report UI

**Files:**
- Modify: `src/trading_learning/dashboard/static/index.html`
- Modify: `src/trading_learning/dashboard/static/app.js`
- Modify: `src/trading_learning/dashboard/static/styles.css`
- Modify: `tests/test_dashboard.py`

- [ ] Add report metric strip under the replay controls.
- [ ] Add equity curve chart using Lightweight Charts line series.
- [ ] Add a trade list table.
- [ ] Clicking a trade row should update trade detail and move the visible K-line range to that trade.

### Task 4: Verification

**Files:**
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] Run targeted tests.
- [ ] Run full test suite.
- [ ] Restart dashboard and browser-smoke the report UI.
- [ ] Mark Phase 13 complete if verification passes.
