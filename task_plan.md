# Trading Learning System Plan

## Goal

Build a local-first, low-frequency crypto trading learning system that can:

- Keep a durable record of daily reviews, lessons, and strategy knowledge.
- Run Binance Spot Testnet operations through a guarded local Brain service.
- Support future phone access through Feishu without moving exchange keys out of the local machine.
- Keep live-order capability out of scope until testnet, review, and risk workflows are stable.

## Current Status

- [x] SQLite storage, export, backtest, review repository, learning repository.
- [x] Binance Spot Testnet signed client and `/api/v3/order/test`.
- [x] Execution risk guard.
- [x] Local Brain service with audit logs and confirmation flow.
- [x] Windows long-running startup scripts.
- [x] Local terminal chat helper.
- [x] Feishu event endpoint foundation.
- [x] Brain review and learning commands.
- [x] Trading plan commands and pre-trade checklist.
- [x] Strategy knowledge-base workflow.
- [x] Feishu production wiring support that can be completed locally.
- [x] Real testnet order placement beyond `/order/test` for Spot Testnet only.

## Phase 1: Brain Review And Learning Commands

Status: completed

Acceptance criteria:

- [x] `/review-add` stores a daily review from Brain.
- [x] `/review-summary` returns recent review summaries.
- [x] `/lesson` stores a knowledge card from Brain.
- [x] Commands are audited through existing `brain_audit_logs`.
- [x] All behavior has tests.

## Phase 2: Trading Plan Layer

Status: completed

Acceptance criteria:

- [x] Store daily trading plan and allowed symbols.
- [x] Store pre-trade checklist answers.
- [x] Block execution commands when the plan/checklist is missing or violated.

## Phase 3: Strategy Knowledge Base

Status: completed

Acceptance criteria:

- [x] Add structured command(s) for technical/theory cards.
- [x] Add search/list command(s) for knowledge cards.
- [x] Add mistake-pattern tags that connect reviews to learning cards.

## Phase 4: Feishu Production Connection

Status: local-ready

Acceptance criteria:

- [x] Provide local Feishu event smoke test script.
- [x] Map Feishu user identity to local user id through `FEISHU_USER_MAP`.
- [ ] Configure public HTTPS callback separately from repository.
- [ ] Verify events end-to-end from phone to local Brain after external Feishu setup.

## Phase 5: Expanded Testnet Execution

Status: completed

Acceptance criteria:

- [x] Add explicit create/cancel/get order commands for Binance Spot Testnet only.
- [x] Keep live trading disabled.
- [x] Require stricter confirmation and local plan/checklist checks.

## Completion Boundary

The local codebase is complete through the planned local phases. Remaining work is external setup:

- Feishu app credentials and public HTTPS callback URL.
- Phone-to-local end-to-end validation after Feishu setup.
