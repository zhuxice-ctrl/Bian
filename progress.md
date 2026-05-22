# Progress

## 2026-05-20

- Created persistent plan files: `task_plan.md`, `findings.md`, and `progress.md`.
- Set current execution focus to Phase 1: Brain Review And Learning Commands.
- Added Brain tests for `/review-add`, `/review-summary`, and `/lesson`.
- Implemented Brain review persistence, recent review summaries, and knowledge-card persistence.
- Documented new Brain learning commands in `README.md`.
- Restarted local Brain and verified `/review-add`, `/lesson`, and `/review-summary` through `scripts/brain-chat.ps1`.
- Added Phase 2 trading plans and pre-trade checklists.
- Added execution blocking when the daily plan or checklist is missing or violated.
- Added Phase 3 tagged knowledge cards, knowledge search, and mistake-to-knowledge links.
- Added Phase 4 local Feishu event smoke script.
- Added Phase 5 Spot Testnet create/cancel/get order Brain commands with confirmation.
- Restarted local Brain and verified plan, checklist, guarded `/test-buy`, `/confirm`, knowledge search, and Feishu local event smoke end-to-end.
- Added Phase 6 natural-language chat fallback through the local Codex-compatible API.
- Added `scripts/set-local-codex-env.ps1` for local-only Codex API configuration.
- Restarted local Brain and verified plain text now returns `chat_unavailable` with configuration guidance instead of `unknown` when `LOCAL_CODEX_API_KEY` is absent.
- Added Phase 7 suggested command staging and safe `/run suggested` execution.
- Restarted local Brain and verified `/run suggested` executes the latest safe suggested `/review-add` command end-to-end.
- Added Phase 8 Brain history download, moving-average replay, and strategy experiment persistence.
- Restarted local Brain and verified `/history-download`, `/backtest-ma`, and `/experiment-summary` end-to-end with public BTCUSDT 1h data.
- Added Phase 9 review-to-experiment links and review context summaries.
- Added Phase 10 daily reports, weekly reports, next learning tasks, and learning report export records.
- Restarted local Brain and verified `/daily-report`, `/weekly-report`, and `/learning-next` end-to-end.
- Added Phase 11 Chinese Brain aliases, keyword commands, and guarded Chinese testnet buy confirmation.
- Added Phase 11 local read-only dashboard with overview, reviews, experiments, knowledge cards, learning reports, and K-line replay endpoints.
- Added a vanilla browser dashboard with canvas K-line rendering and experiment trade markers.

## 2026-05-21

- Embedded local TradingView Lightweight Charts in the dashboard replay view and pushed commit `d99e357`.
- Added default learning-symbol scope for `BTCUSDT` and `ETHUSDT` across Brain, CLI data download, CLI backtest, and testnet risk defaults; pushed commit `46ab4d6`.
- Started the next planned development pass from the user's MVP+ roadmap.
- Added planned Phase 12 Historical Data Center and Phase 13 Professional Backtest Report View to `task_plan.md`.
- Added Phase 12 market data catalog module with predictable `data/local/market_data/{SYMBOL}/{SYMBOL}-{INTERVAL}.csv` paths.
- Added CLI `refresh-market-data` and Brain `/market-refresh` for BTC/ETH multi-interval refresh.
- Added dashboard `/api/datasets` plus a historical data picker that loads selected local CSV data into the existing K-line chart.
- Added Phase 13 backtest report payloads with round trips, equity curve, fees, win/loss counts, and max drawdown.
- Added dashboard `/api/backtest-report` and report UI panels for metrics, equity curve, and clickable trade rows.
- Started Phase 14A experiment review loop.
- Added Phase 14A/14B sections to `task_plan.md` and created the Phase 14 implementation plan.
- Added deterministic experiment review drafts with Brain `/experiment-review`, dashboard `/api/experiment-review`, storage, and export support.
- Verified Phase 14A with targeted tests and full suite: `148 passed`.
- Added Phase 14B dashboard review card with review summary, risk flags, focus trades, review questions, and learning tasks.
- Added focus-trade location buttons that reuse the existing trade focus behavior.
- Fixed dashboard compatibility for older local databases that do not yet have `experiment_review_drafts`.
- Browser-verified `http://127.0.0.1:8781/`: review card renders, focus-trade click updates trade detail, and fresh console logs are clean.
- Started Phase 15 experiment review learning-loop commit.
- Added Chinese Brain command `沉淀实验复盘 实验=... 日期=...` and internal `/experiment-review-commit`.
- The commit command now turns an experiment review draft into a daily review, generated knowledge cards, links, and a daily learning report.
- Switched subsequent development to file-based planning workflow using `task_plan.md`, `findings.md`, and `progress.md`.
- Added planned Phase 15S, Phase 16, and Phase 17 sections to the project plan.
- Verified Phase 15S with `pytest -q` (`153 passed`), dashboard JavaScript syntax check, and current-diff sensitive information scan before commit.
- Started Phase 16 professional backtest software experience.
- Phase 16 v1 scope: report filter metadata, dashboard trade filters, and multi-experiment comparison.
- Added backtest report filter metadata, round-trip result annotations, and experiment comparison payload/API.
- Added dashboard trade filters for side, result, date range, and risk flag, plus a read-only experiment comparison table.
- Browser-verified `http://127.0.0.1:8782/` on desktop and mobile: filters and comparison render, interactions update visible rows, and console logs are clean.
- Verified Phase 16 with `pytest -q` (`155 passed`) and dashboard JavaScript syntax check.
- Verified Phase 16S with `pytest -q` (`155 passed`), dashboard JavaScript syntax check, and current-diff sensitive information scan before commit.
- Started Phase 17 Feishu phone access configuration.
- Added Feishu bot reply client and Windows user-environment setup script for Feishu app configuration.
- Local Feishu callback smoke passed for URL verification and `/status` text event.
- Verified Phase 17 local changes with `pytest -q` (`158 passed`).

## 2026-05-22

- Reframed the final product goal as an AI-led, local-first quant workstation.
- Confirmed the product boundary: assistant as brain, local program as hands, user as student/final risk authority, server as Feishu bridge/task queue.
- Updated `task_plan.md` to mark Phase 17 as completed based on the working server Feishu bridge and phone verification.
- Added Phase 18 through Phase 28 to `task_plan.md` as the remaining roadmap toward the final product.
- Recorded Phase 18-22 as the immediate next development block: local-first architecture, server task queue, local Quant Runner, Feishu remote backtest execution, and local Codex/LLM bridge with mock mode.
- Created the Phase 18-22 implementation plan at `docs/superpowers/plans/2026-05-22-phase-18-22-remote-runner.md`.
- Added `/llm-status`, Chinese link-check aliases, and deterministic mock-mode guidance when local Codex/LLM is unavailable.
- Added server-side `remote_tasks` queue storage, Brain queue commands, and token-protected runner HTTP endpoints.
- Added local `quant-runner` execution path with whitelisted `local_status` and `backtest_ma` tasks.
- Added Windows scripts for starting the local quant runner and opening the server-to-local LLM reverse tunnel.
- Added Chinese `远程回测 ...` alias that queues a local runner backtest instead of executing on the server.
- Verified the Phase 18-22 target tests with `37 passed`.
- Added Phase 23 deterministic AI coach commands `/coach-next` and `/coach-evaluate`.
- Added Phase 24 strategy profiles and MA parameter sweep persistence.
- Added Phase 25 sanitized testnet status and local testnet order lifecycle records.
- Added Phase 26 local health check, SQLite backup, and restore support.
- Added Phase 27 production readiness gate commands that keep real trading disabled.
- Added Phase 28 Chinese operation docs for local setup, server setup, and daily use.
