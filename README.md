# Trading Learning

Local low-frequency crypto trading learning system.

Phase 1 supports:

- SQLite local storage
- Historical CSV loading
- Binance Spot public K-line download
- Moving-average backtests
- Backtest metrics: round trips, win rate, realized PnL, fees
- Daily review and learning records
- Local Codex-compatible draft assistant
- Binance Spot Testnet signed client and test-order CLI
- Execution risk guard for test orders
- Local command brain with confirmation and audit logs
- Brain-driven history download and strategy experiment records
- Review-to-experiment learning loop records
- Daily and weekly learning reports
- Local read-only dashboard and CSV K-line replay
- JSONL and Markdown ZIP export

Phase 1 does not place live orders. The test-order command uses Binance Spot Testnet `/api/v3/order/test`, which validates a signed order request without placing a live order.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Initialize Database

```powershell
trading-learning init-db
```

## Download Binance Klines

This uses Binance Spot public market data through `https://data-api.binance.vision` and does not require an API key.
By default, learning data downloads are limited to `BTCUSDT` and `ETHUSDT`.

```powershell
trading-learning download-klines --symbol BTCUSDT --interval 1h --limit 500 --output data/local/BTCUSDT-1h.csv
```

To refresh the default local data center for BTC/ETH across `1m`, `5m`, `15m`, and `1h`:

```powershell
trading-learning refresh-market-data --limit 500
```

Files are stored under `data/local/market_data/{SYMBOL}/{SYMBOL}-{INTERVAL}.csv` and appear in the dashboard historical data picker.

## Run Backtest

```powershell
trading-learning backtest-ma --csv tests/fixtures/btcusdt_1h_sample.csv --symbol BTCUSDT --short-window 2 --long-window 3
```

The backtest stores simulated trades in SQLite and prints summary metrics.
Backtests use the same default learning scope: `BTCUSDT` and `ETHUSDT`.

## Add Daily Review

```powershell
trading-learning review-add --date 2026-05-20 --symbols BTCUSDT,ETHUSDT --trade-count 2 --plan-followed yes --pnl 12.5 --mistake-tags late_entry --emotion-note "calm" --lesson "wait for planned entries"
```

## Create Local Codex Review Draft

The assistant endpoint is local-only. The client rejects non-loopback hosts.

```powershell
$env:LOCAL_CODEX_BASE_URL="http://127.0.0.1:61771/v1"
$env:LOCAL_CODEX_MODEL="gpt-5.4-mini"
$env:LOCAL_CODEX_API_KEY="your-local-only-key"
trading-learning ai-review-draft --source-external-id review-2026-05-20 --review-text "review body"
```

## Binance Spot Testnet Test Order

API keys stay local. Put them in your local `.env` or shell environment; do not commit them.

```powershell
$env:BINANCE_TESTNET_BASE_URL="https://testnet.binance.vision"
$env:BINANCE_TESTNET_API_KEY="your-testnet-key"
$env:BINANCE_TESTNET_API_SECRET="your-testnet-secret"
trading-learning spot-test-order --symbol BTCUSDT --side BUY --type MARKET --quote-order-qty 10 --orders-today 0 --max-quote-order-qty 20
```

The command applies local risk checks before making the signed request. Defaults:

- Daily order limit: `5`
- Max quote order quantity: `100`
- Allowed symbols: `BTCUSDT,ETHUSDT`

To add another symbol later, extend the local-only scope before running download, backtest, or testnet commands:

```powershell
$env:TRADING_LEARNING_ALLOWED_SYMBOLS="BTCUSDT,ETHUSDT,SOLUSDT"
```

## Local Brain HTTP Service

The local brain is the control layer for chat-style operation. It runs on your machine, writes audit logs to SQLite, and requires confirmation before sending a Binance Spot Testnet test order.

```powershell
$env:BINANCE_TESTNET_BASE_URL="https://testnet.binance.vision"
$env:BINANCE_TESTNET_API_KEY="your-testnet-key"
$env:BINANCE_TESTNET_API_SECRET="your-testnet-secret"
$env:FEISHU_VERIFICATION_TOKEN="your-feishu-verification-token-or-empty"
$env:FEISHU_ENCRYPT_KEY="your-feishu-encrypt-key-or-empty"
$env:FEISHU_USER_MAP="your-feishu-open-id:owner"
$env:FEISHU_APP_ID="your-feishu-app-id"
$env:FEISHU_APP_SECRET="your-feishu-app-secret"
trading-learning brain-serve --host 127.0.0.1 --port 8765 --allowed-user-id owner
```

Send commands to `POST http://127.0.0.1:8765/brain/command`:

```json
{"text":"/status","user_id":"owner"}
```

Or use the local chat helper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/brain-chat.ps1 -Command "/status"
powershell -ExecutionPolicy Bypass -File scripts/brain-chat.ps1
```

Natural-language chat uses the local Codex-compatible API. Configure it once with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/set-local-codex-env.ps1
powershell -ExecutionPolicy Bypass -File scripts/restart-brain.ps1
```

Without `LOCAL_CODEX_API_KEY`, non-command text returns a clear `chat_unavailable` response instead of executing anything.

When natural-language chat suggests a low-risk record command, run it explicitly with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/brain-chat.ps1 -Command "/run suggested"
```

`/run suggested` only executes safe record/planning commands such as `/review-add`, `/lesson`, `/knowledge-add`, `/experiment-link`, `/experiment-review-commit`, `/plan-set`, and `/checklist`. Trading and confirmation commands must be typed manually.

## Local Read-Only Dashboard

The dashboard serves local SQLite summaries and a browser K-line replay from CSV. It binds to loopback by default, opens the existing SQLite database read-only, and does not expose API keys or provide trading actions. Run `trading-learning init-db` before starting it on a fresh machine.

```powershell
trading-learning dashboard-serve --host 127.0.0.1 --port 8780
```

Open `http://127.0.0.1:8780/`. JSON endpoints include `/api/overview`, `/api/reviews`, `/api/experiments`, `/api/knowledge`, `/api/datasets`, `/api/reports?type=daily`, `/api/reports?type=weekly`, and `/api/kline?experiment=EXPERIMENT_ID`.

Supported commands:

- `/status`: health check and mode summary.
- `/plan-set date=2026-05-20 symbols=BTCUSDT,ETHUSDT max_trades=5 bias=neutral conditions=trend_up forbidden=fomo`: stores the daily trading plan.
- `/checklist symbol=BTCUSDT plan=yes setup=yes risk=yes emotion=calm`: stores the pre-trade checklist.
- `/plan-status date=2026-05-20`: returns the plan and checklist records.
- `/test-buy BTCUSDT 10`: creates a pending Spot Testnet test buy request.
- `/testnet-create-buy BTCUSDT 10`: creates a pending real Spot Testnet market buy request.
- `/testnet-cancel symbol=BTCUSDT order_id=123`: creates a pending Spot Testnet cancel request.
- `/testnet-order symbol=BTCUSDT order_id=123`: fetches a Spot Testnet order.
- `确认-CODE`: executes the pending test order once.
- `/confirm CODE`: ASCII confirmation command for terminals or channels that do not handle Chinese input reliably.
- `/review-add date=2026-05-20 symbols=BTCUSDT trades=2 plan=yes pnl=12.5 tags=late_entry lesson=Wait_for_planned_entries note=Calm`: stores a daily review.
- `/review-summary limit=5`: returns recent daily reviews.
- `/lesson title=MA_lag category=technical content=Moving_average_signals_lag_price`: stores a learning card.
- `/knowledge-add title=FOMO_control category=psychology content=Pause_before_entry tags=fomo,discipline`: stores a tagged knowledge card.
- `/knowledge-search query=FOMO limit=5`: searches knowledge cards.
- `/mistake-link review=review-2026-05-20 card=knowledge-id tag=fomo`: links a review mistake to a knowledge card.
- `/experiment-link review=review-2026-05-20 experiment=experiment-id tag=late_entry note=Replay_matches_review`: links a review to a strategy experiment.
- `/review-context review=review-2026-05-20`: returns one review with linked experiments and knowledge cards.
- `/history-download symbol=BTCUSDT interval=1h limit=500 output=data/local/BTCUSDT-1h.csv`: downloads public Binance Spot K-lines to CSV without API keys.
- `/market-refresh limit=500`: refreshes default BTC/ETH `1m,5m,15m,1h` local CSV datasets for the dashboard data center.
- `/backtest-ma csv=data/local/BTCUSDT-1h.csv symbol=BTCUSDT interval=1h short=20 long=60 starting_cash=1000 quote_amount=100 fee=0.001 daily_limit=5 note=MA_replay`: runs a moving-average replay and stores the experiment summary.
- `/experiment-summary limit=5`: returns recent strategy experiment summaries.
- `/experiment-review experiment=experiment-id`: generates and stores a deterministic experiment review draft.
- `/experiment-review-commit experiment=experiment-id date=2026-05-20`: commits an experiment review draft into the learning loop by writing a daily review, knowledge cards, review links, and the daily learning report.
- `/daily-report date=2026-05-20`: stores a daily learning report from plan, checklist, review, experiments, and knowledge links.
- `/weekly-report start=2026-05-18 end=2026-05-24`: stores a weekly learning report with plan-follow rate, PnL, focus tags, and next actions.
- `/learning-next date=2026-05-20`: returns the next learning tasks for one review day without storing a report.
- `/run suggested`: executes the latest safe suggested command generated by natural-language chat.

Chinese aliases and keyword commands are also supported for local chat and Feishu text input:

- `沉淀实验复盘 实验=experiment-id 日期=2026-05-20`

- `状态`
- `设置计划 日期=2026-05-20 币种=BTCUSDT,ETHUSDT 最大交易=5 方向=neutral 条件=trend_up 禁止=fomo`
- `交易前检查 币种=BTCUSDT 计划=是 形态=是 风险=是 情绪=冷静`
- `计划状态 日期=2026-05-20`
- `添加复盘 日期=2026-05-20 币种=BTCUSDT 交易=2 遵守计划=是 盈亏=12.5 标签=late_entry 教训=Wait_for_planned_entries 笔记=Calm`
- `下载历史 币种=BTCUSDT 周期=1h 数量=500 文件=data/local/BTCUSDT-1h.csv`
- `最近复盘`
- `最近实验`
- `今天学什么`
- `执行建议`
- `测试网买入 BTCUSDT 10U`
- `确认 123456`

Chinese trading aliases still use the same plan, checklist, and confirmation guards. Fuzzy text such as `帮我买 BTC` is not treated as an execution command.

History and replay commands are research tools only. They use public market data or local CSV files, persist simulated trades and experiment metrics, and do not place Spot Testnet or live orders. Brain file paths for history download and replay are intentionally limited to `data/local`.

The service is local-first. It can start without Binance keys so you can test chat, history download, replay, audit logging, and confirmation flow locally. Actual Spot Testnet order validation still requires `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_API_SECRET` in the local environment. A Feishu bridge can call this endpoint later, but the Binance keys should remain only in the local environment.

After setting Binance Testnet keys in the Windows user environment, restart the local service so it reads the new variables:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restart-brain.ps1
```

### Feishu Event Bridge

The same local service also exposes `POST http://127.0.0.1:8765/feishu/events` for Feishu event callbacks. It supports:

- URL verification challenge.
- `im.message.receive_v1` text messages.
- Optional verification token checks when Feishu provides a token.
- Optional `X-Lark-Signature` verification when `FEISHU_ENCRYPT_KEY` is set.
- Open ID to local user mapping through `FEISHU_USER_MAP`.
- Optional Feishu bot replies when `FEISHU_APP_ID` and `FEISHU_APP_SECRET` are set.

Configure local Feishu values once with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/set-feishu-env.ps1
powershell -ExecutionPolicy Bypass -File scripts/restart-brain.ps1
```

For remote phone access, put a tunnel or reverse proxy in front of this local endpoint and point Feishu event subscription to that public HTTPS URL. In the Feishu developer console:

- Set the event subscription Request URL to `https://YOUR_PUBLIC_HOST/feishu/events`.
- Use the same Verification Token and Encrypt Key that you stored locally if Feishu shows those fields; otherwise leave them empty locally.
- Subscribe to message receive events for text messages.
- Grant the bot permission to send messages, then publish or install the app to your tenant.

Official Feishu references:

- Event subscription Request URL configuration: `https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-configure-/request-url-configuration-case`
- Send message API: `https://open.feishu.cn/document/server-docs/im-v1/message/create`

Keep Binance keys and Feishu secrets in local environment variables only.

Before connecting the real Feishu app, run the local callback smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/feishu-event-smoke.ps1
```

### Keep The Brain Running On Windows

For a long-running local setup, install a current-user Startup shortcut. It starts the brain service when you log in, reads credentials from your Windows user environment variables, and does not store keys in the repository.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-brain-startup-shortcut.ps1
```

The shortcut is `TradingLearningBrain.lnk`. It writes logs to:

- `logs/brain-service.log`
- `logs/brain-service.err.log`

To remove the Startup shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/uninstall-brain-startup-shortcut.ps1
```

If you prefer Task Scheduler and your Windows user has permission to register tasks, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register-brain-task.ps1
```

To remove the scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/unregister-brain-task.ps1
```

## Export Data

```powershell
trading-learning export --output exports/trading-learning-export.zip
```
