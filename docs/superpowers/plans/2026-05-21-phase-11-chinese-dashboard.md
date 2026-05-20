# Phase 11 Chinese Commands And Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Chinese-friendly Brain command layer and a local read-only visual dashboard with K-line replay.

**Architecture:** Keep existing slash commands as stable internal APIs. Add a thin Chinese command normalization layer before dispatch, then add a separate dashboard HTTP surface that reads SQLite and local CSV files without exposing secrets or placing orders.

**Tech Stack:** Python standard library HTTP server, SQLite, vanilla HTML/CSS/JS, pytest.

---

### Task 1: Chinese Brain Command Normalization

**Files:**
- Create: `src/trading_learning/brain/command_aliases.py`
- Modify: `src/trading_learning/brain/commands.py`
- Test: `tests/test_brain_chinese_commands.py`

- [ ] Write tests for Chinese status, plan status, review summary, learning prompt, suggested-command execution, structured review, and guarded testnet buy aliases.
- [ ] Run the new tests and verify they fail because aliases are not implemented.
- [ ] Implement deterministic normalization from Chinese text to existing slash commands.
- [ ] Run the new tests and targeted Brain tests.

### Task 2: Local Dashboard API

**Files:**
- Create: `src/trading_learning/dashboard/__init__.py`
- Create: `src/trading_learning/dashboard/data.py`
- Create: `src/trading_learning/dashboard/service.py`
- Modify: `src/trading_learning/cli.py`
- Test: `tests/test_dashboard.py`

- [ ] Write tests for read-only overview, experiments, knowledge, and K-line CSV endpoints.
- [ ] Run the dashboard tests and verify they fail because the dashboard package does not exist.
- [ ] Implement JSON endpoints and static serving without trading endpoints.
- [ ] Add `trading-learning dashboard-serve --host 127.0.0.1 --port 8780`.
- [ ] Run dashboard tests and CLI parser tests.

### Task 3: Dashboard Static UI And K-Line Replay

**Files:**
- Create: `src/trading_learning/dashboard/static/index.html`
- Create: `src/trading_learning/dashboard/static/styles.css`
- Create: `src/trading_learning/dashboard/static/app.js`
- Modify: `pyproject.toml`
- Test: `tests/test_dashboard.py`

- [ ] Add tests that the root page and static assets are served.
- [ ] Build a compact operations dashboard with overview panels, experiment list, knowledge list, and a canvas K-line replay view.
- [ ] Keep the UI read-only: no order buttons, no secret fields.
- [ ] Verify in a browser-capable smoke path after tests pass.

### Task 4: Documentation, Verification, And Git

**Files:**
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `progress.md`

- [ ] Document Chinese Brain examples and dashboard startup.
- [ ] Run full pytest, diff check, and secret scan.
- [ ] Start the dashboard locally and verify that the page/API loads.
- [ ] Commit and push to `main`.
