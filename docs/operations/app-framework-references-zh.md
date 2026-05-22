# 应用框架参考

Phase 29 没有复制外部项目代码，只吸收成熟量化工具的应用结构思路。

## Freqtrade

参考点：

- REST API 和 Web UI 分离。
- 明确暴露 bot 状态、配置、运行状态、交易和日志。
- 控制面板优先让用户看到系统当前状态。

对 Bian 的落地：

- 增加 `/api/control-console` 聚合本地应用状态。
- dashboard 顶部增加任务队列、runner、Testnet 和门禁状态。
- 所有状态仍然只读，不把交易密钥放入 dashboard。

## Jesse

参考点：

- 策略研究、回测和执行流程分层。
- 研究结果需要进入清晰的实验记录，而不是只停留在命令输出。

对 Bian 的落地：

- AI Coach 提案、策略 Profile、参数扫描各自独立展示。
- 回测报告仍然是本地 dashboard 的主要分析工作区。

## vectorbt

参考点：

- 参数矩阵、批量回测和可视化分析。
- 参数扫描结果必须警惕过拟合。

对 Bian 的落地：

- 参数扫描结果进入 `parameter_sweeps`。
- dashboard 显示 best experiment 和 overfitting warning。

## Bian 自身边界

- Bian 不是普通交易机器人，而是 AI 主导的本地量化学习与执行系统。
- 服务器只做飞书桥接和任务队列。
- 本地电脑持有数据、dashboard、Codex/LLM、Binance testnet 和未来交易权限。
- 实盘交易仍由 production gate 阻断。
