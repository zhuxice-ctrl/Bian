# H-207 · ADF p-value precision upgrade / methodology correction

类别标签：`methodology-correction`

本卡不是研究假设，不旨在改善任何已有 H 的结论或寻找 alpha。
目标：将 ADF 检验的 p-value 输出从 4 桶分类（0.01 / 0.049 / 0.10 / 0.50）升级为连续值，
使协整 gate 的统计表达忠实于其名义精度。

预期结果：H-200 BTC/ETH 在新工具下大概率仍 fail。
- half-life=3431.18 已独立证伪均值回归假设
- 工具升级不应被理解为"给 H-200 翻案的机会"
- 若新连续 p-value 偶然落入 ≤0.05 区间，也不构成做单依据，
  必须开新研究分支重新评估（例如 H-208 "BTC/ETH 在 H-207 工具下的边界协整观察"）

## 背景
`exports/ablation-pairs-2026-05-23-rerun.md` 已披露：当前 ADF/协整 p-value 使用 4 桶 MacKinnon-style 阈值映射，`p=0.5000` 表示 ADF 统计量未达到任何显著性阈值，不应被理解为精确连续 p-value。

## 目标
让协整 gate 的统计表达精度匹配它的语义承诺，仅此而已。H-207 不寻找 alpha，不调整策略参数，不修改 H-200~H-205 的研究契约。

## 实现路径
- 保留现有 ADF OLS 回归逻辑。
- 将 p-value 主输出从 4 桶分类改为连续的 MacKinnon-style 插值近似。
- 保留 bucket 输出作为方法论对照字段，便于解释旧报告。
- 用固定合成数据测试连续 p-value 与旧 bucket 的差异。

## 验收边界
- 不修改任何 H 卡的 entry gate 阈值，仍是 p ≤ 0.05、half-life ≤ 240。
- 新工具产出的 ablation 报告必须明确写"工具升级，不是结论翻案"。
- 即使新 BTC/ETH p-value 大幅改变，也不得在本卡里宣称任何研究结论。

## 范围外
- 寻找新 pair / 新策略：不属于 H-207。
- 调整阈值：不属于 H-207。
- 基于新结果做单：不属于 H-207。
