# 本地 Windows 设置

目标：本地电脑负责量化核心，服务器和飞书只负责入口与队列。

## 1. 安装与初始化

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
trading-learning init-db
```

## 2. 启动本地 Brain

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-brain.ps1
```

需要长期运行时，用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-brain-startup-shortcut.ps1
```

## 3. 启动本地 dashboard

```powershell
trading-learning dashboard-serve --host 127.0.0.1 --port 8780
```

打开 `http://127.0.0.1:8780/`。

## 4. 启动本地 Quant Runner

先设置本地 runner token。该值必须和服务器一致，不要写进仓库。

```powershell
[Environment]::SetEnvironmentVariable("TRADING_LEARNING_RUNNER_TOKEN", "use-a-random-local-secret", "User")
powershell -ExecutionPolicy Bypass -File scripts/start-quant-runner.ps1 -ServerUrl "https://dl.zeroxcore.tech" -RunnerId "local-windows-pc"
```

Runner 第一版只执行白名单任务：本地状态和 MA 回测。

## 5. 连接本地 Codex/LLM 到服务器

本地 Codex API 只允许 loopback。电脑上线后执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/connect-server-llm.ps1
```

默认映射：服务器 `127.0.0.1:61771` -> 本地 `127.0.0.1:61771`。

## 6. 本地健康检查与备份

```powershell
trading-learning health-check
trading-learning backup-db --output-dir backups
```

恢复到指定文件：

```powershell
trading-learning restore-db --backup backups\trading_learning-YYYYMMDDTHHMMSSZ.sqlite3 --target data\local\trading_learning.sqlite3
```
