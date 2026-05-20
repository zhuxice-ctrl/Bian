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

```powershell
trading-learning download-klines --symbol BTCUSDT --interval 1h --limit 500 --output data/local/BTCUSDT-1h.csv
```

## Run Backtest

```powershell
trading-learning backtest-ma --csv tests/fixtures/btcusdt_1h_sample.csv --symbol BTCUSDT --short-window 2 --long-window 3
```

The backtest stores simulated trades in SQLite and prints summary metrics.

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

## Local Brain HTTP Service

The local brain is the control layer for chat-style operation. It runs on your machine, writes audit logs to SQLite, and requires confirmation before sending a Binance Spot Testnet test order.

```powershell
$env:BINANCE_TESTNET_BASE_URL="https://testnet.binance.vision"
$env:BINANCE_TESTNET_API_KEY="your-testnet-key"
$env:BINANCE_TESTNET_API_SECRET="your-testnet-secret"
$env:FEISHU_VERIFICATION_TOKEN="your-feishu-verification-token"
$env:FEISHU_ENCRYPT_KEY="your-feishu-encrypt-key"
$env:FEISHU_USER_MAP="your-feishu-open-id:owner"
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

The service is local-first. It can start without Binance keys so you can test chat, audit logging, and confirmation flow locally. Actual Spot Testnet order validation still requires `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_API_SECRET` in the local environment. A Feishu bridge can call this endpoint later, but the Binance keys should remain only in the local environment.

After setting Binance Testnet keys in the Windows user environment, restart the local service so it reads the new variables:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restart-brain.ps1
```

### Feishu Event Bridge

The same local service also exposes `POST http://127.0.0.1:8765/feishu/events` for Feishu event callbacks. It supports:

- URL verification challenge.
- `im.message.receive_v1` text messages.
- Verification token checks.
- Optional `X-Lark-Signature` verification when `FEISHU_ENCRYPT_KEY` is set.
- Open ID to local user mapping through `FEISHU_USER_MAP`.

For remote phone access, put a tunnel or reverse proxy in front of this local endpoint and point Feishu event subscription to that public HTTPS URL. Keep Binance keys and Feishu secrets in local environment variables only.

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
