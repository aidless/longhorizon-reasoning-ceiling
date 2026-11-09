# v0.4 独立审查报告（2026-11-01）

> Historical note. The 42/42 and 47/47 totals are this review's snapshot, not the current suite. Current claims are in the root README.

审查对象：`longhorizon-reasoning-ceiling/tools`（v0.4，A+B 扩展后）
审查范围：全部 22 个 .py（2266 行），重点 A1-A4 / B5-B6 新增代码
基线：全套件 42/42 RED→GREEN（metrics 15 + io 11 + cli 16）

---

## 修复状态（2026-11-01，v0.4.1）

三个缺陷全部修复，每项走 RED→GREEN 验证：

| 缺陷 | 修复 | 验证 |
|------|------|------|
| ① HIGH | `saturation.py` 百分位索引用 `len(boot_vals)` | RED：旧实现 lo=91 → 断言 lo<91 红；GREEN：新实现 lo=65 通过 |
| ② MEDIUM | `importer.py` 保留 null-id 行（按首现顺序插组） | RED：旧逻辑 2 轨迹 → 断言 3 红；GREEN：3 轨迹通过 |
| ③ MEDIUM | `cli.py` 无参数提前抛清晰 ValueError | RED：旧代码 TypeError → 断言 ValueError 红；GREEN：清晰报错通过 |

新增回归测试 5 项：`test_saturation_bootstrap_high_skip_index`（①）、`test_importer_null_id_not_dropped` + `test_importer_mixed_ids_preserve_order`（②）、`test_cli_saturation_no_params` + `test_cli_visualize_saturation_no_params`（③）。

**全套件 47/47 RED→GREEN**（metrics 16 + io 13 + cli 18，原 42 + 新增 5）；selftest 两模块通过。

---

## 结论

**3 个真实缺陷**（1 HIGH + 2 MEDIUM），**3 个设计/功能注记**（非阻断）。

### 缺陷 ①（HIGH）：`bootstrap_nstar_ci` 百分位索引用错分母

**文件**：`lhr_tools/metrics/saturation.py`（`bootstrap_nstar_ci`，约 L130-140）

**现象**：bootstrap 置信区间的百分位索引用 `n_boot` 当分母，但实际 bootstrap 分布大小是 `len(boot_vals)`——因为退化重采样（全成功/全失败）被跳过，`len(boot_vals) < n_boot`。

**根因**：低 `p_x` 时退化重采样率高（如 `1/40`：635/1000，跳过 365），索引错位。当前 lo 索引 24 对应实际分布百分位 0.0378，而应为 0.025。

**复现**：
```
successes=1/40:  current CI = (91, 324)   # 错
                 fixed   CI = (65, 324)   # 对（下界错 ~40%）
```

**影响**：低 `p_x` 场景（真实推理中常见）下 CI 下界被系统性高估，置信区间失真。属**静默正确性 bug**——现有测试（`30/60`，退化率低）测不出。

**修复**：索引分母改为 `len(boot_vals)`：
```python
n = len(boot_vals)
lo_idx = max(0, int((alpha/2) * n) - 1)
hi_idx = min(n-1, int((1-alpha/2) * n) - 1)
```
并补一个高退化率案例的测试（如 `1/40` 验证 CI 下界 < 91）。

---

### 缺陷 ②（MEDIUM）：`_group_by_trajectory` 静默丢弃 null 轨迹行

**文件**：`lhr_tools/io/importer.py`（`_group_by_trajectory`，约 L47）

**现象**：`order = [gid for gid in groups if gid is not None]`——`trajectory_id=None` 的行被分组到 `None` 键，但被 `order` 排除，导致该行**静默丢失**。

**复现**：
```python
rows = [t1, None-id 行, t2]  # 3 行
import_trajectory('anchor', rows)  # 只返回 2 个轨迹，None 行消失
```

**影响**：无 `trajectory_id` 的推理轨迹（真实数据中常见，尤其单链数据）被无声丢弃，样本量被低估。属**数据丢失缺陷**。

**修复**：把 `None` 键也纳入顺序（每行自成轨迹）：
```python
order = list(groups)  # 含 None 键；或在 to_*_rows 层为 None id 分配独立轨迹
```

---

### 缺陷 ③（MEDIUM）：CLI 无参数时抛裸 `TypeError`

**文件**：`lhr_tools/cli.py`（`_cmd_visualize` L158 + `_cmd_saturation` 类似分支）

**现象**：`visualize saturation` / `saturation` 命令既无 `--px` 也无 `--successes/--attempts` 时，`p_x = None` → `saturation_point(SaturationParams(None, ...))` 抛 `TypeError: '<' not supported between instances of 'float' and 'NoneType'`。

**复现**：
```python
main(['visualize', 'saturation'])  # TypeError（应提示"请提供 --px 或 --successes/--attempts"）
```

**影响**：UX 缺陷——用户收到难以理解的 `TypeError` 而非清晰错误信息。无测试覆盖。

**修复**：在 `p_x is None` 时提前 `raise ValueError("请提供 --px 或 --successes/--attempts")`，并补一个无参数测试。

---

## 设计/功能注记（非阻断）

### ④（LOW）B5 `generate_realistic` 未接入 CLI
`lhr_tools/io/generate.py` 的 `generate_realistic`/`generate_realistic_rows`（文献校准分布）只在 API 层可用；`dataset` CLI 命令未暴露 `--realistic` 参数。功能可及性缺口——用户需直接调 Python API。

### ⑤（INFO）`anchor._within` radius>0 对非 int 静默 no-op
`Trajectory._within` 对非整型状态在 `radius>0` 时返回 `False`（除非严格相等）——文档化限制（"cheap distance test for integer states"）。但 `compare_anchor` 传 `radius>0` + 字符串 steps 时，邻域检查被静默忽略，与 `radius=0` 行为相同。设计约束，非 bug；建议在文档中标注"radius>0 仅对整型状态有效"。

### ⑥（INFO）`to_verifier_rows` 语义混合
`importer.py` 的 `to_verifier_rows` 用模型自身 `confidence` 作为 verifier 的 `score`——但 `Verdict.score` 语义上是"验证器输出分数"（越高越合法）。当 `confidence` 是模型自评置信度而非验证器分时，AUC/AUPRC 的判别含义受限。文档/设计注记，非 bug。

---

## 优点（确认无问题）

- verifier 边缘行为全部正确：全 honest → AUC=0.5/AUPRC=0；全 exploit → AUC=0.5/AUPRC=1；Mann-Whitney 并列 0.5 权重。
- B5 credit accuracy 实测 [0.79, 0.89]，落在 TRCA 72%-96% 范围；verifier exploit_rate 落在 RHB [0, 0.138]；`generate_realistic` 确定性通过（同 seed 一致、异 seed 不同）。
- compare verifier 单文件路由正常；labels 数量不匹配抛清晰 ValueError；anchor 无输入抛清晰 ValueError。
- pipeline 空文件/单行 verifier 均正常返回（不崩溃）。
- 全套件 42/42 复核通过。
