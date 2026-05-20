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
