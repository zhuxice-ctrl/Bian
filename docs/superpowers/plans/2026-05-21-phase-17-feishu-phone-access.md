# Phase 17 Feishu Phone Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure Feishu phone access so text events route to local Brain and the user receives concise Feishu replies.

**Architecture:** Keep the existing local `/feishu/events` endpoint as the inbound boundary. Add a small Feishu bot client for tenant token retrieval and text-message replies, wire it into the adapter only when app credentials are configured, and add a PowerShell environment setup script that stores secrets in the Windows user environment.

**Tech Stack:** Python stdlib `urllib`, SQLite-backed Brain service, Feishu Open Platform event callbacks and IM message API, PowerShell setup scripts, pytest.

---

### Task 1: Feishu Reply Client

**Files:**
- Modify: `src/trading_learning/brain/feishu.py`
- Modify: `tests/test_feishu_bridge.py`

- [x] Add a failing test for sending a concise Brain response back to `chat_id`.
- [x] Add a failing test for tenant token retrieval and send-message request shape.
- [x] Implement a stdlib Feishu bot client.
- [x] Keep adapter behavior unchanged when app credentials are missing.

### Task 2: Runtime Configuration

**Files:**
- Modify: `src/trading_learning/config.py`
- Modify: `src/trading_learning/cli.py`
- Modify: `scripts/start-brain.ps1`
- Add: `scripts/set-feishu-env.ps1`
- Modify: `tests/test_windows_service_scripts.py`

- [x] Add `FEISHU_APP_ID` and `FEISHU_APP_SECRET` to runtime config.
- [x] Wire Feishu bot client into `brain-serve`.
- [x] Add a setup script that prompts for Feishu values without storing secrets in the repo.
- [x] Ensure startup script imports Feishu env vars from Windows user environment.

### Task 3: Docs And Verification

**Files:**
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [x] Document Feishu console configuration and local tunnel requirements.
- [x] Run Feishu targeted tests.
- [x] Run full test suite and sensitive-information scan.
