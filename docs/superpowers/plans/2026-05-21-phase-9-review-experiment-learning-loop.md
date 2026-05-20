# Phase 9 Review Experiment Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Link daily reviews to strategy experiments and knowledge cards so each trading day can become a durable learning record.

**Architecture:** Add a join table between `daily_reviews` and `strategy_experiments`. Expose two non-trading Brain commands: one to link a review to an experiment, and one to return a review context bundle containing the review, linked experiments, and linked knowledge cards.

**Tech Stack:** Python, SQLite, existing `BrainCommandHandler`, existing JSONL exporter, pytest.

---

### Task 1: Link Storage And Export

**Files:**
- Modify: `src/trading_learning/storage/schema.sql`
- Modify: `src/trading_learning/export_import/exporter.py`
- Test: `tests/test_storage.py`
- Test: `tests/test_exporter.py`

- [ ] Add `review_experiment_links` with `review_external_id`, `experiment_external_id`, `tag`, and `note`.
- [ ] Include the table in exports and bump export schema version.

### Task 2: Brain Learning Loop Commands

**Files:**
- Modify: `src/trading_learning/brain/commands.py`
- Test: `tests/test_brain_learning_loop.py`
- Test: `tests/test_brain_suggested_commands.py`

- [ ] Add `/experiment-link review=... experiment=... tag=... note=...`.
- [ ] Add `/review-context review=...`.
- [ ] Validate referenced review and experiment exist before linking.
- [ ] Make `/experiment-link` safe for `/run suggested`; keep `/review-context` read-only and direct.

### Task 3: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] Document both commands.
- [ ] Run target tests, full test suite, diff check, secret scan, and local Brain smoke before commit.
