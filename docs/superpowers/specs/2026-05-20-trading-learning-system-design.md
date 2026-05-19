# Trading Learning System Design

Date: 2026-05-20

## Purpose

Build a low-frequency crypto trading system that can eventually run Binance Spot live trading, while also helping the user learn trading systematically and preserve review history.

The first product goal is not maximum profit. The first goal is a controlled, auditable loop:

```text
Knowledge -> Strategy hypothesis -> Backtest -> Paper trading -> Spot testnet -> Small live spot -> Review -> Knowledge update
```

The system must separate three roles:

```text
Trading core: data, rules, backtests, risk controls, execution, logs
Learning coach: knowledge base, study direction, concept explanation, review prompts
Digital twin: emotional record and long-term memory
```

The trading core may use structured strategy rules. It must not use emotional text or free-form large-model output as direct buy/sell input.

## Product Scope

### Phase 1: Backtest And Review

Phase 1 runs without Binance API keys.

It includes:

- Historical K-line import or download.
- Strategy rule definition.
- Backtest engine.
- Trade simulation logs.
- Daily review records.
- Learning knowledge base.
- Strategy hypothesis records.
- Exportable data package.

### Phase 2: Binance Spot Testnet

Phase 2 connects to Binance Spot Testnet.

It includes:

- Testnet account balance read.
- Testnet order placement.
- Testnet cancel and status polling.
- Execution logs.
- Risk checks before every order.
- Paper mode and testnet mode sharing the same strategy and risk interfaces.

### Phase 3: Small Live Spot

Phase 3 enables Binance Spot live trading only after testnet workflows are stable.

It includes:

- API keys loaded from local environment variables only.
- Withdrawal permission disabled.
- Optional IP allowlist.
- Daily order count limit.
- Daily loss limit.
- Consecutive loss pause.
- Manual kill switch.
- Live execution report.

### Out Of Scope For Early Phases

- Futures trading.
- Leverage.
- Automatic strategy parameter changes.
- AI-generated direct trade signals.
- Emotion-driven trading decisions.
- Multi-user public platform hosting.

Futures can be added later only after the spot loop is stable and reviewed.

## Core Trading Rules

The first version uses low-frequency intraday constraints:

- Target trade count: 2 to 3 trades per day.
- Hard trade count limit: 5 trades per day.
- Market: Binance Spot first.
- Instruments: start with 1 to 3 liquid pairs, such as BTCUSDT, ETHUSDT, and SOLUSDT.
- Holding style: intraday preferred; overnight exposure must be explicit in the strategy rule.
- Position sizing: fixed quote amount or fixed account percentage.
- Every order must pass risk checks before execution.

The system can execute rules, but it cannot modify rules automatically.

Every strategy change must create a new strategy version with:

- Change reason.
- Changed parameters.
- Expected effect.
- Backtest result.
- Reviewer note.

## Architecture

```text
app/
  interfaces/
    cli or local UI
  market_data/
    historical data adapter
    Binance market adapter
  strategy/
    strategy definitions
    signal generation
    strategy versioning
  backtest/
    portfolio simulator
    fee and slippage model
    metrics
  execution/
    paper broker
    Binance Spot testnet broker
    Binance Spot live broker
  risk/
    order count limit
    position limit
    stop loss and take profit checks
    daily loss limit
    kill switch
  journal/
    trade journal
    daily review
    mistake tags
    emotion notes
  learning/
    knowledge cards
    study plan
    strategy hypotheses
    review questions
  export_import/
    JSONL export
    ZIP package export
    import validation
  storage/
    SQLite repositories
```

## Data Flow

### Backtest Flow

```text
Historical K-line data
-> Strategy signal generation
-> Risk filter
-> Simulated fills
-> Trade log
-> Metrics
-> Review prompt
```

### Paper Or Testnet Flow

```text
Live market data
-> Strategy signal generation
-> Risk filter
-> Broker adapter
-> Order status
-> Execution log
-> Daily review
```

### Learning Flow

```text
Manual note or imported material
-> Knowledge card
-> Strategy hypothesis
-> Backtestable rule
-> Result comparison
-> Retain, revise, or discard hypothesis
```

## Large Model Boundaries

Large models may do:

- Explain trading concepts.
- Summarize user notes.
- Turn a trading idea into a testable hypothesis.
- Ask review questions.
- Summarize mistake patterns.
- Help create a study plan.

Large models must not do:

- Directly place orders.
- Directly generate buy/sell commands for execution.
- Change strategy parameters automatically.
- Use emotional journal content as strategy input.
- Override risk rules.

If an AI suggestion affects a strategy, it must become a strategy hypothesis first. It must then pass the normal validation path:

```text
Suggestion -> Hypothesis -> Rule -> Backtest -> Paper/Testnet -> Human approval -> Live
```

## Digital Twin Boundaries

The digital twin is allowed to:

- Store emotional notes.
- Store personal review history.
- Summarize the user's emotional patterns.
- Help the user express frustration, regret, fear, or excitement.

The digital twin is not allowed to:

- Interpret market direction.
- Produce trade signals.
- Modify strategy parameters.
- Trigger execution.
- Feed raw emotional text into the trading core.

Emotional data is private, high-sensitivity data. It must be exportable separately and encryptable later.

## Review System

The first review system is hybrid:

- Structured fields for analysis.
- Free-form text for emotion and reflection.

Required daily fields:

- Date.
- Symbols watched.
- Trades taken.
- Trade count.
- Whether daily trade limit was respected.
- Whether plan was followed.
- Profit or loss.
- Main mistake tags.
- Main lesson.

Required trade fields:

- Symbol.
- Direction.
- Entry time.
- Exit time.
- Entry reason.
- Exit reason.
- Planned risk.
- Actual result.
- Rule followed: yes or no.
- Mistake tags.
- Emotion before entry.
- Emotion after exit.

Free-form fields:

- What I felt.
- What I hesitated about.
- What I regret.
- What I would do differently next time.
- Notes for the digital twin.

## Knowledge Base

The learning knowledge base stores manual learning records, not automatic trading instructions.

Core record types:

- Concept card.
- Technical analysis note.
- Risk management note.
- Trading psychology note.
- Strategy hypothesis.
- Backtest observation.
- Review insight.

Example hypothesis:

```text
H001:
If a 15-minute BTCUSDT candle closes above the previous 20-candle high,
and volume is at least 1.5 times the previous 20-candle average,
then short-term upside continuation may be more likely.
```

This hypothesis is not tradable until it becomes a rule and passes backtesting.

## Storage And Portability

Phase 1 should use SQLite as the source of truth.

Human-readable exports should be generated as Markdown. Portable machine exports should use JSONL inside a ZIP package.

Recommended export structure:

```text
trading-learning-export.zip
  manifest.json
  schema.json
  journals.jsonl
  trades.jsonl
  strategies.jsonl
  hypotheses.jsonl
  knowledge_cards.jsonl
  emotion_logs.jsonl
  tags.json
  markdown/
  checksums.json
```

Records should include:

- `external_id`
- `created_at`
- `updated_at`
- `schema_version`
- `source_system`
- `deleted_at`

The public platform version should ship code and empty schemas only. Personal data must remain private tenant data.

## Risk Controls

Minimum required controls:

- Daily trade count hard limit.
- Daily loss hard limit.
- Consecutive loss pause.
- Max position size.
- Max symbol exposure.
- Stop loss requirement.
- Kill switch.
- Mode guard: backtest, paper, testnet, or live.
- Live mode confirmation.

No order can bypass risk controls.

## Testing Strategy

Phase 1 tests:

- Strategy signal tests.
- Backtest determinism tests.
- Fee and slippage calculation tests.
- Daily trade count limit tests.
- Export/import round-trip tests.
- Journal record validation tests.

Phase 2 tests:

- Binance Spot Testnet broker adapter tests.
- Order status handling tests.
- API error handling tests.
- Retry and timeout behavior.
- Risk rejection before broker calls.

Phase 3 tests:

- Live mode cannot run without explicit configuration.
- API secrets never appear in logs.
- Kill switch blocks execution.
- Daily limits remain enforced after restart.

## Milestones

### Milestone 1: Local Backtest Loop

Deliver:

- Local project scaffold.
- SQLite schema.
- Historical data loader.
- One simple baseline strategy.
- Backtest report.
- Trade journal records.

### Milestone 2: Learning And Review Loop

Deliver:

- Knowledge card records.
- Strategy hypothesis records.
- Daily review template.
- Mistake tags.
- Markdown export.
- JSONL export package.

### Milestone 3: Paper Trading

Deliver:

- Live market data read.
- Paper broker.
- Same risk layer as future execution.
- Daily report.

### Milestone 4: Binance Spot Testnet

Deliver:

- Binance testnet adapter.
- Testnet orders.
- Testnet execution logs.
- Broker failure handling.

### Milestone 5: Small Live Spot

Deliver:

- Live broker adapter.
- Strict environment config.
- Small-size live execution.
- Post-trade review workflow.

## Default Implementation Choices

The first implementation should use conservative defaults so development can start without leaving core behavior ambiguous.

- Baseline strategy: moving average crossover.
- Symbols: BTCUSDT and ETHUSDT.
- Timeframe: 1h for the first backtest, with 15m added after the loop is stable.
- Position sizing: fixed USDT amount.
- Interface: CLI first, local web UI later.
- Storage: SQLite first, with Markdown and JSONL ZIP exports.

These defaults can be changed during user review before implementation planning begins.
