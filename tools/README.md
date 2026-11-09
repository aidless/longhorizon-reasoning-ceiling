# lhr_tools — 长程推理评估工具链（工程架构）

STATUS: WORK-IN-PROGRESS — not A yet. package version 0.5.1. 13 CLI commands. 72/72 pytest tests, checked by `tests/test_drift.py`. This package runs synthetic JSONL and scalar parameters. It does not report a measured ceiling on a live model. See the repository `FAILURE_MODES.md`.

## 项目定位

这是指标管线，不是论文结论，也不是实模型评测。分层、配置、命令和测试都在这个目录里。合成数据与实模型评估是两条路：`tests/data/` 和 `dataset` 属于前者；本仓库没有后者的记录。

## 架构分层

```
┌─────────────────────────────────────────────────────────┐
│  CLI 层   bin/lhr-tools  lhr_tools/cli.py               │
│  （13 CLI commands，见下方命令树）                        │
├─────────────────────────────────────────────────────────┤
│  服务层   lhr_tools/services/                           │
│  （编排：加载配置 → 读取数据 → 调用测量 → 生成报告）     │
├─────────────────────────────────────────────────────────┤
│  测量层   lhr_tools/metrics/                            │
│  （纯函数：anchor.py / saturation.py / credit.py /      │
│    verifier.py —— 确定性、无 IO、可测试）               │
├─────────────────────────────────────────────────────────┤
│  数据层   lhr_tools/io/                                 │
│  （JSONL / JSON 读写、schema 校验、数据生成）           │
├─────────────────────────────────────────────────────────┤
│  配置层   lhr_tools/config/                             │
│  （YAML/JSON 配置加载、默认值、环境变量覆盖）           │
└─────────────────────────────────────────────────────────┘
```

## 数据流

```
config.yaml ──→ Config.load() ──→ 服务层编排
                                    │
dataset.jsonl ──→ IO.read_jsonl() ──→ schema 校验
                                    │
                    metrics.*.compute()  ← 纯函数，无 IO
                                    │
result.json ──→ report.md
```

> **注意**：`saturation` 是**参数驱动**的。它从 `--px` / `--fmax` / `--eps` 计算本地 N*，不读 JSONL。本地表达式不是 TTSPM Eq. (14)，见 `FAILURE_MODES.md`。`anchor` / `credit` / `verifier` / `trajectory` / `calibration` 读 JSONL。

## 命令树

```
lhr-tools
├── anchor        # 锚定率（FALCA）— 数据驱动
├── saturation    # 本地 N*（不是 TTSPM Eq. 14）— 参数驱动
├── credit        # 早期步 credit 精度（Cohen's κ）— 数据驱动
├── verifier      # 验证器鲁棒性（RHB）— 数据驱动
├── trajectory    # 轨迹级诊断（C1，v0.5）— 数据驱动
├── calibration   # 验证器/预测器校准（C2，v0.5）— 数据驱动
├── dataset       # 合成 JSONL（不是 AIME / MATH-500 下载）
├── report        # 报告生成（md）
├── config        # 配置查看/校验
├── visualize     # 指标输出图
├── compare       # 跨配置批量对比表
├── import        # 原始推理轨迹 JSONL → 指标行 JSONL
└── selftest      # 全部模块自检（RED→GREEN）
```

## 目录结构

```
tools/
├── pyproject.toml          # 打包配置（package version 0.5.1）
├── README.md               # 本文档
├── lhr_tools/
│   ├── __init__.py
│   ├── cli.py              # 命令树入口
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py       # YAML/JSON 配置加载
│   │   └── default.yaml    # 默认配置
│   ├── io/
│   │   ├── __init__.py
│   │   ├── jsonl.py        # JSONL 读写
│   │   ├── schema.py       # schema 校验
│   │   ├── generate.py     # 数据集生成
│   │   └── importer.py     # 轨迹导入（B6）
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── anchor.py       # 锚定率
│   │   ├── saturation.py   # 饱和点 + 缩放律
│   │   ├── credit.py       # credit 精度 + min-form
│   │   ├── verifier.py     # 验证器鲁棒性 + HARVE 模式
│   │   ├── trajectory.py   # 轨迹级诊断（C1）
│   │   └── calibration.py  # 校准指标（C2）
│   └── services/
│       ├── __init__.py
│       ├── pipeline.py     # 测量管线编排
│       ├── reporter.py     # 报告生成
│       ├── visualize.py    # 绘图
│       └── compare.py      # 跨配置对比
├── bin/
│   └── lhr-tools           # 独立可执行
└── tests/
    ├── data/               # 测试数据
    ├── test_metrics.py     # 测量层测试
    ├── test_io.py          # 数据层测试
    └── test_cli.py         # CLI 测试
```

## 设计原则

1. **测量层纯函数**：`metrics/` 下的函数无 IO、无副作用，输入输出可预测，
   便于单测与属性测试。
2. **确定性**：相同输入 → 相同输出，无随机状态（随机仅限数据生成器，且种子固定）。
3. **依赖写在打包元数据里**：测量函数只用标准库。安装本包会拉取 PyYAML（读 YAML 配置）。matplotlib 可选，缺它时绘图退回 ASCII。pytest 只用于测试。
4. **RED→GREEN 测试**：每个测量函数既有「违规必须红」也有「合规必须绿」的断言。
5. **配置优先**：所有可调参数走配置，不硬编码；CLI 参数可覆盖配置。

## CI

GitHub Actions 工作流 `.github/workflows/ci.yml` 在 `tools/**`、根 `README.md`、`FAILURE_MODES.md` 或工作流自身变更时运行：
- Python 3.10 / 3.11 / 3.12
- `pip install -e ".[dev,viz]"` 后 `python -m pytest tests/ -q`
- `lhr-tools selftest`
- fixture 冒烟：`tests/data/` 里的 anchor、credit、verifier，外加 `saturation --px 0.3 --fmax 0.9 --eps 0.01`

## 快速开始

仓库根 README 写了从干净克隆安装并跑 pytest 的命令。下面是已提交的合成 fixture，不是模型输出：

```bash
cd tools
python3 -m lhr_tools.cli selftest
python3 -m lhr_tools.cli anchor tests/data/anchor.jsonl
python3 -m lhr_tools.cli credit tests/data/credit.jsonl
python3 -m lhr_tools.cli verifier tests/data/verifier.jsonl
python3 -m lhr_tools.cli saturation --px 0.3 --fmax 0.9 --eps 0.01
```

`dataset` 另写一批合成行。输出目录必须已经存在。`--realistic` 只是改用 `io/generate.py` 里写下的数值区间，仍然是合成数据。

`trajectory` 和 `calibration` 没有提交 fixture。它们的输入分别是 `{steps: [0/1, ...]}` 和 `{confidence, outcome}` 的 JSONL。不要把缺文件的路径当成已经跑过的评测。
