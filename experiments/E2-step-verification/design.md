# E2：步级验证注入（检验 H2）

> 状态：细化完成 ｜ 更新：2026-11-01 ｜ 依据：TRCA (2608.16156)、FoVer (2505.15960)、SWE-MILE (2609.32631)、Self-Credit (2610.28388)

## 1. 假设与可证伪预测

**H2**：中间步 credit 信息不对称是早期误差锚定的根因。注入可独立判定的步级验证信息可提升早期步 credit 精度，降低锚定概率。

- P1：早期步 credit 噪声与最终正确率负相关。
- P2：注入步级验证后早期步 credit 精度↑、锚定概率↓、最终 pass@k↑。
- P3：形式化 verifier（A2）比 transition 式（A1）在 agentic 任务上覆盖窄但更精确。

## 2. 四臂设计

| 臂 | 方法 | 关键机制 | 文献 |
|---|---|---|---|
| A0 | GRPO 最终奖励 | 稀疏终端奖励，无中间 credit | Shao 2024 |
| A1 | TRCA 式步级监督 | Evidence/Execution/Invalidity 三 rubric，从 action-induced transitions 推导 | 2608.16156 |
| A2 | FoVer 式形式化 verifier | Z3/Isabelle 合成 PRM 数据，步级形式化验证 | 2505.15960 |
| A3 | SWE-MILE 式异步隔离沙箱 | 异步 shadow probing 重放 repo 改动 + 并行验证 | 2609.32631 |

## 3. 任务集（与 TRCA 对齐以直接引用其数字）

| 基准 | 规模 | 类型 | 说明 |
|---|---|---|---|
| ALFWorld | 6 类任务 | 文本体感 | TRCA Table 1 直接对比 |
| WebShop | 完整 | 交互购物 | TRCA Table 1；task score + success rate |
| SearchQA（7 数据集） | NQ/TriviaQA/PopQA/HotpotQA/2Wiki/MuSiQue/Bamboogle | 检索增强 QA | TRCA Table 2；严格二元 EM |
| AIME/MATH-500（封闭可验证子集） | 60 题 | 数学 | 供 A2 形式化 verifier 使用 |

## 4. 模型与算力

- 策略模型：Qwen2.5-1.5B-Instruct / 7B-Instruct（与 TRCA 完全一致，便于对齐）；Qwen3-8B 作扩展。
- 组大小：rollout group size N=8（TRCA 设置）。
- λ（Foundational vs Breakthrough 混合系数）= 0.8（TRCA 最优）。
- 温度 1.0，最大响应长度 512 token（ALFWorld），最大交互步数 25。
- 预算：每臂 × 3 随机种子。TRCA 用 4×A800 80GB；本实验先 1.5B 扫 4 臂，再 7B 验证。

## 5. 测量定义

- **早期步 credit 精度**：用 TRCA 诊断——早期步（前 20% 步）的 credit 信号与人工标注一致率（Cohen's κ）。TRCA 的 96.5% 失败率 / 85.6% 无成功轨迹组 / 72.2% 有效 transition 信号是 baseline 参考。
- **锚定率**：FALCA 定义（同 E1）。
- **pass@k / success rate**：ALFWorld 报 success rate；WebShop 报 task score + success rate；SearchQA 报严格二元归一化 EM。

## 6. 关键比较与判据

| 比较 | 判据（H2 成立方向） |
|---|---|
| A1/A2/A3 vs A0 早期步 credit 精度 | 注入臂 κ 显著高于 A0 |
| A1/A2/A3 vs A0 锚定率 | 注入臂锚定率显著下降 |
| A1/A2/A3 vs A0 最终 pass@k | 注入臂 pass@k 显著上升 |
| A2 vs A1（agentic 覆盖） | A2 覆盖窄但精确；A1 覆盖广 |

**对齐 TRCA 数字**（用于验证复现）：TRCA 在 Qwen2.5-1.5B-Instruct 上 ALFWorld 整体 92.0%、WebShop task score 90.5%、success rate 78.4%（比 GiGPO +5.3%/+7.4%/+13.4%）；Qwen2.5-7B-Instruct 94.5%/92.9%/83.8%。SearchQA 3B 平均 45.4%（比 IGPO +8.2%、GiGPO +3.3%）。

## 7. 统计与鲁棒性

- 3 随机种子，报告均值 ± std（TRCA 用 3 seeds）。
- 组间差异用配对 t 检验 / Fisher exact test。
- 消融：A1 去掉 Breakthrough Rubric Reward（TRCA 显示其贡献更大）；λ 敏感性 {0.2, 0.4, 0.5, 0.6, 0.8, 1.0}。

## 8. 风险与对策

| 风险 | 对策 |
|---|---|
| A2 形式化 verifier 不覆盖 agentic | 仅用于封闭可验证子集（AIME/MATH-500） |
| 训练成本 4 臂 × 多基准 | 先 1.5B 扫 4 臂；7B 仅验证 A0/A1 最优臂 |
| TRCA 复现难度（A800） | 用云端通道；先验证 Table 1 数字再放大 |
| SearchQA 检索工具依赖 | 用开源检索器（BM25/DPR）复现 |

## 9. 基线文献

- 2608.16156 TRCA（步级 rubric credit）
- 2505.15960 FoVer（形式化 verifier 合成 PRM 数据）
- 2609.32631 SWE-MILE（异步隔离沙箱里程碑 credit）
- 2610.28388 Self-Credit（自生成 credit + intra-group rescaling）
