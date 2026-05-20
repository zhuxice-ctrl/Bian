# Phase 10 Learning Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate durable daily and weekly learning reports from local trading plans, reviews, replay experiments, and knowledge links.

**Architecture:** Add a `learning_reports` table and deterministic Brain commands that aggregate existing local records. Reports are persisted as JSON so they can be exported and reviewed later without calling any external model.

**Tech Stack:** Python, SQLite, existing `BrainCommandHandler`, JSONL exporter, pytest.

---

### Task 1: Report Storage And Export

**Files:**
- Modify: `src/trading_learning/storage/schema.sql`
- Modify: `src/trading_learning/export_import/exporter.py`
- Test: `tests/test_storage.py`
- Test: `tests/test_exporter.py`

- [ ] Add `learning_reports` with report type, period start/end, JSON content, and timestamps.
- [ ] Include `learning_reports.jsonl` in exports and bump manifest schema version.

### Task 2: Brain Report Commands

**Files:**
- Modify: `src/trading_learning/brain/commands.py`
- Test: `tests/test_brain_learning_reports.py`

- [ ] Add `/daily-report date=YYYY-MM-DD`.
- [ ] Add `/weekly-report start=YYYY-MM-DD end=YYYY-MM-DD`.
- [ ] Add `/learning-next date=YYYY-MM-DD`.
- [ ] Persist generated reports and return deterministic next learning actions.

### Task 3: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] Document the report commands.
- [ ] Run target tests, full test suite, diff check, secret scan, and Brain smoke before commit.
