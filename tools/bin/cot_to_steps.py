"""CoT 推理轨迹 → lhr_tools step rows 桥（最小链路验证）。

把 AIME 真实模型推理轨迹的 CoT 文本解析成 lhr_tools 的 raw step rows
（step_type / is_correct / confidence / step_text），供 import → anchor 链路。

步切分：CoT 按 \\n\\n 段落切分，每非空段 = 1 步。
step_type：含 \\boxed → conclusion；含 = 或 数学环境 → check；else → hypothesis。
is_correct：链路验证粒度——用该轨迹最终 boxed 答案 vs 该步是否含最终答案。
  （官方答案不可得时用模型自身 boxed 做自洽基准；换官方答案后重跑即可。）
"""
from __future__ import annotations
import json, re, sys, os

def split_steps(cot: str) -> list[str]:
    paras = [p.strip() for p in re.split(r'\n\n+', cot) if p.strip()]
    return paras

def classify(step: str) -> str:
    if '\\boxed' in step or 'boxed{' in step:
        return 'conclusion'
    if re.search(r'[=]|\\begin\{|\\\[', step):
        return 'check'
    return 'hypothesis'

def extract_boxed(cot: str) -> str | None:
    m = re.findall(r'\\boxed\{([^}]*)\}', cot)
    return m[-1] if m else None

def cot_to_rows(cot: str, traj_id: str) -> list[dict]:
    steps = split_steps(cot)
    final_ans = extract_boxed(cot)
    rows = []
    for i, st in enumerate(steps):
        stype = classify(st)
        # is_correct：该步是否含最终答案（自洽基准）；conclusion 步用 boxed 匹配
        if stype == 'conclusion' and final_ans:
            is_correct = (final_ans in st) or (extract_boxed(st) == final_ans)
        else:
            is_correct = bool(final_ans) and (final_ans in st)
        rows.append({
            'step_type': stype,
            'is_correct': is_correct,
            'confidence': 0.8 if is_correct else 0.5,
            'step_text': st,
            'trajectory_id': traj_id,
        })
    return rows

def main():
    if len(sys.argv) < 3:
        print('用法: cot_to_steps.py <trajectories.jsonl> <out_steprows.jsonl>')
        sys.exit(1)
    inp, outp = sys.argv[1], sys.argv[2]
    out_rows = []
    with open(inp) as f:
        for line in f:
            r = json.loads(line)
            tid = f"aime25-t{r['convo_idx']}"
            rows = cot_to_rows(r['a'], tid)
            out_rows.extend(rows)
    with open(outp, 'w') as f:
        for row in out_rows:
            f.write(json.dumps(row) + '\n')
    print(f'桥接完成: {len(out_rows)} 步 / {len(out_rows)} rows → {outp}')

if __name__ == '__main__':
    main()
