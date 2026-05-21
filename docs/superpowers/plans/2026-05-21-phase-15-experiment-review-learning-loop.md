# Phase 15 Experiment Review Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Chinese Brain command that converts an experiment review draft into daily review, knowledge, links, and daily report records.

**Architecture:** Reuse the existing Brain command handler as the write boundary. Add a small command method that obtains or generates a draft, writes existing SQLite-backed learning records, and calls the existing daily report builder.

**Tech Stack:** Python stdlib, SQLite, pytest, existing Brain command alias and command handler modules.

---

### Task 1: Command Alias Tests

**Files:**
- Modify: `tests/test_brain_chinese_commands.py`
- Modify: `src/trading_learning/brain/command_aliases.py`

- [x] Add a failing test proving `沉淀实验复盘 实验=exp-1 日期=2026-05-21` normalizes to `/experiment-review-commit experiment=exp-1 date=2026-05-21`.
- [x] Implement the alias by adding `实验 -> experiment`, defining the Chinese command prefix, and routing through `_rewrite_keyed_command`.
- [x] Run the targeted test and confirm it passes.

### Task 2: Brain Persistence Command

**Files:**
- Modify: `tests/test_brain_experiment_review.py`
- Modify: `src/trading_learning/brain/commands.py`

- [x] Add a failing test for the Chinese command writing a daily review, generated knowledge cards, review-experiment link, review-knowledge links, and a daily learning report.
- [x] Add a failing idempotency test showing a rerun does not duplicate generated cards or links.
- [x] Implement `/experiment-review-commit`.
- [x] Run targeted tests and confirm they pass.

### Task 3: Docs And Progress

**Files:**
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [x] Document the Chinese command and internal command.
- [x] Mark Phase 15 progress and findings.
- [x] Run full pytest and dashboard JavaScript syntax check.
