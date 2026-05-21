# Phase 16 Backtest Software Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the read-only dashboard backtest workspace with trade filters and multi-experiment comparison.

**Architecture:** Keep all writes out of the dashboard. Extend `DashboardData.backtest_report` with filter metadata and round-trip result annotations, add a read-only comparison payload, expose it through the dashboard service, then render controls and comparison tables in the existing vanilla JavaScript dashboard.

**Tech Stack:** Python stdlib, SQLite, existing dashboard HTTP service, vanilla HTML/CSS/JS, pytest, Browser validation.

---

### Task 1: Report Filter Metadata

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `src/trading_learning/dashboard/data.py`

- [x] Add a failing test for backtest report trade annotations and filter metadata.
- [x] Annotate trades with `round_trip_result`, `round_trip_pnl`, and `round_trip_pnl_pct` when a round trip is known.
- [x] Return `filter_options` with side values, result values, start/end timestamps, and experiment review risk flags.
- [x] Run targeted dashboard tests.

### Task 2: Experiment Comparison Payload

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `src/trading_learning/dashboard/data.py`
- Modify: `src/trading_learning/dashboard/service.py`

- [x] Add a failing test for comparing two experiments by metrics and parameters.
- [x] Implement `DashboardData.experiment_comparison(experiment_ids)`.
- [x] Add `/api/experiment-comparison?experiments=ID1,ID2`.
- [x] Run targeted dashboard tests.

### Task 3: Dashboard Controls

**Files:**
- Modify: `tests/test_dashboard.py`
- Modify: `src/trading_learning/dashboard/static/index.html`
- Modify: `src/trading_learning/dashboard/static/app.js`
- Modify: `src/trading_learning/dashboard/static/styles.css`

- [x] Add static tests for trade filter controls and comparison UI markers.
- [x] Add side/result/date/risk filter controls above the trade table.
- [x] Filter visible trade rows client-side without mutating stored records.
- [x] Add comparison controls and table.
- [x] Keep mobile layout readable and avoid overlapping controls.

### Task 4: Verification

**Files:**
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [x] Run `pytest -q`.
- [x] Run dashboard JavaScript syntax check.
- [x] Run browser verification for desktop and mobile dashboard views.
- [x] Update plan/progress/findings with final verification results.
