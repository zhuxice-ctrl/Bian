# Phase 18-22 Remote Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build the first working chain for Feishu/server task intake, local Quant Runner execution, LLM status/mock mode, and local-first safety boundaries.

**Architecture:** The server Brain owns Feishu intake and a durable SQLite task queue. The local Quant Runner authenticates to the server, claims queued tasks, executes only whitelisted local commands through the existing Brain command handler, and reports structured results. The local LLM remains loopback-only; when it is unavailable, Brain returns deterministic command guidance instead of failing silently.

**Tech Stack:** Python stdlib HTTP/SQLite/urllib, existing Brain command handler, PowerShell scripts, pytest.

---

### Task 1: Phase 18 status and mock-mode commands

**Files:**
- Modify: `src/trading_learning/ai_assistant/local_codex.py`
- Modify: `src/trading_learning/brain/natural_language.py`
- Modify: `src/trading_learning/brain/commands.py`
- Modify: `src/trading_learning/brain/command_aliases.py`
- Modify: `src/trading_learning/cli.py`
- Test: `tests/test_brain_natural_language.py`
- Test: `tests/test_brain_chinese_commands.py`

- [x] Add tests for `/llm-status`, `妫€鏌ラ摼鎺, `妫€鏌LM杩炴帴`, and no-LLM deterministic guidance.
- [x] Run targeted tests and confirm they fail because commands are missing.
- [x] Add loopback-only LLM health reporting and mock-mode response text.
- [x] Wire status provider into `BrainCommandHandler` from CLI.
- [x] Run targeted tests and confirm they pass.

### Task 2: Phase 19 server task queue

**Files:**
- Modify: `src/trading_learning/storage/schema.sql`
- Create: `src/trading_learning/brain/remote_tasks.py`
- Modify: `src/trading_learning/brain/commands.py`
- Modify: `src/trading_learning/brain/command_aliases.py`
- Test: `tests/test_remote_tasks.py`
- Test: `tests/test_brain_remote_tasks.py`

- [x] Add failing tests for task creation, rejection of unsafe task types, status listing, claim, and completion.
- [x] Run targeted tests and confirm queue APIs are missing.
- [x] Add `remote_tasks` schema and repository functions.
- [x] Add Brain commands `/queue-status`, `/queue-backtest-ma`, `/task-status`.
- [x] Run targeted tests and confirm they pass.

### Task 3: Phase 20 runner HTTP endpoints

**Files:**
- Modify: `src/trading_learning/config.py`
- Modify: `src/trading_learning/brain/service.py`
- Modify: `src/trading_learning/cli.py`
- Test: `tests/test_runner_service.py`

- [x] Add failing tests for authenticated `/runner/claim` and `/runner/complete`.
- [x] Run targeted tests and confirm endpoints are missing.
- [x] Add runner token config and HTTP endpoint handling.
- [x] Wire `TaskQueue` into `brain-serve`.
- [x] Run targeted tests and confirm they pass.

### Task 4: Phase 20 local Quant Runner MVP

**Files:**
- Create: `src/trading_learning/runner.py`
- Modify: `src/trading_learning/cli.py`
- Create: `scripts/start-quant-runner.ps1`
- Test: `tests/test_quant_runner.py`
- Test: `tests/test_windows_service_scripts.py`

- [x] Add failing tests for local status execution, backtest command mapping, result reporting, and script presence.
- [x] Run targeted tests and confirm runner is missing.
- [x] Implement one-shot runner with whitelisted task execution.
- [x] Add CLI command `quant-runner`.
- [x] Add Windows startup script.
- [x] Run targeted tests and confirm they pass.

### Task 5: Phase 21 Feishu remote backtest path

**Files:**
- Modify: `src/trading_learning/brain/command_aliases.py`
- Modify: `src/trading_learning/brain/commands.py`
- Test: `tests/test_brain_chinese_commands.py`
- Test: `tests/test_brain_remote_tasks.py`

- [x] Add failing tests for Chinese `杩滅▼鍥炴祴 ...` task intake and concise queued response.
- [x] Run targeted tests and confirm alias is missing.
- [x] Implement the Chinese alias using the server queue.
- [x] Run targeted tests and confirm they pass.

### Task 6: Documentation, planning updates, and verification

**Files:**
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`

- [x] Document server/local/runner/LLM commands in Chinese-first form.
- [x] Mark completed acceptance criteria for Phase 18-22 MVP scope.
- [x] Run `pytest -q`.
- [x] Run dashboard JavaScript syntax check.
- [x] Run sensitive information scan.
- [x] Commit and push the completed branch when verification passes.
