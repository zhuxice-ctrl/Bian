# Phase 14 Experiment Review Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert backtest reports into durable review drafts that guide manual replay, learning questions, and follow-up study.

**Architecture:** Add a deterministic learning builder that consumes the existing backtest report shape, persist one updatable draft per experiment, expose it through Brain and a read-only dashboard API, and export it with the rest of the learning data.

**Tech Stack:** Python stdlib, SQLite, existing Brain command handler, existing dashboard data/service layer.

---

### Task 1: Deterministic Review Builder

**Files:**
- Add: `src/trading_learning/learning/experiment_review.py`
- Add: `tests/test_experiment_review.py`

- [x] Build a review draft from a backtest report payload.
- [x] Include `summary`, `risk_flags`, `review_questions`, `focus_trades`, and `learning_tasks`.
- [x] Flag negative PnL, drawdown, low win rate, losing trades, and fee pressure.
- [x] Produce a lighter maintenance task when the experiment has no major risk flags.

### Task 2: Storage And Export

**Files:**
- Modify: `src/trading_learning/storage/schema.sql`
- Modify: `src/trading_learning/export_import/exporter.py`
- Modify: `tests/test_storage.py`
- Modify: `tests/test_exporter.py`

- [x] Add `experiment_review_drafts`.
- [x] Enforce one updatable draft per experiment.
- [x] Include drafts in local data export.

### Task 3: Brain Command

**Files:**
- Modify: `src/trading_learning/brain/commands.py`
- Add: `tests/test_brain_experiment_review.py`

- [x] Add `/experiment-review experiment=EXPERIMENT_ID`.
- [x] Reuse dashboard/backtest report data rather than duplicating report calculations.
- [x] Save or update the draft and return the draft payload.
- [x] Return clear `not_found` or `failed` responses for missing experiments/data.

### Task 4: Read-Only Dashboard API

**Files:**
- Modify: `src/trading_learning/dashboard/data.py`
- Modify: `src/trading_learning/dashboard/service.py`
- Modify: `tests/test_dashboard.py`

- [x] Add `DashboardData.experiment_review(experiment_id)`.
- [x] Add `/api/experiment-review?experiment=...`.
- [x] Return stored drafts when present; otherwise return a generated unsaved draft for preview.

### Task 5: Verification

**Files:**
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [x] Run targeted tests.
- [x] Run full test suite.
- [x] Run syntax/static checks used by the project.
- [x] Commit and push Phase 14A.
