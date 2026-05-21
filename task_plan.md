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
- [x] Natural-language chat fallback through local Codex API.
- [x] Suggested command staging and safe `/run suggested`.
- [x] Brain history download, replay backtest, and experiment records.
- [x] Review-to-experiment learning loop.
- [x] Daily and weekly learning reports.
- [x] Chinese Brain aliases and keyword commands.
- [x] Local read-only dashboard with K-line replay.
- [x] Phase 12 historical data center for BTCUSDT and ETHUSDT.
- [x] Phase 13 professional backtest report view.

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
- Local Codex API key must be configured in the Windows user environment before natural-language chat is active.

## Phase 6: Natural-Language Chat Layer

Status: completed

Acceptance criteria:

- [x] Non-command text can route to a local Codex-compatible model.
- [x] Missing local model configuration returns a clear safe response instead of `unknown`.
- [x] Natural-language responses cannot execute trades directly.
- [x] Local setup script prompts for `LOCAL_CODEX_API_KEY` without storing it in the repository.

## Phase 7: Suggested Command Safety Layer

Status: completed

Acceptance criteria:

- [x] Natural-language responses can persist a `suggested_command`.
- [x] `/run suggested` executes the latest safe low-risk suggestion once.
- [x] High-risk suggestions such as trading or confirmation commands are blocked from automatic execution.
- [x] Suggested command results are stored for auditability.

## Phase 8: History Replay And Experiment Records

Status: completed

Acceptance criteria:

- [x] Brain can download public Binance Spot K-lines to local CSV without API keys.
- [x] Brain can run a moving-average replay from a local CSV.
- [x] Backtest trades and experiment metrics are persisted for review.
- [x] Brain can list recent experiment summaries.
- [x] Export includes strategy experiment records.

## Phase 9: Review Experiment Learning Loop

Status: completed

Acceptance criteria:

- [x] Brain can link a daily review to a strategy experiment.
- [x] Brain can return a review context bundle with review details, linked experiments, and linked knowledge cards.
- [x] `/run suggested` can execute safe `/experiment-link` suggestions.
- [x] Export includes review-to-experiment links.

## Phase 10: Learning Reports

Status: completed

Acceptance criteria:

- [x] Brain can store a daily learning report from existing plan, checklist, review, experiment, and knowledge records.
- [x] Brain can store a weekly learning report with aggregate trade count, PnL, plan-follow rate, and focus tags.
- [x] Brain can return next learning tasks for a review day without placing orders or calling an external model.
- [x] Export includes learning reports.

## Phase 11: Chinese Commands And Local Dashboard

Status: completed

Acceptance criteria:

- [x] Common Brain commands work through Chinese aliases and keyword-style input without a leading slash.
- [x] Trading aliases still require the existing plan, checklist, and confirmation guard.
- [x] The local dashboard serves read-only overview, review, experiment, knowledge, report, and K-line replay JSON.
- [x] The browser dashboard can display summary panels and K-line replay from local experiment CSV data.
- [x] The dashboard exposes no trading action and no local credentials.

## Phase 12: Historical Data Center

Status: completed

Scope:

- Keep the default learning universe limited to `BTCUSDT` and `ETHUSDT`.
- Provide one local workflow to download and refresh 1m, 5m, 15m, and 1h public Binance Spot K-lines.
- Store market data under `data/local` with predictable file names.
- Expose local dataset inventory to the dashboard so the user can choose symbol and interval without typing CSV paths.
- Keep data download public-data only; no exchange keys are required or exposed.

Acceptance criteria:

- [x] Brain/CLI can download or refresh the default BTC/ETH interval set.
- [x] Unsupported symbols remain blocked unless `TRADING_LEARNING_ALLOWED_SYMBOLS` is locally extended.
- [x] The dashboard can list available local datasets with symbol, interval, path, row count, first candle, and last candle.
- [x] Tests cover symbol scope, path safety, dataset inventory, and refresh behavior.

## Phase 13: Professional Backtest Report View

Status: completed

Scope:

- Upgrade replay from chart-only review into a report workspace.
- Add equity curve, realized PnL, round trips, win/loss counts, win rate, total fees, and drawdown-oriented metrics.
- Add a trade list beside or below the chart; selecting a row should locate the matching trade on the K-line.
- Keep dashboard read-only and local-first.

Acceptance criteria:

- [x] Backtest report data is available through local dashboard APIs.
- [x] The dashboard shows metrics, trade list, and visual report panels for an experiment.
- [x] Clicking a trade row updates the replay detail and visible range.
- [x] Tests cover report metric calculation, API payload shape, and static UI markers.
