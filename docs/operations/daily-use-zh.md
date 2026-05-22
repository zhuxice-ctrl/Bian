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
```

## 2. 远程发起本地回测

飞书输入：

```text
远程回测 币种=BTCUSDT 周期=1h 文件=data/local/BTCUSDT-1h.csv 短线=20 长线=60
```

服务器会入队，本地 Quant Runner 拉取后执行。

## 3. AI 教练下一步

```text
/coach-next
```

有 follow-up 实验后：

```text
/coach-evaluate proposal=proposal-id experiment=experiment-id
```

## 4. 策略实验室

保存策略 Profile：

```text
/strategy-profile-set name=ma_baseline symbol=BTCUSDT interval=1h csv=data/local/BTCUSDT-1h.csv short=20 long=60 quote_amount=100
```

参数扫描：

```text
/sweep-ma symbol=BTCUSDT interval=1h csv=data/local/BTCUSDT-1h.csv shorts=10,20 longs=40,60 starting_cash=1000 quote_amount=100
```

## 5. 复盘沉淀

```text
/experiment-review experiment=experiment-id
/experiment-review-commit experiment=experiment-id date=2026-05-22
/daily-report date=2026-05-22
```

## 6. 备份

每天结束后执行：

```powershell
trading-learning backup-db --output-dir backups
```

需要检查系统：

```powershell
trading-learning health-check
```

## 7. 实盘边界

实盘默认禁用：

```text
/real-trading-status
```

任何实盘启用都必须经过单独的本地生产准备门禁。飞书不能绕过。
