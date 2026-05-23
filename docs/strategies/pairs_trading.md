# 配对交易策略

## 目标
配对交易模块实现 C2 均值回归研究分支。它用 Engle-Granger 两步法检验协整，用 log spread 构造 z-score 信号，并在 walk-forward 训练窗口中决定测试窗口是否启用。

## 模块
- `cointegration.py`: ADF 平稳性检验和 Engle-Granger 协整检验。
- `spread.py`: `log(A) - alpha - beta * log(B)` spread 与滚动 z-score。
- `half_life.py`: OU 半衰期估计，单位是 bar 数。
- `hedge_ratio.py`: 静态 OLS beta 和无 lookahead 的滚动 beta。
- `strategy.py`: `PairsTradingConfig`、`PairsSignal`、`PairsTradingStrategy` 和 walk-forward factory。

## 信号规则
- `z <= -entry_threshold`: long spread，买 A、卖 B。
- `z >= entry_threshold`: short spread，卖 A、买 B。
- 持仓后 `|z| < exit_threshold`: exit。
- 持仓后 `|z| > stop_threshold`: stop。
- 协整 p 值超过阈值或半衰期超过阈值时，训练窗口不启用交易。

## 成本模型
配对交易是双腿交易。一次进场同时成交 A 和 B；一次平仓再次成交 A 和 B。

```python
round_trip_cost = 2 * (
    asset_a_qty * asset_a_price
    + asset_b_qty * asset_b_price
) * (fee + slippage + latency)
```

因此一笔完整 round-trip 包含四次单腿成本。`tests/strategy/pairs_trading/test_strategy.py` 显式覆盖该计算。

## 研究规则
- H-200 到 H-204 必须严格 ablation，每次只改一个变量。
- H-205 多 pair 必须独立注册、独立评估，禁止只报告最好的 pair。
- 数据要求是至少 2 年同步 1h 数据；不足时标记 `deferred`。
- `commands.py` 暂不接入，Brain 命令应在研究核心稳定后单独完成。
