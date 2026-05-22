# Phase 39 Local Quant Workstation UI Spec

## Goal

Build the next dashboard generation as a local-first quant workstation, not a single crowded dashboard page. The product should combine:

- TradingView-style chart testing for local market data.
- Quant research lab workflows for strategies, parameters, experiments, and comparisons.
- AI Coach teaching and review guidance beside the user's work.

The app remains local-first. Binance keys, local Codex/LLM access, backtests, data, and any future execution stay on the Windows machine. Feishu remains a lightweight remote command and notification interface.

## Product Principles

- Do not cram all features into one page.
- Use a persistent shell with navigation and route-like subpages.
- Keep the chart area professional and powered by the existing local Lightweight Charts integration.
- Show empty and missing-data states honestly; do not add fake sample data.
- Separate research, learning, testnet, and safety workflows.
- Keep real trading disabled and visibly gated.
- Use Chinese-first command labels and workflow text.

## Application Shell

The app uses a stable workstation shell:

- Left navigation rail: main product areas.
- Top status bar: Brain, local data, LLM, runner, server bridge, kill-switch, and real-trading gate.
- Main workspace: one focused page at a time.
- Optional right AI Coach panel: context-aware, collapsible, and page-specific.

The right AI panel should not force every page into a cramped three-column layout. It is open by default on learning-heavy pages and collapsible on chart-heavy pages.

## Navigation

Primary navigation:

- Today: daily work queue, current system status, next recommended action.
- Chart Lab: TradingView-style local K-line testing and technical analysis.
- Data Center: market datasets, freshness, refresh, gaps, and imports.
- Strategy Lab: strategy profiles, parameters, sweeps, and research queue.
- Backtests: run backtests and inspect single-experiment reports.
- Experiments: compare experiments and make continue/reject/promote decisions.
- Review: experiment review drafts, loss-trade review, daily/weekly reports.
- Knowledge: generated lessons, mistake patterns, and learning cards.
- Testnet: testnet account/status/order lifecycle only.
- Safety: kill-switch, production gate, readiness checklist, limits.
- Settings: local paths, allowed symbols, provider status, server/Feishu connection status.

This can be implemented as hash routes or route-like tabs within the existing vanilla dashboard before considering a framework migration.

## Page Specs

### Today

Purpose: answer "what should I do today?"

Content:

- AI Coach daily plan.
- Data readiness summary.
- Pending review queue.
- Last experiments and unresolved risk flags.
- Safe next actions: refresh data, open Chart Lab, run a research backtest, review an experiment.

No chart needs to dominate this page.

### Chart Lab

Purpose: local TradingView-style analysis and manual strategy testing.

Content:

- Large Lightweight Charts K-line area using real local data.
- Symbol and interval switcher: BTCUSDT, ETHUSDT, later ETF/stock providers.
- Overlay toggles: MA lines, volume, strategy signals, trade markers, support/resistance, trend lines, risk zones.
- Time range controls and quick zoom presets.
- Side drawer for chart settings, active dataset, selected candle, selected trade, and current strategy context.
- AI Coach can be open or collapsed. When open, it teaches technical analysis from the visible context.

Important behavior:

- K-lines must never be hand-drawn placeholder bars in the real app.
- Missing data should show a refresh/import prompt instead of an empty chart.
- Chart interactions should not trigger trading.

### Data Center

Purpose: manage real local datasets.

Content:

- Dataset inventory table with symbol, interval, row count, first/last candle, freshness, source, gaps, and status.
- Actions for public crypto refresh and future ETF/manual import.
- Gap detection and repair prompts after Phase 41.
- Provider status without exposing credentials.

### Strategy Lab

Purpose: define and test strategy ideas.

Content:

- Strategy profile list.
- Strategy family selector: MA first, later breakout, mean reversion, volatility filter, grid research mode.
- Parameter editor with validation.
- Research-only warning.
- Queue button for parameter sweeps and candidate experiments.

### Backtests

Purpose: run and inspect focused backtests.

Content:

- Backtest form with symbol, interval, date range, strategy, parameters, fee/slippage assumptions.
- Result report with metrics, equity curve, drawdown, trade list, and chart jump-to-trade.
- Review draft action after a completed run.

### Experiments

Purpose: compare and decide.

Content:

- Experiment table with metrics, risk flags, strategy family, parameters, date range, and validation status.
- Comparison groups.
- Decisions: reject, needs more data, continue research, testnet candidate.
- AI Coach explanation of the next research priority.

### Review

Purpose: turn test results into learning.

Content:

- Pending experiment review queue.
- Generated review draft.
- Focus trades, especially large losses.
- Review questions and learning tasks.
- Commit-to-learning action that writes daily review, knowledge cards, links, and reports.

### Knowledge

Purpose: durable lessons.

Content:

- Knowledge cards.
- Mistake-pattern tags.
- Search/filter by strategy, market state, error type, and review date.
- Later spaced-review queue.

### Testnet

Purpose: guarded Binance Spot Testnet operations only.

Content:

- Sanitized account status.
- Testnet order lifecycle records.
- Plan/checklist/confirmation state.
- Links back to strategy experiment and review records.

### Safety

Purpose: make risk boundaries explicit.

Content:

- Kill-switch status.
- Real-trading disabled status.
- Missing readiness gates.
- Read-only planned risk limit rows until Phase 48 implements them.
- Audit summaries.

No real-trading activation UI is included in Phase 40.

### Settings

Purpose: local product configuration.

Content:

- Local data paths and database status.
- Allowed symbols.
- LLM/mock status.
- Runner/server bridge status.
- Feishu status.
- Backup/restore links.

No secrets are printed.

## AI Coach Behavior

The AI Coach is page-aware:

- Today: tells the user what to do next.
- Chart Lab: teaches technical analysis from visible chart state and selected overlays.
- Backtests: explains metrics, drawdown, trades, and possible overfitting.
- Experiments: compares strategies and recommends next research tasks.
- Review: asks review questions and turns mistakes into knowledge.
- Safety/Testnet: explains gates and refuses unsafe execution.

The Coach can suggest commands and local actions, but it cannot bypass existing guards. Trading commands still require the established plan, checklist, confirmation, and safety gates.

## Data Flow

- Dashboard reads from local Brain/dashboard APIs.
- Chart Lab reads local CSV/cache through existing dataset APIs.
- Backtest actions use existing local action endpoints.
- Review commit actions use deterministic local learning-loop logic.
- Feishu remote tasks remain queue-based through the server bridge.
- Future real trading is not part of this UI spec.

## Visual Direction

Use a professional research terminal style:

- Dark chart workspace for focus.
- Restrained status colors: green for healthy, amber for warnings, red only for real risk.
- Dense but readable tables.
- Compact controls.
- No marketing landing page.
- No oversized decorative hero section.
- No fake chart placeholders in production UI.

The visual reference direction is B + C + D:

- B: TradingView-like chart interaction.
- C: Quant research lab structure.
- D: AI teaching and review panel.

## Implementation Boundaries

Phase 40 should focus on shell and page structure first:

- Route-like navigation.
- Real chart page with existing Lightweight Charts.
- Page-specific panels and empty states.
- AI Coach panel placement and collapse behavior.

Phase 40 should not implement the full Phase 41-50 feature set. Later phases add deeper data refresh, additional strategies, validation, experiment portfolio, Feishu polish, testnet execution loop, and real-trading readiness gates.

## Testing Expectations

- Static JavaScript syntax check.
- Unit/API tests for any payload shape changes.
- Browser smoke tests for desktop and mobile.
- Chart page smoke test using real cached data when available and missing-data state when not.
- No secret exposure in UI payloads or logs.
