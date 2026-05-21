# Findings

## 2026-05-20

- The repository is clean on `main` and synced with GitHub.
- Local Brain `/status` is reachable through `scripts/brain-chat.ps1`.
- Windows user environment has Binance Testnet key presence; keys are not stored in the repository.
- Existing review storage is available through `daily_reviews`.
- Existing knowledge storage is available through `knowledge_cards`.
- Brain command handler currently supports status, test buy, and confirmation; review/learning commands are the next missing layer.
- Brain command values are currently parsed as simple `key=value` tokens; spaces can be represented with underscores and converted for stored display text.
- Execution commands now require a same-day trading plan and an approved pre-trade checklist for the symbol.
- Expanded order placement remains Spot Testnet only and still requires confirmation.
- Feishu production cannot be fully completed inside the repository because it needs an external public HTTPS callback and Feishu app configuration.
- Natural-language chat is intentionally non-executing: it can answer and suggest commands, but existing command handlers still control state changes and execution.
- Current machine has local-only Codex-compatible API configuration in the Windows user environment; do not store or print the key in repository files or final reports.
- `/run suggested` is intentionally limited to low-risk record/planning commands; trading and confirmation suggestions must be typed manually.
- Historical replay now persists simulated trades with experiment-scoped source ids, so repeated experiments do not collide with prior backtest trade external ids.
- Daily reviews can now be connected to replay experiments and knowledge cards through `/review-context`, making the learning loop queryable from Brain.
- Learning reports are deterministic local summaries; they do not call external models and do not add any trading execution path.

## 2026-05-21

- The current system is an MVP technical prototype, not a mature daily-use trading workstation.
- The next practical milestone should focus on `历史数据中心 + 专业回测报告页` before expanding Feishu or automated execution.
- Current market universe should stay narrow: default scope is `BTCUSDT` and `ETHUSDT`; later symbols should be explicitly added through local configuration.
- Existing dashboard K-line replay uses local bundled Lightweight Charts and is read-only; this should remain the visualization base for Phase 13.
- Existing market data layer can fetch one Binance Spot K-line request and write CSV, but it does not yet provide multi-interval batch refresh, local inventory, or data completeness checks.
- Existing backtest metrics include trade count, round trips, win rate, realized PnL, and total fees, but do not yet expose equity curve or drawdown-style report data for the dashboard.
- Phase 12 implements overwrite-style public data refresh for the configured limit. It does not yet do true incremental append/merge; that remains a future hardening step after the data center is usable.
- Dashboard dataset loading is read-only and reuses the same K-line chart engine as experiment replay.
- Phase 13 report metrics are deterministic from stored experiment trades. Equity curve currently advances on closed round trips, not mark-to-market on every candle; candle-by-candle equity can be added later if needed.
- Trade-row clicks update the existing replay detail panel and visible K-line range without adding any trading action surface.
- Phase 14A should stay deterministic and local. The review draft can be generated from stored report data without calling the local Codex API.
- `ai_drafts` already exists, but experiment review drafts need a dedicated table because they are tied to one strategy experiment and should be upsertable.
- `/api/experiment-review` is read-only from the dashboard perspective: it returns a stored draft when present, otherwise a generated unsaved preview.
- Brain `/experiment-review experiment=...` is the persistence path for review drafts and still does not expose any trading action.
