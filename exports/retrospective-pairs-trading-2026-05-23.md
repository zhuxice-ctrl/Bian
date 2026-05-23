# 配对交易研究线（H-200~H-207）回顾

## 时间线
- C2 分支：配对交易模块代码完成
- H-200~H-205 立卡：BTC/ETH 基线 + 4 个 ablation + 3 个 pair 扩展
- 首次 ablation：全部 deferred，因数据不足（1000 根，约 41 天）
- H-206 工具：补齐 BTC/ETH/BNB/SOL 1h 数据至 17520 根（2 年）
- 二次 ablation：BTC/ETH 配对 fail，p=0.5（4 桶兜底）
- H-207 工具：ADF p-value 从 4 桶分类升级为连续值
- 三次 ablation：全部 4 对 pair fail，连续 p=0.65~0.77

## 最终结论
BTC/ETH/BNB/SOL 在 2024-05~2026-05 这两年中两两不构成可交易的协整配对。
结论由连续 p-value 与 half-life 两个独立指标互证。

## 研究纪律层面的关键决定（按时间序）
1. 数据不足时全部标 deferred，不降低门槛硬上
2. 旧 ablation 报告保留为历史证据，新报告独立文件名追加
3. H-206 / H-207 标签 = methodology correction / tooling，不与 hypothesis 混合
4. H-207 工具升级后即使结果有变也不得改写 H-200 卡正文
5. 三份 ablation 报告 + 三段 H-200 卡历史 = 完整研究审计链

## 学到了什么
1. fail 是合法且高价值的研究结论，前提是它来自 honest 流程
2. 工具精度伪装（4 桶 p-value 写成 0.5000）是隐性陷阱
3. 工具改进和研究结论必须走独立证据链
4. 多 pair 同方向同时 fail 暗示市场结构问题，不是 pair 选择问题

## 范围声明
本文档为研究过程回顾，不构成任何执行契约或新假设。
