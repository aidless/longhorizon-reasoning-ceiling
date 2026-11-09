# v0.5 扩展计划

> Historical note, not a current claim. Counts and "全部 arXiv 验号通过" were not re-checked in the honesty pass. Current claims are in the root README. Citation gaps are in `FAILURE_MODES.md`.

## 背景

用户 m01235「再找找论文 看看还有什么可以进化的吗 先把项目做大 再求精简」。
三个方向共检索 47 篇新文献（全部 arXiv 验号通过），发现现有工具链的测量缺口。

## 现有工具链（v0.4.1）

**指标模块（4 个）**：
- anchor.py: `anchor_rate` / `anchored_ids` / `Trajectory`
- saturation.py: `saturation_point` / `pass_at_k` / `estimate_px` / `bootstrap_nstar_ci` / `SaturationParams`
- credit.py: `cohens_kappa` / `credit_precision` / `StepCredit`
- verifier.py: `false_accept_rate` / `false_reject_rate` / `auc_roc` / `auprc` / `Verdict`

**服务**：compare / pipeline / reporter / visualize / config
**IO**：generate / importer / jsonl / schema
**CLI**：11 命令（anchor/saturation/credit/verifier/dataset/report/visualize/compare/config/import/selftest）

## 三方向检索发现（可扩展维度）

### 方向1 验证器/RM（15 篇）
新维度缺口：
1. **对抗鲁棒性剖面**（HARVE 2606.03131，13 种模式）— 现有只测总体 exploit rate
2. **校准/置信度边际**（RLCM 2604.23333，VL-Cal 2604.09529，Calibration Collapse 2604.10585）— 现有测 AUC/AUPRC 不测 ECE
3. **共训增益**（CoRe 2609.36245，RL Tango 2505.15034）— 静态 RM → 动态共训
4. **标度律指数**（GenRM Scaling Laws 2610.30765）— 单点性能 → 性能 vs 规模
5. **信用分配形式**（PURE min-form 2504.15275，LCA 2606.27739）— sum vs min，可学习权重

### 方向2 credit assignment（15 篇）
新维度缺口：
1. **信用聚合函数形式**（PURE 2504.15275）— sum vs min，可测「最弱环节支配度」
2. **信用权重可学习性**（LCA 2606.27739）— 学到的信用分布 vs 人工 rubric 偏差
3. **credit 方差分解**（2605.16302）— 反事实路径降低方差
4. **条件奖励校准**（2509.26578 CRM）— P(reward|step) 校准误差
5. **归因误差传播曲线**（P2T 2610.18704）— token→reward 归因矩阵累积误差

### 方向3 误差锚定/长程推理（17 篇）
新维度缺口：
1. **snowball rate**（CART 2607.16727）— 首错→全链失败概率，MLLM 上 0.65
2. **每步可靠性 p 几何律**（How Fast Do Agents Rot 2609.01660）— 长程天花板解析形式
3. **晚期脆弱性**（Late-Stage Fragility 2508.05282）— 晚期误差更致命，positional impact score
4. **上下文拖拽强度**（Contextual Drag 2602.04288）— 树编辑距离量化错误轨迹继承
5. **误差起源点/转移点检测**（2604.14528）— token 级熵尖峰定位
6. **多代理错误级联建模**（Spark to Fire 2603.04474）— 有向依赖图传播动力学
7. **提前终止/上下文衰减**（Context Rot 2606.29718）— 模型何时提前放弃

## v0.5 目标（先做大）

新增 2 个指标模块（扩展 3 个方向的核心维度），并扩展 CLI 命令树：

### C1 新指标模块：`trajectory.py`（方向3 误差锚定/长程）
基于方向3 的 7 个新维度，实现：
- `per_step_reliability` — 每步可靠性 p（几何律，2609.01660）
- `snowball_rate` — 首错→全链失败概率（2607.16727 CART）
- `positional_impact` — 每步误差危害权重曲线（2508.05282）
- `error_origin_detection` — 误差起源点定位（2604.14528，token 级熵尖峰）
- `context_drag` — 树编辑距离量化的错误轨迹继承强度（2602.04288）

### C2 新指标模块：`calibration.py`（方向1 验证器校准）
基于方向1 的校准维度，实现：
- `expected_calibration_error` — ECE（2604.23333 RLCM）
- `reliability_diagram` — 可靠性图
- `confidence_margin` — 置信度边际

### C3 扩展 `verifier.py`：分模式鲁棒性
- `pattern_robustness_profile` — 13 种 RewardHackBench 模式的鲁棒性剖面（HARVE 2606.03131）

### C4 扩展 `credit.py`：信用分配形式
- `min_form_credit` — PURE min 形式（2504.15275）
- `weakest_link_dominance` — 最弱环节支配度

### C5 扩展 `saturation.py`：标度律 + 可靠性模型
- `scaling_law_exponent` — 标度律指数（2610.30765 GenRM）
- `geometric_ceiling` — 每步可靠性 p 的几何律天花板（2609.01660）

### C6 CLI 命令树扩展
- 新增 `trajectory` 命令（C1）
- 新增 `calibration` 命令（C2）
- 扩展 `verifier` 命令加 `--patterns`（C3）
- 扩展 `credit` 命令加 `--min-form`（C4）
- 扩展 `saturation` 命令加 `--scaling` / `--geometric`（C5）

### C7 文档更新
- `docs/API.md` 补新函数签名
- README 命令树更新
- RESEARCH_PLAN.md 加 v0.5 小节 + 新文献
- 文献库补 47 篇（literature/ 目录）

## 实现顺序

1. C1 新模块 trajectory.py（方向3，最相关）
2. C2 新模块 calibration.py（方向1）
3. C3-C5 扩展现有模块
4. C6 CLI 集成
5. C7 文档 + 归档
6. 全套件 RED→GREEN + 归档 v0.5

## 验证方式

每步新增测试 RED→GREEN（先写测试断言违规红、再实现绿）。
全套件跑完（metrics + io + cli + selftest）确保无回归。
归档工件 `longhorizon-eval-toolchain-v0-5` 并 artifact_verify。

## 新增参考文献（47 篇，全部验号）

### 方向1（15 篇）
2504.06141, 2602.01750, 2606.03131, 2610.15924, 2609.36245, 2505.15034,
2610.30765, 2502.00271, 2509.26578, 2504.15275, 2606.27739, 2604.23333,
2604.09529, 2604.10585, 2602.23440

### 方向2（15 篇）
2504.15275, 2606.27739, 2608.16156, 2603.08754, 2508.02298, 2605.16302,
2509.26578, 2602.01791, 2605.25507, 2604.09459, 2601.03823, 2602.09953,
2604.20659, 2606.19236, 2610.18704

### 方向3（17 篇）
2602.04288, 2604.14528, 2508.05282, 2606.02430, 2607.16727, 2609.01660,
2607.21433, 2601.17593, 2604.05655, 2602.15332, 2608.30650, 2610.36471,
2604.18567, 2601.17593, 2606.05402, 2604.25931, 2608.14320, 2603.04474,
2606.29718

### 重复去重
2504.15275 / 2606.27739 / 2509.26578 在方向1、2 重复（计入一次）
2601.17593 在方向3 出现两次（验号后标题为「LLMs Think with DAGs」）
实际唯一新增 = 47 - 2（方向1/2 重复去重） - 1（方向3 内部重复）= 44 篇
