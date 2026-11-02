# lhr_tools — 长程推理评估工具链（工程架构）

## 项目定位

这是一个**工程架构**项目，不是论文写作项目。目标是把「长程推理评估」做成
一个独立、可运行、可扩展、可复用的工程，具备清晰的模块分层、配置系统、
数据流、命令树、测试与 CI。

## 架构分层

```
┌─────────────────────────────────────────────────────────┐
│  CLI 层   bin/lhr-tools  lhr_tools/cli.py               │
│  （命令树：anchor / saturation / credit / verifier /    │
│    dataset / report / config / selftest）               │
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

> **注意**：`saturation` 是唯一的**参数驱动**指标——它从 `--px`/`--fmax`/`--eps`
> 直接计算 N*，不读取 JSONL 数据文件。其余三个指标（anchor/credit/verifier）
> 均为数据驱动，走上面的完整数据流。

## 命令树

```
lhr-tools
├── anchor        # 锚定率（FALCA）— 数据驱动
├── saturation    # 饱和点 N*（TTSPM Eq.14）— 参数驱动
├── credit        # 早期步 credit 精度（Cohen's κ）— 数据驱动
├── verifier      # 验证器鲁棒性（RHB）— 数据驱动
├── trajectory    # 轨迹级诊断（C1，v0.5）— 数据驱动
├── calibration   # 验证器/预测器校准（C2，v0.5）— 数据驱动
├── dataset       # 数据集生成/管理（AIME / MATH-500 / 合成）
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
├── pyproject.toml          # 打包配置（console 脚本，v0.5.0）
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
3. **零第三方依赖**：核心测量只用标准库；配置层可选 PyYAML（未装则回退 JSON）。
4. **RED→GREEN 测试**：每个测量函数既有「违规必须红」也有「合规必须绿」的断言。
5. **配置优先**：所有可调参数走配置，不硬编码；CLI 参数可覆盖配置。

## CI

GitHub Actions 工作流 `.github/workflows/ci.yml` 在 push/PR 时自动运行：
- 3 个 Python 版本（3.10 / 3.11 / 3.12）矩阵
- 全套件测试（metrics / io / cli 三套 + selftest）
- CLI 入口冒烟（`lhr-tools --help` / `config --show` / `saturation --px`）

## 快速开始

```bash
cd tools
python3 -m lhr_tools.cli selftest       # 自检（RED→GREEN 7 模块）
python3 -m lhr_tools.cli config --show  # 查看配置
python3 -m lhr_tools.cli dataset anchor --n 10 --seed 42 --output data/anchor.jsonl
python3 -m lhr_tools.cli dataset verifier --n 100 --seed 7 --realistic --output data/verifier.jsonl  # B5 文献校准分布
python3 -m lhr_tools.cli anchor data/anchor.jsonl
python3 -m lhr_tools.cli saturation --px 0.5 --fmax 0.9   # 参数驱动
python3 -m lhr_tools.cli verifier data/verifier.jsonl
python3 -m lhr_tools.cli trajectory data/trajectory.jsonl  # C1 轨迹诊断
python3 -m lhr_tools.cli calibration data/calibration.jsonl # C2 校准
```

生成的数据文件（`data/anchor.jsonl`）可直接喂给 `anchor` 命令。`saturation`
不需要数据文件，直接给 `--px` 即可。
