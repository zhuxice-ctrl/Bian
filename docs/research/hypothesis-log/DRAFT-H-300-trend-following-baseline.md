> ⚠️ **此文档为骨架草稿，未经用户清醒头脑填写 entry gate 与失败定义之前，严禁启动任何回测。**
> 文件名前缀 DRAFT- 为标识；用户审定后将更名为 H-300-trend-following-baseline.md。

# H-300 趋势跟踪基线（DRAFT）

## 背景
- 配对交易方向（H-200~H-207）已 fail，详见相关 ablation 报告
- 用户实操直觉：长期跟趋势是其多年实盘行为之一
- 本卡是分支 A（宏观趋势跟踪）的入口，作为后续 H-301~H-30x 的 baseline

## 研究问题
BTC 在 4h 或 1d 周期上，简单趋势信号是否产生统计显著的正期望收益？

## 候选信号（待用户明日选定唯一一个）
<!-- TODO: 三选一 -->
- 选项 1：MA 交叉（参数待定）
- 选项 2：Donchian 通道突破（参数待定）
- 选项 3：ATR-adjusted momentum（参数待定）

## 数据范围
- Symbol：BTCUSDT
- Interval：<!-- TODO: 4h 或 1d 二选一 -->
- 时间窗口：2024-05-23 ~ 2026-05-23（H-206 已回填）
- 数据条数：<!-- TODO: 4h≈4380 / 1d≈730 -->

## Entry Gate（明日填写）
<!-- TODO: 必须明确以下内容
- 信号触发的具体条件
- 仓位规模规则
- 入场前的过滤条件（如波动率、流动性）
-->

## Exit / 止损规则（明日填写）
<!-- TODO: 必须明确
- 止损阈值
- 止盈或退出信号
- 最大持仓时间
-->

## 失败定义（最重要，明日填写）
<!-- TODO: 必须明确
- 不通过的最低 Sharpe / Calmar / win rate
- 最大回撤上限
- 任何一条不满足即 fail
注意：此节填写后即不可修改，结果出来后只能照填，不能事后调整阈值。
-->

## 评估指标（参考 metrics 库）
计算以下指标（H-206 配套的 `src/trading_learning/metrics/performance.py` 已就绪）：
- Sharpe ratio（年化）
- Sortino ratio
- Calmar ratio
- Max drawdown
- CAGR
- Volatility（年化）
- Win rate
- Profit factor

## 运行计划
1. 用户填写所有 TODO 段落，去除 DRAFT- 前缀
2. 实现信号计算函数（独立模块，与 strategy 解耦）
3. 跑完整 ablation
4. 输出 `exports/ablation-trend-h300-{date}.md`
5. 结果照填，不调整阈值

## 范围声明
本卡为骨架草稿。任何研究契约必须由用户清醒头脑填写后方可执行。
所有 TODO 必须有具体内容，模糊表述（如"较高 Sharpe"）不予接受。
