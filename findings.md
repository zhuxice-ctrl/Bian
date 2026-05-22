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
- Existing local databases may not have `experiment_review_drafts` until a write-path schema initialization runs; dashboard review preview now tolerates that table being absent.
- Phase 14B uses the review draft as explanation beside replay, not as an execution signal or trade recommendation.
- Phase 15 should keep dashboard writes out of scope. The safer first write path is Brain, because it already has local audit logging and command normalization.
- Generated experiment-review knowledge cards can be deterministic and idempotent by using experiment-scoped external ids.
- Knowledge cards can carry all risk flag tags, while review-to-knowledge links should remain one link per card to avoid noisy daily report context.
- Before Phase 16 or Phase 17 starts, Phase 15 should be committed and pushed so future work has a clean baseline.
- Phase 16 is dashboard-heavy and should include browser verification in addition to pytest and JavaScript syntax checks.
- Phase 17 depends on external Feishu app/public HTTPS setup, so repository work should focus on local event behavior, documentation, and safe command handling first.
- Phase 16 v1 keeps filtering client-side for visible trade rows. Stored experiment, trade, review, and knowledge records remain read-only from the dashboard.
- Round-trip result annotations are attached to both entry and exit trades so side/result filters can work on the existing trade table without adding a new storage table.
- Experiment comparison is read-only and uses stored `strategy_experiments` metrics/parameters; it does not recompute backtests.
- Feishu inbound callback alone is not enough for mobile use; the local service also needs a Feishu app id/secret so it can call the message API and reply to the chat.
- Feishu app credentials should stay in Windows user environment variables through `scripts/set-feishu-env.ps1`; the repository only stores prompts and variable names.
- Real phone verification still requires external setup: public HTTPS tunnel/reverse proxy, Feishu event subscription Request URL, bot message permissions, and app installation/publish in the tenant.

## 2026-05-22

- The final product should be an AI-led, local-first quant workstation rather than a simple Feishu bot or ordinary backtest dashboard.
- The assistant is the brain: coach, research lead, system designer, review author, and task planner. The program is the hands: data, backtests, Binance access, execution, logs, dashboard, and recovery.
- Feishu should remain a light remote interface for task intake, learning records, status checks, and concise summaries. It should not become the main trading terminal.
- The server should remain a stable bridge and task queue. It should not hold Binance exchange keys or directly execute real trading operations.
- The local PC should own all sensitive quant operations: Binance keys, full dashboard, local Codex/LLM, local data, backtests, and future trading execution.
- Remote automation should use a pull model: local Quant Runner pulls queued tasks from the server. The server should not directly control the local PC.
- Real trading must stay disabled until a dedicated readiness gate exists with local confirmation, risk limits, kill switch, audit logs, and tests proving Feishu cannot bypass local controls.
- The immediate product gap is Phase 18-22: capability boundary, server task queue, local runner, Feishu remote backtest path, and local LLM bridge/mock mode.
- Phase 18-22 MVP uses a pull model: the server stores `remote_tasks`, and the Windows `quant-runner` claims tasks through token-protected `/runner/claim` and reports through `/runner/complete`.
- The first remote task types are intentionally narrow: `local_status` and `backtest_ma`. Real trading and arbitrary shell/Codex execution are not task types.
- The server-side LLM bridge still enforces loopback-only local Codex URLs. The SSH reverse tunnel maps server loopback to local loopback and avoids publishing the local Codex API.
- Phase 23-28 complete the first final-product skeleton: deterministic AI coach proposals, strategy profiles, parameter sweeps, sanitized testnet workbench, health/backup commands, production gate, and Chinese operation docs.
- The strategy lab deliberately labels parameter sweeps as research-only because best-parameter selection on one sample is an overfitting risk.
- The production gate is a blocker, not an enablement path. Real trading still has no executable order route.
- Phase 29 should not replace Bian with Freqtrade/Jesse/vectorbt. The useful reference is application structure: status surfaces, research workflow separation, parameter-grid visibility, and explicit risk state.
- The local application console can remain read-only while still becoming the user's main application shell.
- After local smoke data was cleared, the product needs explicit empty-state guidance; otherwise a clean dashboard looks broken instead of ready.
- The next productization batch must avoid reintroducing sample data. All new flows should either read real local cache, generate deterministic backtest records from user-selected data, or show a missing-data state.
- Dashboard writes are now limited to local, deterministic research/learning actions: MA backtest, experiment-review draft save, and experiment-review commit. No dashboard path touches exchange credentials or real trading.
- Market data inventory now intentionally shows missing cache entries so the user can see what still needs refresh instead of wondering why a selector is empty.
- Kill-switch commands are status/lock commands only; they do not create any path to enable real trading.
- The remaining product work should start with UX/product specification before code changes, because the user explicitly paused UI implementation and wants to discuss the right application shape.
- The next architecture direction remains local-first: local PC handles data, backtests, LLM/Codex, Binance keys, and execution; the server/Feishu layer handles remote task intake and short summaries.
- Stable-profit research requires broad experimentation, but the safe sequence is research, validation, testnet, readiness gates, then small-capital pilot. Unrestricted autonomous real trading remains out of scope.
- The preferred UI direction is not a single crowded dashboard. It should be a navigable workstation with separate pages for Today, Chart Lab, Data Center, Strategy Lab, Backtests, Experiments, Review, Knowledge, Testnet, Safety, and Settings.
- The real Chart Lab must use existing Lightweight Charts with real local data, not hand-drawn placeholder candles.
- Phase 40 can be done safely without a frontend framework migration because the existing vanilla dashboard already has stable API and chart integration points.
- The current local market cache only has a few 1h candles after workspace cleanup, so a browser screenshot may look visually sparse even though it is using the real Lightweight Charts surface and real local data. Data refresh belongs to Phase 41.
- Market data refresh now starts from the next expected candle after the existing local cache, then merges by `opened_at`; this avoids duplicate rows and preserves older local history.
- Manual ETF/stock support is best handled first as CSV import into the same cache layout, before adding live third-party providers.
- Strategy expansion should stay research-only at this stage: adding signal families is safe, but promotion to testnet or real trading still requires later validation and safety phases.
- A generic strategy signal dispatcher lets the dashboard and Brain share strategy families without adding one endpoint per strategy.
- Validation summaries now distinguish selected date range, in-sample, out-of-sample, and stress-window context. These warnings are evidence for research decisions, not trading permission.
- `BacktestMetrics` does not carry drawdown directly; drawdown is produced by the richer report builder. Validation slice summaries should avoid assuming report-only fields exist.
- Experiment promotion is now represented as a decision record, not an execution path. Marking `testnet_candidate` creates research state only; it does not place or enable orders.
- Failed experiments should create deterministic mistake-pattern knowledge cards rather than free-form notes, so the learning queue can rank them reliably without LLM access.
- Review queue priority is derived from source, category, risk tags, and recency; it is a study workflow, not a trading signal.
- The dashboard had a latent JavaScript scope bug where experiment decisions were rendered from `renderReferenceList` using a local variable from another function. Moving that rendering into `renderStrategyLab` keeps runtime behavior consistent with the data payload.
- Feishu remains safest when long-running work becomes a `remote_tasks` record and the local runner pulls it; adding `market_refresh` preserves that queue boundary instead of letting Feishu call local data downloads directly.
- Chinese Feishu shortcuts should map only to known Brain commands. Unknown plain text can still go to the non-executing chat fallback, but common study workflows now avoid that dependency.
- Testnet strategy execution should be tied to an explicit `testnet_candidate` research decision, not to raw backtest performance alone.
- Testnet order records need context links because the useful learning object is the full chain: experiment, signal, daily plan, checklist, order result, and later review.
- A helper named `_experiment_decision` collided with the existing Brain command handler of the same name; command handlers and read helpers should use distinct names to avoid runtime routing bugs.
- Real-trading readiness can be improved without adding a live order path: dry-run simulation and independent risk checks provide coverage while preserving the default disabled state.
- The default real-trading risk config intentionally fails closed; unset max order size, loss limit, position limit, or cooldown all block the simulated path.
- The daily startup path should assume Windows network authentication happens first; after that, one local script can start Brain, runner, dashboard, and health checks without storing secrets.
- Secret scans over docs can find placeholder assignment examples, so the higher-signal scan for committed source/scripts should distinguish placeholder docs from executable secret-bearing files.

## 2026-05-23

- Indicator correctness should be locked to a repository-owned golden fixture, not TA-Lib or pandas-ta runtime comparisons; this prevents a hidden TA dependency from entering tests.
- Strategy research decisions need four states, not two: `kept`, `rejected`, `inconclusive`, and `risk_reduction_kept`. The fourth state matters when Sharpe is not better but drawdown/volatility materially improves.
- Hypothesis cards are only useful if they include preregistered predicted metrics before the run and actual metrics after the run; actual-only cards destroy the research method.
- The current local BTCUSDT 1h cache is sufficient for a research smoke walk-forward with 7d train / 5d test / 1d purge, but it is too short for production-grade conclusions.
- H-101 currently looks like a risk-control variant, not an alpha improvement: the EMA200 filter reduced exposure/drawdown in the short local sample but did not prove Sharpe improvement.
- H-103 to H-105 need a stronger multi-timeframe walk-forward runner before conclusions are meaningful; the current vectorized runner does not yet simulate synchronized 15m/5m entries or intrabar stop/take-profit exits.
