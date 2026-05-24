# H-209 加密标的维度独立性测量

## 性质
本卡是 methodology measurement，不是 alpha hypothesis。

目的不是判断某个交易信号是否有效，而是先量化加密标的之间的相关性和有效投注数，
为后续趋势、配对、横截面或多标的组合研究提供基础约束。

## 背景
- Carver 框架强调：真正的分散来自独立收益来源，而不是名义标的数量
- 加密市场内部标的相关性可能很高，单纯扩展 BTC / ETH / BNB / SOL 不一定提供有效维度分散
- 在继续设计信号前，需要先测量当前本地数据下的标的独立性

## 研究问题
BTCUSDT / ETHUSDT / BNBUSDT / SOLUSDT 在最近两年 1d 收益序列中，实际提供多少有效独立投注数？

## 标的与数据
- Symbol：BTCUSDT / ETHUSDT / BNBUSDT / SOLUSDT
- Interval：1d
- 时间窗口：最近 2 年，以本地已回填 CSV 的共同日期交集为准
- 数据来源：`data/local/market_data/`
- 数据文件：优先读取 `data/local/market_data/{symbol}/1d/{symbol}-1d.csv`
- 不下载新数据

## 测量内容

### 1. Pearson 相关矩阵
使用各标的日收益率计算 4×4 Pearson correlation matrix。

### 2. Spearman 相关矩阵
使用各标的日收益率计算 4×4 Spearman correlation matrix。

### 3. Effective N of Bets
使用相关矩阵和等权权重计算有效投注数：

`N_eff = (Σwᵢ)² / (w'Σw)`

其中：
- `Σ` 为相关矩阵
- `w` 为等权权重，BTC / ETH / BNB / SOL 各 0.25
- 若四个标的完全独立，`N_eff` 接近 4
- 若四个标的完全相关，`N_eff` 接近 1

### 4. 滚动 90 天相关性
仅计算 BTCUSDT vs 其他三个标的的 rolling 90d correlation：
- BTCUSDT vs ETHUSDT
- BTCUSDT vs BNBUSDT
- BTCUSDT vs SOLUSDT

## 通过 / 失败标准
不设置 pass/fail。

本卡只做测量，不做假设判定，不根据结果调整阈值。

## 输出
生成报告：

`exports/ablation-h209-correlation-N_eff-<date>.md`

报告必须包含：
- 数据窗口与共同样本数量
- Pearson 相关矩阵
- Spearman 相关矩阵
- 等权 `N_eff` 具体数值
- BTC vs ETH / BNB / SOL 的 rolling 90d correlation 摘要
- 对 `N_eff` 的基础文字解读

## 范围声明
- 不修改 H-200~H-300 已有卡片或报告
- 不修改 cointegration / strategy / signal 代码
- 不修改数据回填或 catalog 逻辑
- 不下载新数据
- 不设计 alpha，不优化参数，不提出交易结论
