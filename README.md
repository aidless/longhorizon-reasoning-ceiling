# Long-Horizon Reasoning Evaluation Toolchain

[![CI](https://github.com/aidless/longhorizon-reasoning-ceiling/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/longhorizon-reasoning-ceiling/actions/workflows/ci.yml)

> **English TL;DR**: An engineering toolchain for measuring the long-horizon reasoning ceiling: anchor rate, saturation points, credit assignment, verifier robustness, trajectory diagnostics, and calibration metrics, each mapped to cited literature. Install the `lhr-tools` Python package with `pip install -e .` and drive it through a 13-command CLI (`lhr-tools --help`). An independent-researcher project with no institutional affiliation, it aims for reproducible, zero-dependency, verifiable evaluation rather than a paper claim.

评估长程推理能力天花板（long-horizon reasoning ceiling）的工程级工具链：锚定率、饱和点、credit assignment、验证器鲁棒性、轨迹级诊断与校准指标。

> 独立研究者项目，无机构隶属。目标从论文转向工程架构：提供可复现、零依赖、可校验的评估工具。

## 项目结构

```
longhorizon-reasoning-ceiling/
├── RESEARCH_PLAN.md          # 研究计划（假设 H1-H3 + 实验 E1-E3 + 文献）
├── tools/                    # lhr-tools 工具链（Python 包）
│   ├── lhr_tools/
│   │   ├── metrics/          # 指标模块：anchor / saturation / credit / verifier / trajectory / calibration
│   │   ├── io/               # 数据：generate / importer / jsonl / schema
│   │   ├── services/         # 服务：pipeline / reporter / visualize / compare / config
│   │   └── cli.py            # CLI 入口（13 命令）
│   ├── tests/                # 测试（69/69 通过）
│   ├── docs/API.md           # API 参考
│   └── README.md             # 工具链使用说明
├── experiments/              # 实验设计（E1-E3）
└── analyses/                 # 分析输出
```

## 快速开始

```bash
cd tools
pip install -e .
mkdir -p data                                    # dataset 的 --output 不会自动建目录
lhr-tools --help
lhr-tools dataset anchor --n 10 --seed 42 --output data/anchor.jsonl
lhr-tools saturation --px 0.3 --fmax 0.95 --eps 0.01
lhr-tools dataset verifier --n 10 --seed 42 --output data/verifier.jsonl
lhr-tools verifier data/verifier.jsonl          # verifier 收位置参数，不接受 --input
lhr-tools anchor data/anchor.jsonl > data/anchor.json
lhr-tools report data/anchor.json --output ../analyses/lhr-report.md   # report 收位置参数（一个或多个结果 JSON）
```

两处容易踩坑的写法：`verifier` 和 `report` 的输入文件都是**位置参数**（`report` 可接多个结果 JSON）；`dataset --output` 指向的目录必须先存在，否则报 `FileNotFoundError`。

Quickstart 实测（2026-11-10，真实输出节选；本机 pip 受 PEP 668 限制，
用 `PYTHONPATH=tools python3 -m lhr_tools.cli` 等价运行）：

```text
$ lhr-tools saturation --px 0.3 --fmax 0.95 --eps 0.01
{
  "metric": "saturation_point",
  "N_star": 17,
  "p_x": 0.3,
  "f_max": 0.95,
  "eps": 0.01,
  "pass_at_1": 0.30000000000000004,
  "pass_at_4": 0.7599,
  ...
}

$ lhr-tools dataset anchor --n 10 --seed 42 --output data/anchor.jsonl
已生成 10 行 → data/anchor.jsonl

$ lhr-tools anchor data/anchor.jsonl
{
  "value": 0.5,
  "n_anchored": 5,
  "anchored_indices": [1, 2, 6, 7, 8],
  "metric": "anchor",
  "n": 10,
  ...
}
```

## Results（实验状态与已有结果）

### 工具链验证（真实跑过）

| 检查 | 命令 | 实测结果（2026-11-10） |
|---|---|---|
| 单元测试 | `python3 -m pytest tests/ -q`（在 `tools/`） | **69 passed in 1.60s**（0 失败） |
| CLI 自检 | `lhr-tools selftest` | 13 命令齐备（`--help` 实测列出 anchor/saturation/credit/verifier/dataset/report/visualize/compare/config/import/trajectory/calibration/selftest） |
| saturation 数值例 | `lhr-tools saturation --px 0.3 --fmax 0.95 --eps 0.01` | N*=17, pass@1=0.30, pass@4=0.7599 |
| anchor 数值例 | `lhr-tools anchor data/anchor.jsonl`（seed 42 生成 10 行） | value=0.5, n_anchored=5 |

### 示例报告（已有）

`analyses/lhr-report.md` 是**工具链演示报告**（`lhr-tools report` 的输出样例）：
锚定率 value=0.5000，n=2，数据源为合成 demo 文件——它验证的是 report 链路，
**不是**真实模型实验结果。

### 实验执行状态（诚实标注）

| 实验 | 假设 | 状态 | 结果 |
|---|---|---|---|
| E1 锚定-算力解耦 | H1（TTSPM/FALCA/ParaThinker 依据） | **细化完成，未执行**（2026-11-01） | **NOT YET MEASURED**：`experiments/E1-anchor-compute/` 只有 `design.md`，无结果文件。未执行原因：需要 5 基准 × 908 题的模型推理算力（小模型扫曲面 + 大模型验证格），按本工作区纪律实验须上云，尚未排期执行 |
| E2 步级验证注入 | H2 | **细化完成，未执行** | **NOT YET MEASURED**（四臂设计已在 `design.md` 定稿，无运行日志） |
| E3 验证器对抗鲁棒性 | H3 | **细化完成，未执行** | **NOT YET MEASURED**（三类验证器设计定稿，无运行日志） |

因此：本仓库目前**不携带任何真实模型实验数字**；全部可验证的数字是工具链
测试与合成数据的指标示例（上表），所有真实实验数字待 E1–E3 执行后补录。

## What this doesn't claim / Limits

- **不声明任何论文级结论**：目标是可复现、零依赖、可校验的评估工具链，不是实证 claim。
- 指标概览表中的文献（TTSPM、PURE、RHB 等）映射的是**指标的出处**，不是「本工具已在对应文献设置下复现其结果」。
- E1–E3 已设计未执行；在结果落盘前，任何引用本仓的说法应限定为「工具链 + 实验设计」。
- `analyses/lhr-report.md` 为合成数据演示，勿当作实验证据引用。

## 指标概览

| 类别 | 指标 | 文献来源 |
|------|------|---------|
| 锚定 | `anchor_rate` / `anchored_ids` | 误差锚定假说 |
| 饱和 | `saturation_point` / `pass_at_k` / `estimate_px` / `bootstrap_nstar_ci` | TTSPM (arXiv:2505.20522) |
| Credit | `cohens_kappa` / `credit_precision` / `min_form_credit` | PURE (arXiv:2504.15275) |
| 验证器 | `false_accept_rate` / `false_reject_rate` / `auc_roc` / `auprc` / `pattern_robustness_profile` | RHB / HARVE |
| 轨迹 | `per_step_reliability` / `geometric_ceiling` / `snowball_rate` / `context_drag` | arXiv:2609.01660 / CART |
| 校准 | `expected_calibration_error` / `brier_score` / `confidence_margin` | VL-Cal / SLATE |

## 开发

```bash
cd tools
python3 -m pytest tests/ -q   # 全套件 69/69
lhr-tools selftest            # 模块自检（RED→GREEN）
```

## 许可

MIT License。详见 [LICENSE](LICENSE)。

## U1 live recompute (executed 2026-11-11)

The values below come from executing the toolchain in this repository during
this pass; they are synthetic/demo computations, **not** model experiment
results.

| Live check | Value | Source |
|---|---|---|
| `saturation` N* | 17 | live `PYTHONPATH=tools python3 -m lhr_tools.cli saturation --px 0.3 --fmax 0.95 --eps 0.01` |
| `p_x` / `f_max` / `eps` | 0.3 / 0.95 / 0.01 | same JSON output |
| `pass_at_1` | 0.30000000000000004 | same |
| `pass_at_4` | 0.7599 | same |
| `pass_at_8` | 0.94235199 | same |
| `pass_at_16` | 0.9966767069430399 | same |
| `pass_at_32` | 0.9999889557232575 | same |
| `anchor` value / n_anchored / n | 0.5 / 5 / 10 | live `dataset anchor --n 10 --seed 42` + `anchor <file>` |
| Toolchain unit tests | **69 passed in 1.16s** | live `python3 -m pytest tests/ -q` in `tools/` (exit 0) |

Experiment inventory (checked on disk this pass):

| Experiment dir | Contents | Status |
|---|---|---|
| `E1-anchor-compute` | 1 file(s), all design/notes | **NOT YET MEASURED** |
| `E2-step-verification` | 1 file(s), all design/notes | **NOT YET MEASURED** |
| `E3-verifier-robustness` | 1 file(s), all design/notes | **NOT YET MEASURED** |

**NOT YET MEASURED**: E1 anchor-compute decoupling, E2 step-level verification,
and E3 verifier robustness. The directories above contain design documents and
no result files; the existing "实验执行状态（诚实标注）" table above is
unchanged. Reproduce the toolchain numbers (no model, no network):

```bash
PYTHONPATH=tools python3 -m lhr_tools.cli saturation --px 0.3 --fmax 0.95 --eps 0.01
PYTHONPATH=tools python3 -m lhr_tools.cli dataset anchor --n 10 --seed 42 --output data/anchor.jsonl
PYTHONPATH=tools python3 -m lhr_tools.cli anchor data/anchor.jsonl
cd tools && python3 -m pytest tests/ -q
```

<!-- figure: pending real measurement -->
