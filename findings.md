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
