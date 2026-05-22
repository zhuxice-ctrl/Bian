# Daily Use

This is the Chinese-first daily operation checklist for the local-first quant workstation.

## 1. Start After Windows Reboot

After network verification, run:

```powershell
.\scripts\start-local-workstation.ps1
```

The script starts `start-brain.ps1`, starts `start-quant-runner.ps1` when
`TRADING_LEARNING_RUNNER_TOKEN` exists, starts `trading-learning dashboard-serve`,
runs `trading-learning health-check`, and prints:

```text
http://127.0.0.1:8780/
```

## 2. Local And Feishu Checks

Use Brain or Feishu:

```text
检查链接
/llm-status
/task-status limit=5
/workspace-status
/market-status
/coach-daily
```

## 3. Data And Backtests

Refresh public market cache locally:

```powershell
trading-learning refresh-market-data --limit 500
```

Queue local backtest from Feishu:

```text
远程回测 币种=BTCUSDT 周期=1h 文件=data/local/market_data/BTCUSDT/BTCUSDT-1h.csv 短线=20 长线=60
```

Queue public data refresh from Feishu:

```text
远程刷新数据 币种=BTCUSDT 周期=1h 数量=500
```

## 4. Coach And Learning

```text
/coach-daily
/coach-next
/learning-queue
/experiment-review experiment=experiment-id
/experiment-review-commit experiment=experiment-id date=2026-05-23
/daily-report date=2026-05-23
```

## 5. Backup And Recovery

```powershell
trading-learning backup-db --output-dir backups
trading-learning health-check
trading-learning reset-workspace --confirm RESET_LOCAL_WORKSPACE --backup-dir data/backups
```

Restore example:

```powershell
trading-learning restore-db --backup backups\trading_learning-YYYYMMDDTHHMMSSZ.sqlite3 --target data\local\trading_learning.sqlite3
```

## 6. Real Trading Boundary

Real trading remains disabled. Check the gate:

```text
/real-trading-status
/kill-switch-status
```

Dry-run only:

```text
/real-dry-run-buy symbol=BTCUSDT quote=10
```

No Feishu command can bypass local readiness gates or send a real order.
