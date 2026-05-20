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
- [ ] Brain review and learning commands.
- [ ] Trading plan commands and pre-trade checklist.
- [ ] Strategy knowledge-base workflow.
- [ ] Feishu production wiring.
- [ ] Real testnet order placement beyond `/order/test`.

## Phase 1: Brain Review And Learning Commands

Status: completed

Acceptance criteria:

- [x] `/review-add` stores a daily review from Brain.
- [x] `/review-summary` returns recent review summaries.
- [x] `/lesson` stores a knowledge card from Brain.
- [x] Commands are audited through existing `brain_audit_logs`.
- [x] All behavior has tests.

## Phase 2: Trading Plan Layer

Status: next

Acceptance criteria:

- Store daily trading plan and allowed symbols.
- Store pre-trade checklist answers.
- Block execution commands when the plan/checklist is missing or violated.

## Phase 3: Strategy Knowledge Base

Status: pending

Acceptance criteria:

- Add structured command(s) for technical/theory cards.
- Add search/list command(s) for knowledge cards.
- Add mistake-pattern tags that connect reviews to learning cards.

## Phase 4: Feishu Production Connection

Status: pending

Acceptance criteria:

- Configure public HTTPS callback separately from repository.
- Map Feishu user identity to local user id.
- Verify events end-to-end from phone to local Brain.

## Phase 5: Expanded Testnet Execution

Status: pending

Acceptance criteria:

- Add explicit create/cancel/get order commands for Binance Spot Testnet only.
- Keep live trading disabled.
- Require stricter confirmation and local risk checks.
