# Phase 29 Local Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing dashboard into a more complete local application console inspired by mature quant tools, without moving secrets or execution authority off the local machine.

**Architecture:** Keep the existing read-only dashboard and add a control-console API that aggregates health, runner tasks, AI coach proposals, strategy profiles, sweeps, testnet records, and real-trading gate state. The UI adds dense operational panels above the replay workspace while preserving the existing backtest/report workflow.

**Tech Stack:** Python dashboard data/service layer, SQLite queries, vanilla JS/CSS dashboard, pytest, Node syntax check.

---

### Task 1: Dashboard control-console API

- [x] Add tests for `DashboardData.control_console()`.
- [x] Add tests for `GET /api/control-console`.
- [x] Implement the aggregate API with tolerant missing-table handling.

### Task 2: Local console UI

- [x] Add static HTML markers for console panels.
- [x] Add JS render functions and fetch `/api/control-console`.
- [x] Add CSS for dense operational console panels.

### Task 3: Docs and verification

- [x] Document Phase 29 references and local-console direction.
- [x] Update planning/progress files.
- [x] Run full tests, JS syntax check, and sensitive scan.
