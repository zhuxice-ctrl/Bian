# H-300 趋势跟踪基线

## 背景
- 配对交易方向（H-200~H-207）已 fail，详见相关 ablation 报告
- 用户实操直觉：长期跟趋势是其多年实盘行为之一
- 本卡是分支 A（宏观趋势跟踪）的入口，作为后续 H-301~H-30x 的 baseline

## 研究问题
BTC 这两年的价格序列里，是否存在足够稳健的趋势持续性，
使得 Donchian 参数族（N=20/40/60）在统计上都能探测到正期望？

## 信号设计
**Donchian 通道突破，参数族 N=20 / N=40 / N=60**

入场：
- 收盘价突破过去 N 天最高价 → 做多
- 收盘价跌破过去 N 天最低价 → 做空

参数族稳健性原则：
- 三个 N 独立运行，互不交叉
- 不挑选"表现最好的 N"——所有结论必须对参数族成立才有效
- 不在事后调整 N 取值

## 数据范围
- Symbol：BTCUSDT
- Interval：1d
- 时间窗口：2024-05-23 ~ 2026-05-23（H-206 已回填）
- 数据条数：730

## Entry Gate

### 信号触发条件
- N=20：突破过去 20 天最高 → 做多；跌破过去 20 天最低 → 做空
- N=40：突破过去 40 天最高 → 做多；跌破过去 40 天最低 → 做空
- N=60：突破过去 60 天最高 → 做多；跌破过去 60 天最低 → 做空

### 仓位规模规则
- 每次交易固定 1 单位资金
- **不开杠杆**
- **不复利**（每次交易资金独立）
- 总资金的 1%-2% 分配给本策略（生产侧约束）

### 入场前过滤条件
- 无（baseline 不加过滤）
- 注：波动率、成交量、市场状态等过滤是 H-301+ 的 ablation 维度

## Exit / 止损规则

### 退出信号
- 持多时：收盘价跌破过去 N/2 天最低 → 平仓
  - N=20 → 10 天反向通道
  - N=40 → 20 天反向通道
  - N=60 → 30 天反向通道
- 持空时：收盘价突破过去 N/2 天最高 → 平仓

### 止损规则
- 不设独立 ATR 止损（仅依靠反向通道退出）
- 理由：保持信号单一性，避免引入第二个参数源

### 最大持仓时间
- 无限制（趋势策略不应设时间止损）

## 失败定义（**填写后此节不可修改**）

**Pass 条件——三个 N 必须同时满足**：

| 指标 | 阈值 |
|---|---|
| 年化 Sharpe ratio | ≥ 0.3 |
| Max drawdown | ≤ 60% |
| 总交易次数 | ≥ 10 |
| Profit factor | ≥ 1.2 |

**任何一个 N 不满足任何一条 → 整张 H-300 卡 fail**。

结果出来后只能照填，不能事后调整阈值。

## 评估指标（参考 metrics 库）
计算以下指标（H-206 配套 [src/trading_learning/metrics/performance.py](cci:7://file:///F:/Bian/src/trading_learning/metrics/performance.py:0:0-0:0) 已就绪）：
- Sharpe ratio（年化）
- Sortino ratio
- Calmar ratio
- Max drawdown
- CAGR
- Volatility（年化）
- Win rate
- Profit factor

**对照基准**：同期 BTC buy-and-hold 所有指标必须并列展示，
便于判断策略 alpha vs beta（**展示但不作为 pass/fail 标准**）。

## 运行计划
1. 实现 Donchian 信号计算函数（独立模块，与 strategy 解耦）
2. 跑完整 ablation：三个 N 各跑一次
3. 输出 `exports/ablation-trend-h300-{date}.md`，包含：
   - 三个 N 的完整 metrics
   - BTC buy-and-hold 同期 metrics
   - Pass/Fail 判定
4. 结果照填，不调整阈值

## 范围声明
- 本卡仅测 BTCUSDT 1d 周期 Donchian 信号
- 不涉及 ETH/BNB/SOL（如果想测，独立立 H-310/H-320/H-330）
- 不涉及 4h/1h 周期（如果想测，独立立 H-310 系列）
- 不涉及任何过滤条件（如果想加，独立立 H-301+ 系列做 ablation）
