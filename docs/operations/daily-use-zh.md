# 日常使用

系统角色：

- 助手：大脑、教练、研究员。
- 本地程序：手脚、执行器、审计员。
- 服务器：飞书桥接和任务队列。
- 飞书：手机端轻量入口。
- 用户：学生和最终风险确认人。

## 1. 开机后检查

飞书或本地 Brain 输入：

```text
检查链接
```

也可以输入：

```text
/llm-status
/task-status limit=5
/workspace-status
/market-status
/coach-daily
```

## 2. 本地 dashboard

启动后打开：

```text
http://127.0.0.1:8780/
```

dashboard 现在包含：

- 控制台：健康、任务、AI Coach、策略、Testnet、安全门禁。
- 行情：本地缓存 CSV 清单，包含缺失状态。
- 回测：从本地 `data/local` CSV 运行 MA 回测。
- 复盘：保存实验复盘草稿，并沉淀到学习记录。
- 知识库：查看沉淀后的知识卡。
- 安全：实盘禁用和 kill switch 状态。

## 3. 刷新真实行情缓存

```powershell
trading-learning refresh-market-data --limit 500
```

默认范围是：

```text
BTCUSDT, ETHUSDT
1m, 5m, 15m, 1h, 4h, 1d
```

查看缓存状态：

```text
/market-status
```

## 4. 本地回测

可以在 dashboard 回测表单里运行，也可以用命令：

```powershell
trading-learning backtest-ma --csv data/local/market_data/BTCUSDT/BTCUSDT-1h.csv --symbol BTCUSDT --short-window 20 --long-window 60
```

飞书远程发起本地回测：

```text
远程回测 币种=BTCUSDT 周期=1h 文件=data/local/market_data/BTCUSDT/BTCUSDT-1h.csv 短线=20 长线=60
```

服务器会入队，本地 Quant Runner 拉取后执行。

## 5. AI 教练

每日建议：

```text
/coach-daily
```

生成下一步实验：

```text
/coach-next
```

完成 follow-up 实验后评价：

```text
/coach-evaluate proposal=proposal-id experiment=experiment-id
```

## 6. 策略实验室

保存策略 Profile：

```text
/strategy-profile-set name=ma_baseline symbol=BTCUSDT interval=1h csv=data/local/market_data/BTCUSDT/BTCUSDT-1h.csv short=20 long=60 quote_amount=100
```

参数扫描：

```text
/sweep-ma symbol=BTCUSDT interval=1h csv=data/local/market_data/BTCUSDT/BTCUSDT-1h.csv shorts=10,20 longs=40,60 starting_cash=1000 quote_amount=100
```

## 7. 复盘沉淀

```text
/experiment-review experiment=experiment-id
/experiment-review-commit experiment=experiment-id date=2026-05-22
/daily-report date=2026-05-22
```

dashboard 也可以直接保存复盘草稿、沉淀到学习记录。

## 8. 备份与重置

每天结束后备份：

```powershell
trading-learning backup-db --output-dir backups
```

检查系统：

```powershell
trading-learning health-check
```

清空本地学习/回测记录时，程序会先备份 SQLite：

```powershell
trading-learning reset-workspace --confirm RESET_LOCAL_WORKSPACE --backup-dir data/backups
```

这个命令不清除环境变量、API key、飞书密钥，也不删除行情 CSV 缓存。

## 9. 实盘边界

实盘默认禁用：

```text
/real-trading-status
/kill-switch-status
```

任何实盘启用都必须经过单独的本地生产准备门禁。飞书不能绕过。
