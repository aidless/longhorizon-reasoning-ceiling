# Long-Horizon Reasoning Evaluation Toolchain

[![CI](https://github.com/aidless/longhorizon-reasoning-ceiling/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/longhorizon-reasoning-ceiling/actions/workflows/ci.yml)

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
