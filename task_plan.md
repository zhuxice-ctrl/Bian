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
- [x] Phase 14A experiment review draft API and Brain command.
- [x] Phase 14B dashboard experiment review card.
- [x] Phase 15 experiment review learning loop.
- [x] Phase 16 professional backtest software experience.
- [x] Phase 17 Feishu phone access through the server Brain.
- [x] Phase 18-38 final product skeleton: AI-led local quant workstation.
- [ ] Phase 39+ final product roadmap: professional research, execution safety, and daily-use polish.

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

## Phase 14A: Experiment Review Draft API And Brain Command

Status: completed

Scope:

- Generate deterministic review drafts from stored backtest report payloads.
- Persist one updatable review draft per strategy experiment.
- Expose a local read-only API to inspect the review draft payload.
- Add a Brain command that saves the draft and returns learning questions/tasks.
- Keep all behavior local; no external model calls and no trading execution path.

Acceptance criteria:

- [x] Schema includes `experiment_review_drafts` with one draft per experiment.
- [x] A deterministic builder creates summary, risk flags, review questions, focus trades, and learning tasks.
- [x] Brain `/experiment-review experiment=...` persists/upserts a draft and audits the command.
- [x] Dashboard `/api/experiment-review?experiment=...` returns a generated or stored read-only draft payload.
- [x] Export includes experiment review drafts.
- [x] Tests cover builder rules, storage, Brain command, dashboard API, and export payload.

## Phase 14B: Dashboard Experiment Review Card

Status: completed

Scope:

- Add a dashboard panel that displays the experiment review draft beside the backtest report.
- Keep dashboard read-only: viewing drafts only, no trade execution controls.
- Make the review questions and learning tasks usable during manual replay.

Acceptance criteria:

- [x] The dashboard renders review summary, risk flags, focus trades, questions, and tasks for the selected experiment.
- [x] Empty/missing review draft states are clear.
- [x] Static UI tests and browser smoke tests cover the panel.

## Phase 15: Experiment Review Learning Loop

Status: completed

Scope:

- Add a Chinese Brain command to commit one experiment review draft into durable learning records.
- Generate or refresh the experiment review draft before committing it.
- Write or update the daily review, generated knowledge cards, review-experiment link, review-knowledge links, and daily learning report.
- Keep the dashboard read-only and avoid any trading execution path.

Acceptance criteria:

- [x] `沉淀实验复盘 实验=... 日期=...` routes to the local Brain write command.
- [x] `/experiment-review-commit experiment=... date=...` writes learning-loop records from a deterministic draft.
- [x] Rerunning the command is idempotent for generated daily reviews, knowledge cards, and links.
- [x] Tests cover the Chinese alias, persistence behavior, and idempotency.

## Development Planning Workflow

Status: active

Rules for future phases:

- Keep `task_plan.md`, `findings.md`, and `progress.md` as the persistent planning source of truth.
- Before implementation, add or update the target phase with scope, acceptance criteria, and test strategy.
- Use TDD for behavior changes: write failing tests first, verify the failure, then implement.
- After each phase, update progress and findings with the concrete result and verification output.
- Keep dashboard write actions out of scope unless a separate safety design is approved.

## Phase 15S: Commit And Push Phase 15

Status: completed

Scope:

- Review Phase 15 diff.
- Commit the current Phase 15 implementation and planning artifacts.
- Push to GitHub `main` after verification.

Acceptance criteria:

- [x] `pytest -q` passes.
- [x] Dashboard JavaScript syntax check passes.
- [x] Sensitive information scan shows no newly committed credentials.
- [x] Commit is created with a clear Phase 15 message.
- [x] Commit is pushed to GitHub `main`.

## Phase 16: Professional Backtest Software Experience

Status: completed

Scope:

- Improve the dashboard backtest workspace from a single experiment viewer into a stronger analysis tool.
- Add trade filtering by side, PnL result, date range, and risk/review flag.
- Add experiment date/range controls for chart and report panels.
- Add parameter summary and comparison for multiple experiments.
- Keep dashboard read-only and avoid adding any trading or secret-bearing surface.

Acceptance criteria:

- [x] Dashboard can filter visible trades without mutating stored records.
- [x] Report payload supports enough metadata for range and filter views.
- [x] User can compare at least two experiments by metrics and parameters.
- [x] Static UI tests cover controls and expected DOM markers.
- [x] Data-layer tests cover filtering and comparison payloads.
- [x] Browser verification confirms chart/report controls render and do not overlap.

## Phase 17: Feishu Phone Access

Status: completed

Scope:

- Connect Feishu mobile messages to local Brain through the existing event endpoint.
- Support phone queries for status, recent experiments, experiment reviews, daily learning reports, and next learning tasks.
- Allow safe learning commands from phone, including experiment review commit.
- Keep Binance keys, local Codex keys, and Feishu secrets in the local environment only.
- Keep all trading execution commands behind existing plan, checklist, and confirmation guards.
- Support the deployed server path where Feishu reaches the server Brain and the server keeps only Feishu bridge secrets.

Acceptance criteria:

- [x] Local Feishu event smoke tests cover safe learning queries and commands.
- [x] User mapping routes Feishu open_id values to local Brain users.
- [x] Phone-facing responses are concise and Chinese-first when Feishu app credentials are configured.
- [x] No API keys or secrets are returned in responses, logs, or exports.
- [x] End-to-end setup supports public HTTPS callback requirements.
- [x] Real Feishu app credentials are configured outside the repository.
- [x] Public HTTPS callback is configured in Feishu developer console.
- [x] Phone-to-Brain is verified with a real mobile message.

## Phase 16S: Commit And Push Phase 16

Status: completed

Scope:

- Review Phase 16 diff.
- Commit the current Phase 16 dashboard analysis improvements and planning artifacts.
- Push to GitHub `main` after verification.

Acceptance criteria:

- [x] `pytest -q` passes.
- [x] Dashboard JavaScript syntax check passes.
- [x] Sensitive information scan shows no newly committed credentials.
- [x] Commit is created with a clear Phase 16 message.
- [x] Commit is pushed to GitHub `main`.

## Final Product Target

Status: active planning

Build an AI-led, local-first crypto quant learning and execution workstation:

- The assistant acts as the brain, coach, research lead, and system designer.
- The local quant program acts as the hands: data, backtests, Binance access, dashboard, execution, logs, and recovery.
- The user remains the student and final authority for risk-bearing decisions.
- The server acts as a stable Feishu bridge and task queue, not as the holder of exchange keys or the primary trading engine.
- Feishu acts as a light remote command and learning interface, not as the main trading workstation.

Core boundaries:

- Binance keys and real trading authority stay on the local machine.
- Server-side Brain can record learning state and queue tasks, but should not directly place exchange orders.
- Local Quant Runner pulls tasks from the server; the server does not directly control the local PC.
- Real trading remains disabled until a separate production-readiness gate is explicitly completed.

## Phase 18: Local-First Quant Architecture And Capability Boundary

Status: completed

Scope:

- Formalize the split between server Brain, local Brain, local Quant Runner, dashboard, Codex/LLM, and Binance clients.
- Define command permission levels: query, learning write, backtest, testnet, and real trading.
- Add product-level documentation that explains what runs on the server and what must remain local.
- Add status commands for Feishu and local chat: `检查链接`, `检查LLM连接`, `电脑状态`, and `/llm-status`.

Acceptance criteria:

- [x] Architecture document explains server/local responsibilities.
- [x] Capability matrix lists every command class and its allowed runtime.
- [x] Feishu can report server status, local runner status, and LLM status separately.
- [x] Missing local LLM returns useful mock-mode guidance instead of a dead-end error.
- [x] Tests cover the new status commands and mock/unavailable states.

## Phase 19: Server Task Queue And Feishu Remote Intake

Status: completed

Scope:

- Add a durable server-side task queue for remote requests from Feishu.
- Convert eligible Feishu commands into structured queued tasks instead of direct local execution.
- Add task states: queued, claimed, running, succeeded, failed, rejected, expired.
- Add audit logs for who requested each task and how it was resolved.

Acceptance criteria:

- [x] Feishu can create a task for safe query, backtest, sync, or learning actions.
- [x] Task records include requester, command text, parsed task type, risk level, state, timestamps, and result summary.
- [x] Feishu can query recent task status.
- [x] Invalid or high-risk requests are rejected with a clear reason.
- [x] Tests cover task creation, state transitions, and Feishu response text.

## Phase 20: Local Quant Runner MVP

Status: completed

Scope:

- Build a Windows-friendly local runner that periodically pulls queued tasks from the server.
- Execute only whitelisted local quant operations.
- Return structured results to the server for Feishu replies and learning records.
- Provide startup scripts for manual run and long-running mode.

Acceptance criteria:

- [x] `quant-runner` can authenticate to the server without storing secrets in the repository.
- [x] Runner can claim one task at a time and prevent duplicate execution.
- [x] Runner can execute safe local tasks: status and backtest replay.
- [x] Runner executes through the existing local Brain handler so normal audit logs are written for backtest commands.
- [x] Runner returns success/failure summaries to the server.
- [x] Tests cover claim/execute/report behavior without calling real Binance.

## Phase 21: Remote Backtest Execution From Feishu

Status: completed

Scope:

- Allow Feishu to request local backtests through the server queue and local runner.
- Support structured Chinese commands for symbol, interval, strategy, date range, and parameters.
- Store generated experiments in the local database and send concise summaries back to Feishu.
- Keep full charts and detailed analysis in the local dashboard.

Acceptance criteria:

- [x] Feishu command can queue a local backtest request.
- [x] Local runner executes the backtest using local data and stores the experiment.
- [x] Feishu can query task status and see completion summary after runner reports it.
- [x] Dashboard can open the resulting experiment normally from the local database.
- [x] Tests cover parsing, queueing, execution, and result serialization.

## Phase 22: Local Codex/LLM Bridge And Mock Mode

Status: completed

Scope:

- Keep default server mode deterministic and useful without local LLM access.
- Add a Windows script that opens an SSH reverse tunnel from server loopback to local Codex-compatible API.
- Keep `LocalCodexClient` loopback-only and never expose the local LLM publicly.
- Let Brain check LLM health at request time instead of requiring a service restart.

Acceptance criteria:

- [x] `scripts/connect-server-llm.ps1` creates a reverse tunnel to the server loopback address.
- [x] `/llm-status` reports configured, reachable, unavailable, or mock mode.
- [x] Natural-language requests degrade to deterministic command suggestions when LLM is unavailable.
- [x] No arbitrary remote LLM URL is accepted unless it is explicitly loopback-safe.
- [x] Tests cover LLM status and fallback behavior.

## Phase 23: AI Coach Experiment Cycle

Status: completed

Scope:

- Turn stored experiments and review drafts into an AI-led study loop.
- Generate the next experiment proposal from recent performance, risk flags, and learning gaps.
- Track assignments, hypotheses, outcomes, and follow-up tasks.
- Keep the first version deterministic; add LLM enhancement only after the deterministic flow is stable.

Acceptance criteria:

- [x] Brain can propose the next experiment from recent experiment history.
- [x] Each proposal includes hypothesis, parameters, expected learning value, and stop criteria.
- [x] Completed experiments can be compared against their original hypothesis.
- [x] Experiment proposals persist status and outcome for later reporting.
- [x] Tests cover deterministic proposal generation and evaluation.

## Phase 24: Strategy Lab And Parameter Research

Status: completed

Scope:

- Improve the strategy research layer beyond a single moving-average replay.
- Add parameter sweeps, saved strategy profiles, and multi-experiment comparison groups.
- Consider mature open-source quant projects as references, but keep Bian as the product shell.
- Keep strategy execution local and reproducible.

Acceptance criteria:

- [x] Strategy profiles are stored with parameters and description.
- [x] Parameter sweep results are persisted as grouped experiments.
- [x] Sweep payload highlights overfitting risk.
- [x] Reports distinguish research performance from actionable trading readiness through research-only warnings.
- [x] Tests cover profile storage and sweep execution.

## Phase 25: Testnet Operations Workbench

Status: completed

Scope:

- Build a local-only testnet operations surface for Binance Spot Testnet.
- Connect testnet orders to plans, checklists, reviews, and strategy experiments.
- Support Feishu only as a request/notification layer with confirmation controls.
- Keep execution guarded by plan, checklist, confirmation, and audit logs.

Acceptance criteria:

- [x] Brain shows sanitized testnet account status without exposing secrets.
- [x] Confirmed testnet orders are stored as local order lifecycle records.
- [x] Feishu can request a testnet action, but execution requires existing plan/checklist/confirmation flow.
- [x] Failed or rejected testnet actions create reviewable audit entries through Brain audit logs.
- [x] Tests cover guardrails and order lifecycle records.

## Phase 26: Observability, Backup, And Recovery

Status: completed

Scope:

- Make the system reliable enough for daily use.
- Add health checks, backup scripts, restore scripts, and server/local sync diagnostics.
- Add clear startup checks for local dashboard, local runner, Brain, database, Feishu, and LLM tunnel.

Acceptance criteria:

- [x] One command can check local system health.
- [x] Server bridge health is visible through `/status`, `/llm-status`, and `/task-status`.
- [x] SQLite backup and restore are documented and tested.
- [x] Health output avoids secret-bearing fields.
- [x] Tests cover backup metadata and health-check response shapes.

## Phase 27: Production Trading Readiness Gate

Status: completed

Scope:

- Define the requirements before any real Binance trading is enabled.
- Add dry-run enforcement, daily loss limits, symbol allowlists, position limits, cooldowns, and kill-switch controls.
- Require local manual approval before enabling any real trading mode.
- Keep this phase as a gate, not an automatic activation.

Acceptance criteria:

- [x] Real trading remains disabled by default.
- [x] A readiness checklist is exposed before any real trading configuration can be considered.
- [x] Risk limit checks are represented as missing readiness gates until separately implemented.
- [x] Kill-switch is active in the default readiness status.
- [x] Feishu cannot bypass local real-trading confirmation because enable commands are blocked.
- [x] Tests prove real trading enablement is blocked.

## Phase 28: Final Product Packaging

Status: completed

Scope:

- Make the system maintainable as a personal product rather than a development prototype.
- Add setup, update, deploy, backup, and recovery guides.
- Provide simple entrypoints for daily use: local dashboard, local runner, Feishu commands, and study reports.
- Keep developer workflows separate from normal user workflows.

Acceptance criteria:

- [x] Local setup guide can recreate the system on a fresh Windows machine.
- [x] Server setup guide can recreate the Feishu bridge on a fresh Ubuntu server.
- [x] Daily-use command guide is Chinese-first.
- [x] Update/deploy process is documented.
- [x] Final verification includes full tests, dashboard JavaScript check, and sensitive information scan.

## Phase 29: Local Application Console

Status: completed

Scope:

- Reference mature quant application structures without copying external project code.
- Add a unified local console to the existing dashboard for system status, task queue, AI Coach, strategy lab, Testnet records, and production gate.
- Keep the console read-only and local-first.
- Preserve the existing replay/report workspace.

Acceptance criteria:

- [x] Dashboard exposes `/api/control-console`.
- [x] Control console payload includes health, remote tasks, coach proposals, strategy profiles, parameter sweeps, testnet records, production gate, and reference notes.
- [x] Static dashboard shows console panels for tasks, coach proposals, strategy lab, sweeps, testnet orders, and real-trading gate.
- [x] Tests cover dashboard data payload, HTTP route, and static UI markers.
- [x] Documentation records the Freqtrade/Jesse/vectorbt reference direction.

## Phase 30: Server Deployment And Runner Route Verification

Status: completed

Scope:

- Deploy the latest local code to the Ubuntu server that hosts the Feishu bridge.
- Keep secrets in server/local environment variables only.
- Expose only the token-protected runner queue endpoints publicly.
- Verify the server Brain, nginx, local runner, and local dashboard after deployment.

Acceptance criteria:

- [x] Server `bian-brain` is active and health check returns `status=ok`.
- [x] Server nginx is active and `/feishu/events` remains configured.
- [x] Public `/runner/claim` and `/runner/complete` route to Brain and reject bad tokens.
- [x] Local `quant-runner --once` can claim and complete a queued status task through the public server URL.
- [x] Local test suite and dashboard JavaScript syntax checks pass.

## Phase 31: Clean Workspace And Data Provenance

Status: completed

Scope:

- Make the clean, no-real-data state explicit in dashboard and Brain responses.
- Add provenance labels for local data: manual, backtest, generated, remote task, testnet, system.
- Add a safe reset workflow that backs up the SQLite database before clearing local learning/research records.
- Keep exchange keys, Feishu secrets, local LLM settings, and market CSV cache out of reset scope.

Acceptance criteria:

- [x] CLI has a `reset-workspace` command that requires explicit confirmation and writes a backup.
- [x] Brain has a low-risk `/workspace-status` query and a guarded `/workspace-reset confirm=...` command.
- [x] Dashboard overview includes `workspace_state` and data source counts.
- [x] Tests prove reset clears business records but preserves schema and does not touch secrets.

## Phase 32: Real Market Data Center

Status: completed

Scope:

- Extend the default BTC/ETH market intervals to `1m,5m,15m,1h,4h,1d`.
- Surface dataset freshness, candle count, first/last candle time, and source labels in dashboard.
- Add a status command that explains whether data is cached locally or missing.
- Keep data download public-only and local-cache based.

Acceptance criteria:

- [x] Default inventory includes `4h` and `1d`.
- [x] Dataset payloads include `source`, `exists`, `updated_at`, and clear missing states.
- [x] Brain `/market-status` summarizes cached and missing datasets.
- [x] Tests cover inventory payloads and status command output.

## Phase 33: Local Backtest Workbench

Status: completed

Scope:

- Let the local dashboard start a safe MA backtest from selected cached data and parameters.
- Persist the generated experiment and trades so existing report/replay views can open it.
- Keep the operation local, deterministic, and limited to allowed symbols and `data/local` CSV paths.

Acceptance criteria:

- [x] Dashboard exposes a local-only backtest action endpoint.
- [x] Action validates symbol, interval, CSV path, and MA parameters.
- [x] Successful action returns an experiment id and summary metrics.
- [x] Tests cover action validation, persistence, and HTTP response shape.

## Phase 34: Learning Loop Actions

Status: completed

Scope:

- Make experiment review and review-commit usable as first-class local actions.
- Show what should be reviewed next when experiments exist but learning records do not.
- Keep writes deterministic and auditable through existing Brain logic.

Acceptance criteria:

- [x] Dashboard control console includes `next_review_actions`.
- [x] Local action can persist an experiment review draft.
- [x] Local action can commit an experiment review into review/knowledge/report records.
- [x] Tests cover empty state, draft persistence, and commit action.

## Phase 35: Feishu Remote Loop Polish

Status: completed

Scope:

- Improve remote task status output so Feishu can return useful completion summaries.
- Keep task queue operations token-protected and avoid exposing local secrets.

Acceptance criteria:

- [x] `/task-status` returns a concise Chinese-readable `message`.
- [x] Completed remote tasks include result summary and payload for Feishu status follow-up.
- [x] Tests cover task status text for queued and succeeded tasks.

## Phase 36: AI Coach Daily Flow

Status: completed

Scope:

- Add a daily coach command that turns current workspace state into a short next-action plan.
- Prefer deterministic suggestions when there is no LLM connection.
- Keep recommendations research/learning oriented, not trading signals.

Acceptance criteria:

- [x] Brain `/coach-daily` returns next actions for empty workspace, data-ready workspace, and experiment-ready workspace.
- [x] Dashboard control console surfaces the same daily coach plan.
- [x] Tests cover deterministic branches.

## Phase 37: Local Application Shell

Status: completed

Scope:

- Turn the dashboard from a long page into a clearer local workstation shell.
- Add navigation anchors for console, data, backtest, review, knowledge, reports, and safety.
- Keep controls compact, readable, and non-overlapping on desktop and mobile.

Acceptance criteria:

- [x] Dashboard has stable navigation targets for the main work areas.
- [x] Empty states guide the first real workflow without pretending sample data exists.
- [x] Static UI tests cover the navigation and new controls.
- [x] Browser smoke check confirms the page renders cleanly.

## Phase 38: Safety Trading Preparation

Status: completed

Scope:

- Strengthen the visible safety boundary before any real trading discussion.
- Add explicit kill-switch/status commands and dashboard safety summaries.
- Keep real trading disabled and unimplemented.

Acceptance criteria:

- [x] Brain `/kill-switch-status` and `/kill-switch-enable` report safe disabled state without enabling real trading.
- [x] Dashboard safety panel shows kill-switch active, real trading disabled, and missing readiness gates.
- [x] Tests prove real trading remains blocked after safety commands.

## Phase 39: Product Direction And UX Specification

Status: drafted

Scope:

- Decide the final local application shape before rebuilding the dashboard UI.
- Define the daily first screen, navigation model, visual style, and core workflows.
- Keep the app local-first: Feishu remains a light remote interface, not the main terminal.
- Produce a written UI/product spec before implementation.
- Use navigation and subpages instead of cramming all features into one page.

Acceptance criteria:

- [x] A product spec defines the target workstation layout and user flows.
- [x] The first-screen workflow answers "what should I do today" without fake sample data.
- [x] The design separates research, learning, testnet, and safety states clearly.
- [ ] The spec is approved before major dashboard rewrites.

## Phase 40: Professional Local Quant Workstation UI

Status: completed

Scope:

- Rebuild the current dashboard into a professional research workstation.
- Add a left navigation rail, top system status bar, main workspace, and right AI Coach/review queue panel.
- Improve visual density, spacing, tables, forms, empty states, and mobile behavior.
- Keep all existing local APIs and safety boundaries intact.

Acceptance criteria:

- [x] The app no longer feels like a simple prototype dashboard.
- [x] Data, backtest, experiments, review, knowledge, tasks, safety, and settings are reachable as clear work areas.
- [x] Controls do not overlap or resize unpredictably on desktop or mobile.
- [x] Browser smoke tests verify the main workflows render cleanly.

## Phase 41: Market Data Pipeline Hardening

Status: planned

Scope:

- Replace overwrite-only data refresh with incremental append/merge.
- Add data completeness checks, gap detection, freshness warnings, and repair actions.
- Add optional ETF/stock data provider support behind a separate provider abstraction.
- Keep crypto public data and sensitive trading credentials separate.

Acceptance criteria:

- [ ] BTC/ETH cache refresh can update only new candles without duplicating rows.
- [ ] The app can report missing ranges and stale datasets.
- [ ] ETF/stock import path is supported through a configured provider or manual CSV import.
- [ ] Tests cover incremental refresh, gap detection, and provider boundaries.

## Phase 42: Strategy Engine Expansion

Status: planned

Scope:

- Move beyond MA-only research into a small, controlled strategy library.
- Add breakout, mean-reversion, volatility filter, grid-style research mode, and stop-loss/take-profit variants.
- Keep strategy definitions reproducible and versioned.
- Label every result as research-only until it passes validation.

Acceptance criteria:

- [ ] Strategy profiles can choose from multiple strategy families.
- [ ] Each strategy records parameters, data range, version, fees, and slippage assumptions.
- [ ] Backtest reports clearly show which strategy and assumptions produced the result.
- [ ] Tests cover strategy selection and parameter validation.

## Phase 43: Robust Backtesting And Validation

Status: planned

Scope:

- Add more realistic backtest assumptions: fees, slippage, latency, partial fills where practical.
- Add train/test splits, walk-forward validation, stress periods, and overfitting warnings.
- Add market-regime tagging for trend, range, high volatility, drawdown, and recovery periods.

Acceptance criteria:

- [ ] Experiments can run on selected date ranges and validation splits.
- [ ] Reports distinguish in-sample, out-of-sample, and stress-test results.
- [ ] Overfitting and unstable-parameter warnings are visible in the dashboard and Brain.
- [ ] Tests cover split generation, stress windows, and validation summaries.

## Phase 44: Experiment Portfolio And Comparison Lab

Status: planned

Scope:

- Let the system compare strategies, symbols, intervals, parameters, and date ranges as a portfolio of experiments.
- Add experiment ranking, tagging, saved comparison groups, and reject/continue decisions.
- Track why a strategy was promoted, paused, or discarded.

Acceptance criteria:

- [ ] The dashboard can compare multiple experiments side by side.
- [ ] AI Coach can explain the next research priority from experiment history.
- [ ] Each experiment can be marked as rejected, needs more data, testnet candidate, or archived.
- [ ] Tests cover comparison groups and decision persistence.

## Phase 45: Learning System Deepening

Status: planned

Scope:

- Turn experiment results into a structured curriculum for the user.
- Improve knowledge cards, mistake patterns, daily review prompts, and weekly learning summaries.
- Add spaced repetition or review queue behavior for important lessons.

Acceptance criteria:

- [ ] Failed experiments generate learning tasks and mistake-pattern cards.
- [ ] The app shows a review queue ranked by importance and recency.
- [ ] Daily/weekly reports connect learning progress to actual experiments.
- [ ] Tests cover generated tasks, review queue ranking, and report links.

## Phase 46: Feishu Remote Study Assistant

Status: planned

Scope:

- Polish Feishu as a remote command and study interface.
- Support status checks, data refresh requests, backtest requests, review summaries, task lists, and learning reminders.
- Keep Feishu away from unrestricted local automation and real-trading execution.

Acceptance criteria:

- [ ] Chinese Feishu commands cover common remote study workflows.
- [ ] Long tasks return task ids and readable completion summaries.
- [ ] Remote actions remain queue-based and token-protected.
- [ ] Tests prove Feishu cannot bypass local execution safety.

## Phase 47: Testnet Strategy Execution Loop

Status: planned

Scope:

- Promote selected research candidates into Binance Spot Testnet only.
- Connect strategy signals, paper/testnet orders, order lifecycle, post-trade review, and learning reports.
- Keep confirmation, plan, checklist, and kill-switch controls active.

Acceptance criteria:

- [ ] A research experiment can be explicitly promoted to a testnet candidate.
- [ ] Testnet execution records link back to strategy, signal, plan, checklist, and review records.
- [ ] Kill-switch and risk guards block execution when unsafe.
- [ ] Tests cover the full testnet lifecycle without touching real trading.

## Phase 48: Real Trading Readiness Implementation

Status: planned

Scope:

- Implement the missing readiness gates before any real trading is possible.
- Add account mode separation, position limits, daily loss limits, max order size, cooldowns, allowlists, dry-run mode, and emergency stop behavior.
- Keep real trading disabled by default and require a separate explicit activation process.

Acceptance criteria:

- [ ] The system can explain every missing real-trading requirement.
- [ ] Risk checks are implemented and tested independently.
- [ ] Dry-run mode can simulate the exact order path without sending real orders.
- [ ] No real order can be sent without local manual activation and passing all gates.

## Phase 49: Semi-Automated Small-Capital Pilot

Status: planned-blocked

Scope:

- Only after Phase 48 passes, allow a tightly limited real-trading pilot.
- Start with manual confirmation for every order and very small capital.
- Require daily review, loss-limit enforcement, and rollback procedures.

Acceptance criteria:

- [ ] User explicitly approves entering this phase after reviewing risks.
- [ ] Every pilot order has manual confirmation, audit log, and post-trade review.
- [ ] Daily loss and position limits are enforced in code.
- [ ] The phase can be stopped instantly through kill-switch.

## Phase 50: Operations, Packaging, And Maintenance

Status: planned

Scope:

- Make the system easy to run for months: startup, updates, backups, diagnostics, server deploys, and local recovery.
- Add versioned migrations, release notes, one-command health checks, and clear user docs.
- Keep secrets out of repo, logs, exports, and screenshots.

Acceptance criteria:

- [ ] A normal daily startup flow works after Windows reboot and network verification.
- [ ] Server bridge deploy/update steps are documented and repeatable.
- [ ] Backups and restores are verified against the current schema.
- [ ] Final verification includes tests, dashboard browser QA, JavaScript syntax check, and secret scan.
