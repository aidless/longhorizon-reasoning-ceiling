# lhr_tools API Reference (v0.5.1)

本文件列出 `lhr_tools` 各模块的公开函数签名、参数与返回结构。所有函数均为纯 Python 标准库实现（无第三方依赖）。

## metrics/anchor.py — 早期误差锚定（E1）

### `anchor_rate(trajectories: Sequence[Trajectory]) -> float`
计算轨迹集合的锚定率（锚定轨迹数 / 总轨迹数）。

**参数**：`trajectories` — `Trajectory` 对象序列，每个含 `steps`（步结果列表）、`correct`（正确步集合）、`anchor_fraction`（锚定阈值分数，默认 0.20）、`neighbourhood_radius`（邻域半径，默认 0）。

**返回**：`float` — 锚定率（0.0 ~ 1.0）。

**锚定判定**：当存在某步 `i` 满足「`correct` 中与 `i` 距离 ≤ radius 的步数占 `steps` 的分数 ≥ anchor_fraction」，即判定该轨迹被锚定。

---

### `Trajectory` dataclass
```python
@dataclass
class Trajectory:
    steps: list[int]           # 每步结果（编码值）
    correct: frozenset[int]    # 正确步的索引
    anchor_fraction: float = 0.20
    neighbourhood_radius: int = 0  # radius>0 仅支持整数状态；非 int 抛 ValueError（v0.4.1 已修）
```

---

## metrics/saturation.py — 饱和点 N*（E1）

### `saturation_point(params: SaturationParams) -> int`
计算 TTSPM Eq.(14) 饱和点：
```
N* = ceil( ln(eps * p_x / F_max) / ln(1 - p_x) )
```
**参数**：`params` — `SaturationParams`（`p_x` 单次成功概率 ∈ (0,1)、`f_max` 渐近性能 > 0、`eps` 边际收益阈值，默认 0.01）。

**返回**：`int` — 饱和点 N*（≥ 1）。

**异常**：`p_x` 不在 (0,1) 或 `f_max ≤ 0` 时抛 `ValueError`。

### `scaling_law_exponent(p_x: float, k: int) -> float`（C5）
计算第 k 次尝试的计算缩放指数（边际收益的对数）。返回负值表示收益递减；绝对值越大衰减越快。

**参数**：`p_x` — 单次成功概率 ∈ [0,1]；`k` — 尝试次数 ≥ 1。

**返回**：`float` — 缩放指数。

### `geometric_ceiling(p_x: float, max_steps: int) -> float`（C5）
几何天花板：`p_x ** max_steps`。长程推理天花板（arXiv:2609.01660 "How Fast Do Agents Rot?"）的数学形式——链条在 L 步内无错的概率指数衰减。

**参数**：`p_x` — 单步可靠性 ∈ [0,1]；`max_steps` — 链条长度 ≥ 0。

**返回**：`float` — `p_x ** max_steps`。

---

### `bootstrap_nstar_ci(successes: int, attempts: int, f_max: float, eps: float = 0.01, n_boot: int = 1000, seed: int = 42, alpha: float = 0.05) -> tuple[float, float]`
Bootstrap 置信区间（A1）。对观测的二元结果（成功/失败）做有放回重采样，每次重算 MLE `p_x` 与 `N*`，返回 `(alpha/2, 1-alpha/2)` 分位数区间。

**参数**：
- `successes` — 观测成功数
- `attempts` — 总尝试次数
- `f_max` — 渐近性能
- `eps` — 边际收益阈值（默认 0.01）
- `n_boot` — 重采样次数（默认 1000）
- `seed` — RNG 种子（默认 42，可复现）
- `alpha` — 双侧显著性水平（默认 0.05 → 95% CI）

**返回**：`(lo, hi)` — 置信区间下/上界。

**退化处理**：
- 全成功（`successes == attempts`）→ `(1.0, 1.0)`（第一发即饱和）
- 全失败（`successes == 0`）→ `(inf, inf)`（永不饱和）

---

### `pass_at_k(p_x: float, k: int) -> float`
k 次独立尝试至少成功一次的概率：`1 - (1 - p_x)^k`。

---

## metrics/credit.py — 早期步 credit 精度（E2）

### `cohens_kappa(pairs: Sequence[StepCredit]) -> float`
计算 Cohen's kappa（观察一致率与机会一致率的校正）。

**参数**：`pairs` — `StepCredit` 序列，每个含 `pred`（预测标签）、`truth`（真实标签）。

**返回**：`float` — kappa 值（-1 ~ 1）。

---

### `credit_precision(pairs: Sequence[StepCredit]) -> float`
计算 credit 精度（预测与真实一致的比率）。

---

### `min_form_credit(pairs: Sequence[StepCredit]) -> float`（C4）
最小形式 credit（PURE arXiv:2504.15275）：`min` 跨步的精度，反映"最弱环节"视图——链条 credit 只与其最弱步同强。

**返回**：`float` — [0,1]。

---

### `weakest_link_dominance(pairs: Sequence[StepCredit]) -> float`（C4）
最弱环节支配度：若任一步错误 → 0.0（链条整体失败）；全对 → 1.0。

**返回**：`float` — [0,1]。

---

### `StepCredit` dataclass
```python
@dataclass
class StepCredit:
    pred: str   # 预测标签（如 "positive"/"negative"）
    truth: str  # 真实标签
```

---

## metrics/verifier.py — 验证器对抗鲁棒性（E3）

### `false_accept_rate(verdicts: Sequence[Verdict]) -> float`
计算假接受率（被接受且实际为 exploit 的比例）。

---

### `false_reject_rate(verdicts: Sequence[Verdict]) -> float`
计算假拒绝率（被拒绝且实际为 honest 的比例）。

---

### `auc_roc(verdicts: Sequence[Verdict]) -> float`
计算 ROC AUC。正类 = exploit，分数低 = 检测成功。并列分数计 0.5 权重（Mann-Whitney）。

**注意**：AUC 必须同时满足——完美分离（honest 高分 / exploit 低分）= 1.0，反转 = 0.0，完全并列 = 0.5。

---

### `auprc(verdicts: Sequence[Verdict]) -> float`
计算 PR-AUC（precision-recall 曲线下面积）。

---

### `pattern_robustness_profile(verdicts: Sequence[Verdict]) -> dict`（C3）
HARVE（arXiv:2606.03131）13 种攻击模式的鲁棒性剖面。对每个模式计算 false_accept 率与样本数，返回 `{"pattern": {"false_accept": float, "n": int}, ...}` + `worst_pattern`。

**返回**：`dict` — 各模式 false_accept 率 + 最弱模式。

---

### `Verdict` dataclass
```python
@dataclass
class Verdict:
    is_exploit: bool   # 是否为 exploit 样本
    accepted: bool     # 验证器是否接受
    score: float       # 验证器打分（低分 = 更可能是 exploit）
```

---

## metrics/trajectory.py — 轨迹级诊断（C1，v0.5）

### `per_step_reliability(steps: Sequence[int], horizon: int | None = None) -> float`
逐步可靠性（几何定律，arXiv:2609.01660）：正确步占比。`horizon` 给定则只算前 horizon 步。

**返回**：`float` — [0,1]；空 → 1.0。

---

### `geometric_ceiling(p_x: float, max_steps: int) -> float`
几何天花板：`p_x ** max_steps`。

---

### `snowball_rate(trajectories: Sequence[Sequence[int]]) -> float`
雪球率（arXiv:2607.16727 CART）：轨迹中出现「错误后不再恢复」的比例。级联（一旦错误，后续全错）= 1.0；完全恢复 = 0.0。

---

### `positional_impact(steps: Sequence[int]) -> list[float]`
位置冲击：每步错误对最终结果的影响权重（步索引 × 是否错误）。后步错误权重更高。

**返回**：`list[float]` — 每步冲击值。

---

### `late_stage_fragility_index(steps: Sequence[int]) -> float`
后段脆弱性指数（arXiv:2508.05282 Late-Stage Fragility）：加权错误位置的归一化指数。错误集中在后段 → inf；前段 → 0.0；无错 → 1.0。

---

### `error_origin_detection(steps: Sequence[int], reference: Sequence[int]) -> int | None`
误差起点检测：返回第一个与 reference 不一致的步索引（1-based）；全对 → None。

---

### `error_spread_curve(trajectories: Sequence[Sequence[int]]) -> list[float]`
误差扩散曲线：每步位置的平均错误率。

---

### `context_drag(trajectories: Sequence[Sequence[int]]) -> float`
上下文拖拽（arXiv:2602.04288 Contextual Drag）：跨轨迹平均 Levenshtein 编辑距离。相同 → 0.0；完全不同 → 接近 1.0。

---

## metrics/calibration.py — 验证器/预测器校准（C2，v0.5）

### `expected_calibration_error(confidences: Sequence[float], outcomes: Sequence[bool]) -> float`
期望校准误差（ECE）：按等距 bin 分箱，每箱 |平均置信度 − 实际频率| 的加权平均。空输入 → 0.0。

---

### `brier_score(confidences: Sequence[float], outcomes: Sequence[bool]) -> float`
Brier 分数：`mean((conf - outcome)^2)`。完美校准 → 0.0。

---

### `reliability_diagram(confidences: Sequence[float], outcomes: Sequence[bool]) -> list[dict]`
可靠性图数据：每箱 `{"bin": (lo, hi), "accuracy": float, "count": int}`。

---

### `confidence_margin(confidences: Sequence[float], outcomes: Sequence[bool]) -> float`
置信度裕度：`mean(|conf - outcome|)`。

---

## config/loader.py — 配置加载

### `Config.load(path: str | Path | None = None) -> Config`
加载配置。默认从 `config/default.yaml` 读取，可被 `--config` 覆盖，环境变量 `LHR_*` 可覆盖单个值。使用 `copy.deepcopy` 防止嵌套 dict 污染全局默认值。

---

## io/jsonl.py — JSONL 读写

- `read_jsonl(path) -> list[dict]` — 读取 JSONL
- `write_jsonl(path, rows) -> None` — 写入 JSONL
- `iter_jsonl(path)` — 逐行迭代
- `write_json(path, obj) -> None` — 写入 JSON

---

## io/schema.py — Schema 校验

- `SCHEMAS` — 4 个指标（anchor/credit/verifier）的字段 schema
- `validate_rows(metric, rows) -> list[str]` — 校验失败返回错误列表（fail-closed）

---

## io/generate.py — 合成数据生成

- `generate(metric, n=10, seed=42) -> list[dict]` — 按指标生成合成数据（anchor/credit/verifier）
- `GENERATORS` — 生成器分发表
- `generate_realistic(metric, n=100, seed=42) -> list[dict]` — 按文献分布生成（B5：verifier exploit rate ∈ [0, 13.9%]、credit accuracy ≈ 0.85）
- `REALISTIC_GENERATORS` — 真实分布生成器分发表

---

## io/importer.py — 真实推理轨迹导入（B6）

- `import_trajectory(metric, rows) -> list[dict]` — 原始推理步 JSONL → 指标行格式
- `_group_by_trajectory(rows) -> list[list[dict]]` — 按 `trajectory_id` 分组（无 id 则每行自成轨迹）
- `to_anchor_rows(rows) -> list[dict]` — 转 `{steps: [0/1], correct: [idx]}`
- `to_credit_rows(rows) -> list[dict]` — 转 `{pred, truth}`（confidence ≥ 0.5 → positive）
- `to_verifier_rows(rows) -> list[dict]` — 转 `{is_exploit, accepted, score}`；score 优先用输入 `verifier_score` 字段（真实验证器信号），无则回退 `confidence`（代理，v0.4.1 注记 ⑥ 已修）
- `CONVERTERS` — 指标 → 转换器分发表

---

## services/pipeline.py — 服务编排

- `run_metric(metric, data_path, config=None) -> dict` — 运行指标，返回结构化结果（含 metric/n/data_file 元字段）
- `run_all(metric, data_path, config=None) -> dict` — 别名（接口对称）

---

## services/visualize.py — 可视化（A2）

- `saturation_curve(p_x, f_max, eps=0.01, k_max=64, n_star=None, output=None) -> str` — 饱和曲线（matplotlib 可用时 PNG，否则 ASCII）
- `anchor_dist(anchored_steps, output=None) -> str` — 锚定步分布直方图
- `roc_curve(verdicts, output=None) -> str` — 验证器 ROC 曲线
- `render(metric, result, output=None) -> str` — 按指标分发

---

## services/compare.py — 跨配置对比（A3）

- `compare_anchor(data_path, configs) -> list[dict]` — 多 (frac, radius) 配置对比
- `compare_saturation(configs) -> list[dict]` — 多 (p_x, f_max) 配置对比
- `compare_verifier(data_paths, labels) -> list[dict]` — 多数据集对比
- `format_comparison(rows) -> str` — 渲染 Markdown 对比表

### `CompareConfig` dataclass
```python
@dataclass
class CompareConfig:
    label: str                      # 配置标签
    params: dict[str, Any] = field(default_factory=dict)
```

---

## services/reporter.py — 报告生成

- `generate_report(results, output=None) -> str` — 生成 Markdown 报告（`output` 给定则写文件并返回路径）
- `result_to_md(result) -> str` — 单个结果渲染为 Markdown 表
- `format_value(v) -> str` — 标量格式化

---

## CLI 命令树（v0.5，13 命令）

| 命令 | 数据/参数驱动 | 说明 |
|------|--------------|------|
| `anchor` | 数据 | 锚定率（JSONL `{steps, correct}`） |
| `saturation` | 参数 | 饱和点 N*（`--px`/`--successes+--attempts`/`--fmax`/`--eps`） |
| `credit` | 数据 | 早期步 credit 精度（JSONL `{pred, truth}`） |
| `verifier` | 数据 | 验证器鲁棒性（JSONL `{is_exploit, accepted, score}`） |
| `trajectory` | 数据 | 轨迹级诊断（JSONL `{steps}`）（C1） |
| `calibration` | 数据 | 验证器/预测器校准（JSONL `{confidence, outcome}`）（C2） |
| `dataset` | 生成 | 合成数据（`--n`/`--seed`/`--output`；`--realistic` 文献校准分布 B5） |
| `report` | 聚合 | Markdown 报告（默认项目 `analyses/lhr-report.md`） |
| `visualize` | 绘制 | 指标输出图（matplotlib PNG / ASCII 回退） |
| `compare` | 对比 | 跨配置批量对比表 |
| `import` | 导入 | 原始推理轨迹 JSONL → 指标行 JSONL（B6） |
| `config` | 配置 | 显示/校验配置 |
| `selftest` | 自检 | 全部模块 RED→GREEN 自检 |
