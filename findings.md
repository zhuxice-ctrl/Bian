# Findings

## 2026-05-20

- The repository is clean on `main` and synced with GitHub.
- Local Brain `/status` is reachable through `scripts/brain-chat.ps1`.
- Windows user environment has Binance Testnet key presence; keys are not stored in the repository.
- Existing review storage is available through `daily_reviews`.
- Existing knowledge storage is available through `knowledge_cards`.
- Brain command handler currently supports status, test buy, and confirmation; review/learning commands are the next missing layer.
- Brain command values are currently parsed as simple `key=value` tokens; spaces can be represented with underscores and converted for stored display text.
