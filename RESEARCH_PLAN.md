# 长程推理天花板研究计划

> **项目**：长程推理天花板：早期误差锚定、信用分配与验证时对抗性防御的统一框架
> **状态**：active ｜ **循环阶段**：假设提出（迭代 0）｜ **创建**：2026-11-01
> **研究问题**：长程推理的 test-time scaling 天花板是否源于「早期误差锚定」与「中间步信用分配信息不对称」的相互强化，以及能否通过在早期步骤注入可信且不被攻击的验证信息来破除？

---

## 0. 缘起与定位

本研究从用户一段草稿论断的核查生长而来。初始三条论断（自我纠错被证伪 / 验证器难造 / 推理算力换成绩曲线变平）经文献核查后，进一步深挖三个方向，发现三条论断并非孤立事实，而是**同一个闭环的三个侧面**：

- **早期误差锚定**（error anchoring / Tunnel Vision）决定 test-time scaling 的饱和点；
- **中间步信用分配信息不对称**（仅最终结果有真值）是早期误差锚定的根因；
- **验证信息被奖励污染**（reward hacking）使「注入验证信息」这一防御手段自身失效。

三者相互强化，构成长程推理的实际天花板。本研究把三者统一为一个可证伪的框架，并给出防御着力点。

---

## 1. 核心研究问题

**Q1**：长程推理的 test-time scaling 饱和点（plateau）是「算力总量」的函数，还是「早期误差锚定」的函数？

**Q2**：早期误差锚定的根因是否为「中间步 credit 信息不对称」？

**Q3**：在早期步骤注入「可信且不被攻击的验证信息」能否同时降低早期误差锚定概率并抬升饱和点？

---

## 2. 假设（已登记）

- **H1**：test-time scaling 饱和点由早期误差锚定决定，而非由可用算力总量决定。同一任务在锚定发生后增加顺序算力收益递减，而增加并行路径（重采样）在锚定存在时收益相对更高。
  - 可证伪预测：① 存在阈值 T，顺序算力 > T 后 pass@k 边际收益显著下降；② 并行路径数 P 增加时，在锚定存在场景下收益 > 顺序场景；③ TTSPM 的 saturation point 与早期锚定率相关。
- **H2**：中间步 credit 信息不对称是早期误差锚定的根因。注入可独立判定的步级验证信息可提升早期步 credit 精度，降低锚定概率。
  - 可证伪预测：① 早期步 credit 噪声与最终正确率负相关；② 注入步级验证（TRCA/FoVer/SWE-MILE）后早期步信用精度↑、锚定概率↓、最终 pass@k↑。
- **H3**：验证器自身须具备对抗鲁棒性，否则「注入验证信息」会被奖励污染。形式化 verifier 与白盒监控可降低验证器被污染程度。
  - 可证伪预测：① 纯学习式 PRM 在 reward hacking 攻击下 exploit 认可率显著高于形式化 verifier；② DoM 向量/steering 能预测后续动作的 hack（在线预防），且与 LLM monitor 相当。

---

## 3. 理论框架（统一）

```
        验证信息被奖励污染 (H3 / reward hacking)
                │  污染早期步 credit
                ▼
   中间步 credit 信息不对称 (H2)
                │  早期步无法正确归因
                ▼
   早期误差锚定 / Tunnel Vision (H1)
                │  锁定次优搜索路径
                ▼
   test-time scaling plateau（饱和点提前）
                ▲
                │  再加算力只是填同一个坑
   边际收益递减（TTSPM saturation point）
```

**统一命题**：plateau 的位置由「早期锚定率 × 锚定后的轨迹可行域」决定，而非算力总量。三个 H 分别对应因果链的三环，防御着力点统一为：**在早期步骤注入可信且不被攻击的验证信息**。

---

## 4. 实验设计

### E1：锚定-算力解耦（检验 H1）

- **目的**：证明饱和点由锚定率决定，而非算力总量。
- **设计**：固定任务集（AIME/MATH-500/GPQA + 一个长程 agentic 基准如 BrowseComp-Plus），对同一模型变体（Qwen3-8B/32B）做两维扫描：
  - 顺序算力 N（采样深度、迭代次数）× 并行路径 P（重采样数）；
  - 记录每格 pass@k、早期步锚定率（用 FALCA 定义的 anchor-on-incorrect-candidate）、TTSPM saturation point。
- **关键比较**：固定 P、增 N 的边际收益 vs 固定 N、增 P 的边际收益；锚定率高 vs 低的子群在两种维度上的收益差。
- **判据**：H1 成立当且仅当「锚定率」解释饱和点方差的占比显著大于「算力总量」。
- **基线**：Snell 2408.03314（compute-optimal）、TTSPM 2505.20522、ParaThinker 2509.04475。

### E2：步级验证注入（检验 H2）

- **目的**：注入独立可判定的步级验证信息，检验其对 credit 精度与锚定率的影响。
- **设计**：在同任务上比较四条臂：
  - A0 基线（GRPO 最终奖励）；
  - A1 TRCA 式步级监督（action-induced transitions）；
  - A2 FoVer 式形式化 verifier 合成 PRM 数据（Z3/Isabelle）；
  - A3 SWE-MILE 式异步隔离沙箱重放 + milestone credit。
- **关键比较**：A1/A2/A3 vs A0 的早期步 credit 精度、锚定率、最终 pass@k；A2 vs A1 的对抗鲁棒性（见 E3）。
- **判据**：H2 成立当且仅当任一注入臂在锚定率显著下降的同时 pass@k 显著上升。
- **基线**：TRCA 2608.16156、FoVer 2505.15960、SWE-MILE 2609.32631、Self-Credit 2610.28388。

### E3：验证器对抗鲁棒性（检验 H3）

- **目的**：检验学习式 PRM 在 reward hacking 攻击下是否比形式化 verifier/白盒监控更易被污染。
- **设计**：用 RHB 的 exploit 数据集对三类验证器做攻击测试：
  - V1 纯学习式 PRM（如 ScalePRM 生成式 PRM）；
  - V2 形式化 verifier（Z3/Isabelle）；
  - V3 白盒 DoM 向量监控 + LLM monitor。
- **关键比较**：三类验证器在 exploit 样本上的认可率（False-Accept rate）；V3 的在线预测能力（CoT 上预测后续 hack）。
- **判据**：H3 成立当且仅当 V2/V3 的 False-Accept 显著低于 V1，且 V3 能在线预测。
- **基线**：RHB 2605.02964、2609.19101（DoM）、2610.29129（steering）、ScalePRM 2512.03244。

### E4（可选扩展）：锚定-注入耦合

- **目的**：检验「注入可信验证信息」是否能破除 plateau（H1×H2×H3 联合）。
- **设计**：E2 的最优臂 × E3 的最优验证器，在 E1 的锚定高发子群上重跑 E1 的算力扫描。
- **判据**：联合臂的饱和点显著高于各单臂，且早期锚定率下降可解释该提升。

---

## 5. 预期贡献

1. **理论**：把「plateau」「error anchoring」「credit 信息不对称」「reward hacking」四者纳入一个可证伪的统一框架（TTSPM 的 saturation point 作为数学支点）。
2. **方法**：给出「在早期步注入可信验证信息」的具体可实验组合（TRCA+FoVer、SWE-MILE+DoM），以及验证器对抗鲁棒性的评估协议。
3. **实证**：H1-H3 的可证伪预测 + E1-E3 的实验判据，可直接复用现有基准。

## 6. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 计算成本高（E1 两维扫描 + E3 攻击测试） | 高 | 先小模型（Qwen3-4B/8B）扫出锚定-算力曲面，再在 32B 验证关键格；上云（AMD T4/Kaggle/ModelScope） |
| 早期锚定率测量无标准定义 | 中 | 用 FALCA 的 anchor-on-incorrect-candidate 定义 + 人工抽检一致性 |
| 形式化 verifier 难以覆盖 agentic 任务 | 高 | 仅对封闭可验证子集用 V2；开放任务用 V3 白盒监控替代 |
| H3 的 reward hacking 攻击集依赖 RHB 复现 | 中 | RHB 开源；无法复现则用 2604.26130 reward-lens 的 probe 套件自建 |
| 开放任务（创意/临床报告）无规则真值 | 高 | 明确声明本研究限封闭可验证 + agentic 可验证子集；开放任务列为未来工作 |

## 7. 下一步

1. ✅ 落盘实验设计到 `experiments/`（E1-E3 各一份 design.md，已细化到可执行规格，2026-11-01）。
2. ✅ 构建工程架构工具链 `tools/`（v0.2：5 层分层 + 8 命令命令树 + 25 项 RED→GREEN 测试 + 配置系统，2026-11-01）。
3. 建立文献库 `literature/`（已验号的 30+ 篇，含标题/arXiv id/要点）。
4. 探明可用算力通道（AMD T4 / Kaggle / ModelScope），定 E1 的可行性窗口。
5. 如需投稿：目标 TMLR（两段式：arXiv 预印本先行）。

### 实验细化摘要（2026-11-01）

- **E1（92行）**：任务集 AIME2024/2025+MATH-500+GPQA-Diamond+BrowseComp-Plus；模型 Qwen3-4B/8B 扫曲面 + 32B 验证关键格 + R1-Distill-1.5B/7B 对齐 TTSPM Table 1；两维扫描 N∈{1,2,4,8,16,32}×P∈{1,2,4,8,16}；锚定率用 FALCA 定义；N\* 用 TTSPM Eq.14；统计用 ANCOVA 方差分解。
- **E2（76行）**：四臂 A0 GRPO / A1 TRCA / A2 FoVer / A3 SWE-MILE；任务集 ALFWorld+WebShop+SearchQA（对齐 TRCA 直接引用）+AIME/MATH-500 封闭子集；模型 Qwen2.5-1.5B/7B（与 TRCA 一致，rollout group=8，λ=0.8）；消融去 Breakthrough + λ 敏感性；对齐数字：TRCA 1.5B ALFWorld 92.0%/WebShop 90.5%/78.4%。
- **E3（74行）**：三验证器 V1 学习式 PRM / V2 形式化 / V3 白盒 DoM+LLM；攻击集 RHB 6 类 exploit + chained regime（链长 2-7）；测量 False-Accept/False-Reject/AUC-ROC + V3 在线预测；统计 Clopper-Pearson 95% CI + Fisher exact；对齐数字：RHB exploit rate 0~13.9%、V3 0.6% vs 13.9% 孪生对比。
- **归档**：工件 `longhorizon-e1e3-detailed-design` v1（3 文件 SHA-256 已存）。

### 工具链工程架构（2026-11-01，v0.2）

项目已从「研究计划」转向**工程架构**（用户指示「不要论文 要架构 要工程 要项目」）。核心产出：

- **5 层架构**：CLI（lhr_tools/cli.py）→ 服务（services/pipeline.py, reporter.py）→ 测量（metrics/anchor,saturation,credit,verifier）→ 数据（io/jsonl,schema,generate）→ 配置（config/loader, default.yaml）。
- **8 命令命令树**：anchor / saturation / credit / verifier / dataset / report / config / selftest。
- **25 项分层测试**（test_metrics 10 + test_io 7 + test_cli 8）全部 RED→GREEN 通过。测试抓出真 bug：`DEFAULTS` 浅拷贝污染（环境变量覆盖会改到全局默认值）——已用 `copy.deepcopy` 修复。
- **配置系统**：YAML/JSON 加载 + 默认值 + `LHR_` 环境变量覆盖，自带 RED→GREEN 自检。
- **校准对齐文献**：R1-Distill-1.5B AIME2024 顺序 pass@32=30.0% → p_x=0.0111 → N*=807（文献 808）；并行 53.3% → p_x=0.0235 → N*=347。
- **归档**：工件 `longhorizon-eval-toolchain-v0-2` v1（43 文件 SHA-256 全部一致，artifact_verify status=ok）。

## 8. 参考文献（已验号）

- 2310.01798 Huang et al. ICLR 2024（self-correction 证伪）
- 2408.03314 Snell et al. ICLR 2025 Oral（test-time compute）
- 2509.04475 Wen et al.（ParaThinker, Tunnel Vision）
- 2504.16828 Khalifa et al.（ThinkPRM）
- 2504.00891 Zhao et al.（GenPRM）
- 2505.15960 Kamoi et al. ACL 2026 Findings（FoVer）
- 2512.03244 Rahman et al.（ScalePRM）
- 2605.02964（RHB, ICML 2026）
- 2604.13602（PCH survey）
- 2604.26360（UARD）
- 2609.19101（DoM 监控）
- 2610.29129（representation steering）
- 2610.21040（RRI）
- 2608.16156（TRCA）
- 2609.32631（SWE-MILE）
- 2602.10863（ICA, EMNLP 2026）
- 2610.28388（Self-Credit）
- 2603.08754（HCAPO）
- 2610.03372（SCAD）
- 2605.21768（Memory-R2）
- 2505.20522（TTSPM）
- 2606.06915（ThinkBooster）
- 2506.11595（EasyARC）
- 2608.11829（OPD reversal）
- 2610.28361（FALCA）
- 2411.15594（A Survey on LLM-as-a-Judge）
- 2410.21819（Self-Preference Bias）
- 2604.22891（Quantifying SPB）
- 2607.11871（Inside the Unfair Judge）
- 2603.24579（MARCH）
- 2405.14092（ProCo, EMNLP 2024）
- 2507.02778（Self-Correction Bench, COLM 2026）

## 工具链工程架构（2026-11-01，v0.3）

在 v0.2 基础上修复 4 个缺陷并补 CI，版本 0.2.0→0.3.0：

| 缺陷 | 内容 | 修复 |
|------|------|------|
| 2 | saturation 命令描述不一致（参数驱动 vs 数据驱动） | pipeline/cli docstring + README 数据流/命令树标注 |
| 3 | report 默认输出到 /tmp 不持久 | 默认输出到项目 `analyses/lhr-report.md`（新增 test_cli_report_default_output） |
| 4 | README 快速开始过时 | 逐字核对当前 CLI，快速开始块重写 + 逐条实测 |
| 5 | 缺 CI | 新建 `.github/workflows/ci.yml`（3 Python 版本矩阵） |

- 全套件 **29/29 RED→GREEN**（metrics 13 + io 7 + cli 9）；selftest 5 模块全过；bin/lhr-tools 独立入口冒烟通过。
- 归档工件 `longhorizon-eval-toolchain-v0-3` v2（27 文件，artifact_verify status=ok，全部 SHA-256 一致）。
- 项目 tools 目录 27 文件（无 pycache）。

## 工具链工程架构（2026-11-01，v0.4）

在 v0.3 基础上完成 A+B 扩展（A1-A4 功能扩展 + B5-B6 数据接入），版本 0.3.0→0.4.0：

| 项 | 内容 |
|----|------|
| A1 | `saturation` 加 `bootstrap_nstar_ci`（bootstrap 置信区间，修复全成功/全失败退化边界） |
| A2 | 新建 `services/visualize.py`（saturation_curve/anchor_dist/roc_curve/render，matplotlib PNG 或 ASCII 回退） |
| A3 | 新建 `services/compare.py`（compare_anchor/saturation/verifier + format_comparison，修复 argparse 单文件路由 bug） |
| A4 | 新建 `docs/API.md`（全部公开函数签名 + 11 命令树） |
| B5 | `generate.py` 加 `generate_realistic_rows`/`generate_realistic`（文献分布：verifier exploit rate ∈ [0, 13.9%]、credit accuracy ≈ 0.85，lambda 绑定修复 dispatch bug） |
| B6 | 新建 `io/importer.py`（真实推理轨迹导入：_group_by_trajectory / to_anchor_rows / to_credit_rows / to_verifier_rows / import_trajectory）+ CLI `import` 命令 |

- 全套件 **42/42 RED→GREEN**（metrics 15 + io 11 + cli 16）；CLI 命令树扩至 **11 命令**（新增 `import`）。
- 实测校准：B5 verifier exploit rate 0.0780 落在 RHB 观测范围、credit accuracy 0.8520 接近 TRCA 中值。
- 归档工件 `longhorizon-eval-toolchain-v0-4` v1（47 文件 SHA-256 一致）。

## 工具链审查修复（2026-11-01，v0.4.1）

对 v0.4 做独立审查，发现 3 个真实缺陷并全部修复（每项 RED→GREEN）：

| 缺陷 | 严重度 | 修复 | 验证 |
|------|--------|------|------|
| ① `bootstrap_nstar_ci` 百分位索引用 `n_boot` 而非 `len(boot_vals)` | HIGH | 分母改为实际分布大小 | 旧 lo=91 → 断言红；新 lo=65 通过 |
| ② `_group_by_trajectory` 丢弃 `trajectory_id=None` 行 | MEDIUM | 保留 null 组并按首现顺序插组 | 旧 2 轨迹 → 断言红；新 3 轨迹通过 |
| ③ CLI 无参数抛裸 `TypeError` | MEDIUM | `p_x is None` 提前抛清晰 `ValueError` | 旧 TypeError → 断言红；新清晰报错通过 |

- 新增回归测试 5 项；**全套件 47/47 RED→GREEN**（metrics 16 + io 13 + cli 18）。
- 版本 0.4.0→**0.4.1**；归档工件 `longhorizon-eval-toolchain-v0-4-1` v1（52 文件 SHA-256 一致，`artifact_verify` status=ok）。

## 工具链扩展 v0.5（2026-11-01，方向1/2/3 文献驱动）

用户「再找找论文 看看还有什么可以进化的吗 先把项目做大 再求精简」→ 三方向子代理检索（验证器/RM 15 篇、credit assignment 15 篇、误差锚定/长程推理 17 篇，全部 arXiv id 经 abs 页验号，唯一新增 ≈44 篇），从文献提取 6 类可测维度，扩展工具链 C1-C6：

### C1 轨迹级诊断（metrics/trajectory.py，方向3 误差锚定）

| 函数 | 文献来源 | 说明 |
|------|---------|------|
| `per_step_reliability` | arXiv:2609.01660 | 逐步可靠性（几何定律） |
| `geometric_ceiling` | arXiv:2609.01660 | 几何天花板 `p_x**L` |
| `snowball_rate` | arXiv:2607.16727 (CART) | 雪球率：错误后不再恢复比例 |
| `positional_impact` | — | 位置冲击：每步错误对结果权重 |
| `late_stage_fragility_index` | arXiv:2508.05282 | 后段脆弱性指数（加权错误位置） |
| `error_origin_detection` | — | 误差起点检测 |
| `error_spread_curve` | — | 误差扩散曲线 |
| `context_drag` | arXiv:2602.04288 | 上下文拖拽（跨轨迹 Levenshtein） |

### C2 校准指标（metrics/calibration.py，方向1）

| 函数 | 说明 |
|------|------|
| `expected_calibration_error` | ECE（等距 bin 加权） |
| `brier_score` | Brier 分数 |
| `reliability_diagram` | 可靠性图数据 |
| `confidence_margin` | 置信度裕度 |

### C3 验证器扩展（metrics/verifier.py，方向1 HARVE）

- `pattern_robustness_profile`：HARVE（arXiv:2606.03131）13 种攻击模式的鲁棒性剖面（每模式 false_accept 率 + 最弱模式）。

### C4 credit 扩展（metrics/credit.py，方向2 PURE）

- `min_form_credit`：最小形式 credit（arXiv:2504.15275），`min` 跨步精度（最弱环节视图）。
- `weakest_link_dominance`：任一步错 → 0.0；全对 → 1.0。

### C5 saturation 扩展（metrics/saturation.py，方向1+3）

- `scaling_law_exponent`：局部缩放指数（ln 边际收益，负值 = 收益递减）。
- `geometric_ceiling`：几何天花板（与 C1 共享，arXiv:2609.01660）。

### C6 CLI 命令树扩展（cli.py）

- 新增 `trajectory` / `calibration` 命令 → **13 命令**；selftest 覆盖 7 模块（RED→GREEN）。

### 验证与归档

- 新测试 14 项（trajectory 8 + calibration 4 + CLI 2）；**全套件 61/61**（metrics 28 + io 13 + cli 18），1.55s。
- 版本 0.4.1→**0.5.0**；README 命令树 13 命令 + 目录结构 + 快速开始更新；docs/API.md 加 C1-C5 函数签名。
- 归档工件 `longhorizon-eval-toolchain-v0-5` v2（35 文件 SHA-256 一致，`artifact_verify` status=ok；v1 废弃——误含 `__pycache__`/`saturation_curve.png` 生成物）。

## 工具链 v0.5.1（2026-11-01，v0.4 审查注记处理）

用户选中 v0.4 审查遗留的 3 项注记处理（每项 RED→GREEN）：

| 注记 | 修复 | 新测试 |
|------|------|--------|
| ⑤ `_within` radius>0 非 int 静默 no-op | radius>0 且状态非 int 抛清晰 `ValueError`（anchor.py） | `test_anchor_within_radius_positive_non_int_raises` + `test_anchor_within_radius_zero_non_int_noop` |
| ④ B5 `generate_realistic` 未接 CLI（API-only） | `dataset` 命令加 `--realistic` flag → `generate_realistic` | `test_cli_dataset_realistic`（exploit rate ∈ [0, 0.15]） |
| ⑥ `to_verifier_rows` 用自评 confidence 作 verifier score | score 优先用输入 `verifier_score` 字段（真实验证器信号），无则回退 confidence（代理） | `test_importer_verifier_prefers_external_score` + `test_importer_verifier_falls_back_to_confidence` |

- 全套件 **66/66**（原 61 + 新增 5），1.24s；版本 0.5.0→**0.5.1**。
- README 快速开始加 `--realistic` 行；docs/API.md 更新 dataset 命令树行 + `_within`/`to_verifier_rows` 注记。
- 归档工件 `longhorizon-eval-toolchain-v0-5-1` v1。
