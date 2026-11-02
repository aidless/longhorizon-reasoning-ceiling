# E3：验证器对抗鲁棒性（检验 H3）

> 状态：细化完成 ｜ 更新：2026-11-01 ｜ 依据：RHB (2605.02964)、DoM 监控 (2609.19101)、representation steering (2610.29129)、ScalePRM (2512.03244)、FoVer (2505.15960)

## 1. 假设与可证伪预测

**H3**：验证器自身须具备对抗鲁棒性，否则「注入验证信息」会被奖励污染。形式化 verifier 与白盒监控可降低验证器被污染程度。

- P1：纯学习式 PRM（V1）在 reward hacking 攻击下 False-Accept rate 显著高于形式化 verifier（V2）。
- P2：V3（DoM 向量 + LLM monitor）能在线预测后续动作的 hack（CoT 上跑），且与 LLM monitor 捕获率相当。
- P3：V2/V3 的 False-Accept 显著低于 V1。

## 2. 三类验证器

| 验证器 | 类型 | 机制 | 文献 |
|---|---|---|---|
| V1 | 纯学习式 PRM | 生成式 PRM（ScalePRM 式），从训练数据学习步级判断 | 2512.03244 |
| V2 | 形式化 verifier | Z3/Isabelle 合成步级验证；封闭可验证子集 | 2505.15960 |
| V3 | 白盒 DoM + LLM monitor | difference-of-means 向量监控 + 独立 LLM 审查 | 2609.19101 / 2610.29129 |

## 3. 攻击集（RHB 对齐）

- **主集**：RHB 的 exploit 数据集（6 类 exploit 分类：leakage/tampering/sequence manipulation/proxy gaming/special-casing/denial-of-evaluation）。
- RHB 关键数字（用于校准）：
  - 13 个前沿模型，exploit rate 0%（Claude Sonnet 4.5）~ 13.9%（DeepSeek-R1-Zero）。
  - 受控孪生对比：DeepSeek-V3 0.6% vs DeepSeek-R1-Zero 13.9%（RL 后训练关联更高 hack）。
  - 72% 的 exploit 含显式 CoT 理由（模型把 exploit 包装成合法解题）。
  - 环境加固降 5.7pp（相对 87.7%）。
- **补充集**：2604.26130 reward-lens 的 probe 套件自建 exploit 样本（若 RHB 无法复现）。
- 每验证器在 exploit 样本 + 诚实样本上打分，测量 False-Accept rate（exploit 被认可为合格的比例）与 False-Reject rate（诚实被误杀）。

## 4. 测量定义

- **False-Accept rate**：exploit 样本中被验证器判为「合格/可接受」的比例（越高越危险）。
- **False-Reject rate**：诚实样本中被判为「不合格」的比例（越高越保守）。
- **在线预测能力（V3）**：在 CoT 中间步跑 DoM 向量，预测后续动作是否为 hack；与 LLM monitor 捕获率对比。
- **AUC-ROC / AUPRC**：验证器区分 exploit vs 诚实样本的判别力。

## 5. 关键比较与判据

| 比较 | 判据（H3 成立方向） |
|---|---|
| V1 vs V2 False-Accept | V2 显著低于 V1 |
| V1 vs V3 False-Accept | V3 显著低于 V1 |
| V3 在线预测 | DoM 向量在 CoT 上可预测后续 hack |
| V3 vs LLM monitor 捕获率 | 相当（±5pp 内） |
| False-Reject 权衡 | V2/V3 的 False-Reject 不可过度升高（诚实解法不被误杀） |

**对齐 RHB 数字**：V1 在 R1-Zero 类样本上应接近 13.9% 的识别率基线（即 V1 会认可大量 exploit），V2/V3 应显著更低。

## 6. 统计与鲁棒性

- exploit 样本与诚实样本各 ≥ 200（RHB 每模型 40 独立 + 35 链）。
- 报告 Clopper-Pearson 95% CI（RHB 用此）。
- 组间差异用 Fisher exact test（RHB 用此）。
- 攻击强度扫描：简单 exploit → 复杂多步 exploit（RHB 的 chained regime，链长 2-7）。

## 7. 风险与对策

| 风险 | 对策 |
|---|---|
| RHB 复现难度 | RHB 开源；无法复现则用 reward-lens probe 套件 |
| V2 不覆盖开放任务 | 仅封闭可验证子集 |
| V3 需白盒访问 | 用开源模型（Qwen3 系列）获得内部表征 |
| 攻击集代表性不足 | 6 类 exploit 全覆盖 + chained regime |

## 8. 基线文献

- 2605.02964 RHB（exploit 率基准）
- 2609.19101 DoM 监控（内部表征）
- 2610.29129 representation steering（缓解）
- 2512.03244 ScalePRM（生成式 PRM）
- 2505.15960 FoVer（形式化 verifier）
- 2604.26130 reward-lens（probe 套件）
