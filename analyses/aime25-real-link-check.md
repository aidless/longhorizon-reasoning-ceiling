# E1 最小链路验证报告（lhr_tools 端到端）

> 目的：证明 lhr_tools 的 **import → anchor → trajectory → report** 测量链路能端到端跑通。
> 本验证**不构成 H1 的科学检验**——只用模型自身 boxed 答案做自洽基准（官方答案不可得），且未跑新推理（复用现成轨迹）。

## 1. 数据

- 数据源：`llama.cpp-src/benches/dgx-spark/aime25_openai__gpt-oss-120b-high_temp1.0_20251109_094547_allresults.json`
- 提取：30 道唯一 AIME 2025 题 + 240 条完整推理轨迹（gpt-oss-120b，high temp）
- 桥脚本：`tools/bin/cot_to_steps.py`（CoT 按 \n\n 切步，step_type 启发式，is_correct 用模型 boxed 自洽基准）
- 切步结果：**7961 步** / 240 轨迹，平均 33.2 步/轨迹（min 1 / max 60 / median 33）

## 2. 链路各环节结果

| 环节 | 命令 | 结果 |
|---|---|---|
| import | `import anchor` | 240 行 anchor rows |
| anchor | `anchor` | **anchor_rate = 0.0**（0/240） |
| trajectory | `trajectory` | 240 轨迹（见下） |
| report | `report` | analyses/aime25-real-link-check.md |

## 3. trajectory 指标

| 指标 | 值 |
|---|---|
| mean_per_step_reliability | **0.9336** |
| snowball_rate | **0.8167** |
| mean_context_drag | **0.3020** |

## 4. step_type 分布与正确率

| step_type | 步数 | 正确率 |
|---|---|---|
| hypothesis | 3948 | 0.3% |
| check | 3738 | 7.4% |
| conclusion | 275 | 87.6% |

末步（最终答案）对：**234/240 = 97.5%**

## 5. 诚实边界（必须声明的局限）

1. **anchor_rate = 0.0 是假象**：is_correct 用模型自身 boxed 答案做自洽基准，模型 92.5% 给 boxed 且众数稳定 → 几乎每步判"对" → 无错误步 → 无锚定可测。这不是科学锚定测量。
2. **未跑新推理**：复用 gpt-oss 现成轨迹，未调用 ollama/GPU 生成，不构成"模型扫描曲面"的完整 E1。
3. **官方答案不可得**：HF 网络不通（AIME 题目下载失败），只能用模型自洽基准，不能对齐 TTSPM Table 1 的绝对准确率。
4. **is_correct 判据粗糙**：`extract_boxed` 只取最后一个 \boxed，步级正确性 = 该步是否含最终答案（非步级数学正确性）。

## 6. 结论

**链路能跑通**：import → anchor → trajectory → report 全部端到端执行，指标可复算。
**但 H1 未检验**：anchor=0 是自洽基准的假象，须换官方答案 + 真实模型推理（E1 完整版）才能得出科学结论。

## 7. 下一步（若要推进 H1）

1. 获取 AIME 官方答案（HF 网络恢复 / 手工录入 30 题答案）
2. 用 ollama qwen2.5 在 CPU 上跑小规模 N∈{1,4} 初步扫描（非 GPU 完整版）
3. 对齐 TTSPM Table 1 的绝对准确率验证校准
