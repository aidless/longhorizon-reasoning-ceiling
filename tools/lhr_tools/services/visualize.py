"""Visualization for lhr_tools (A2).

Renders metric outputs as plots. Uses matplotlib when available and
falls back to ASCII/text rendering otherwise (keeps the toolchain
zero-dependency in constrained environments).

Supported plots:
  - saturation_curve  : pass@k vs k, with the saturation point N* marked
  - anchor_dist       : histogram of first-anchored-step distribution
  - roc_curve         : verifier ROC curve (exploit detection)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _try_import_matplotlib():
    """Return the pyplot module, or None if unavailable."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        return None


def saturation_curve(p_x: float, f_max: float, eps: float = 0.01,
                     k_max: int = 64, n_star: int | None = None,
                     output: str | Path | None = None) -> str:
    """Render pass@k vs k with the saturation point marked.

    Returns the path to the saved PNG when matplotlib is available,
    or an ASCII chart string otherwise.
    """
    from lhr_tools.metrics.saturation import pass_at_k

    ks = list(range(1, k_max + 1))
    vals = [pass_at_k(p_x, k) for k in ks]

    plt = _try_import_matplotlib()
    if plt is not None:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(ks, vals, marker="o", markersize=3, linewidth=2, label=f"pass@k (p_x={p_x})")
        if n_star is not None:
            ax.axvline(n_star, color="red", linestyle="--", label=f"N*={n_star}")
        ax.axhline(f_max, color="green", linestyle=":", label=f"F_max={f_max}")
        ax.set_xlabel("attempts k")
        ax.set_ylabel("pass@k")
        ax.set_title("Saturation curve (TTSPM)")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        if output is None:
            output = "saturation_curve.png"
        fig.savefig(output, dpi=150)
        plt.close(fig)
        return str(output)

    # ASCII fallback: render the curve compactly.
    lines = [f"pass@k (p_x={p_x}, F_max={f_max})", ""]
    for k in ks:
        bar = "#" * int(vals[k - 1] * 50)
        marker = " ← N*" if n_star is not None and k == n_star else ""
        lines.append(f"{k:3d} | {bar} {vals[k - 1]:.3f}{marker}")
    return "\n".join(lines)


def anchor_dist(anchored_steps: list[int], output: str | Path | None = None) -> str:
    """Render histogram of first-anchored-step distribution.

    `anchored_steps` is a list of step indices where anchoring occurred.
    """
    if not anchored_steps:
        return "(无锚定样本)"

    plt = _try_import_matplotlib()
    if plt is not None:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(anchored_steps, bins=max(1, min(20, len(set(anchored_steps)))))
        ax.set_xlabel("first-anchored step")
        ax.set_ylabel("count")
        ax.set_title("Anchoring step distribution")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        if output is None:
            output = "anchor_dist.png"
        fig.savefig(output, dpi=150)
        plt.close(fig)
        return str(output)

    # ASCII fallback.
    from collections import Counter
    cnt = Counter(anchored_steps)
    lines = ["anchored-step distribution", ""]
    for step in sorted(cnt):
        bar = "#" * cnt[step]
        lines.append(f"step {step}: {bar} {cnt[step]}")
    return "\n".join(lines)


def roc_curve(verdicts: list[Any], output: str | Path | None = None) -> str:
    """Render the verifier ROC curve.

    `verdicts` is a list of Verdict objects with (is_exploit, accepted, score).
    Computes the empirical ROC from the scores.
    """
    if not verdicts:
        return "(无样本)"

    # Sort by descending score; sweep the decision threshold.
    scored = sorted(verdicts, key=lambda v: v.score, reverse=True)
    n_pos = sum(1 for v in scored if v.is_exploit)
    n_neg = len(scored) - n_pos
    if n_pos == 0 or n_neg == 0:
        return "(单类样本，无法绘制 ROC)"

    tprs: list[float] = [0.0]
    fprs: list[float] = [0.0]
    tp = fp = 0
    for v in scored:
        if v.is_exploit:
            tp += 1
        else:
            fp += 1
        tprs.append(tp / n_pos)
        fprs.append(fp / n_neg)
    tprs.append(1.0)
    fprs.append(1.0)

    plt = _try_import_matplotlib()
    if plt is not None:
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot(fprs, tprs, marker="o", markersize=2, linewidth=2, label="ROC")
        ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="chance")
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        ax.set_title("Verifier ROC")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        if output is None:
            output = "roc_curve.png"
        fig.savefig(output, dpi=150)
        plt.close(fig)
        return str(output)

    # ASCII fallback.
    lines = ["verifier ROC", "", "FPR    TPR"]
    for f, t in zip(fprs, tprs):
        lines.append(f"{f:.3f}  {t:.3f}")
    return "\n".join(lines)


def render(metric: str, result: dict[str, Any], output: str | Path | None = None) -> str:
    """Dispatch visualization by metric name.

    Returns the output path (PNG) or ASCII string.
    """
    if metric == "saturation":
        return saturation_curve(
            result["p_x"], result["f_max"], result.get("eps", 0.01),
            n_star=result.get("N_star"), output=output)
    if metric == "anchor":
        return anchor_dist(result.get("anchored_indices", []), output=output)
    if metric == "verifier":
        # result carries aggregate stats, not raw verdicts; ROC needs raw data.
        raise ValueError("verifier ROC 需要原始 verdict 数据，请用 dataset 生成后直接绘制")
    raise ValueError(f"unknown visualization metric: {metric}")


# ---------------------------------------------------------------------
# Self-test (RED → GREEN).
# ---------------------------------------------------------------------
def _selftest() -> None:
    # RED→GREEN: saturation_curve produces output for valid params.
    out = saturation_curve(0.3, 0.9, k_max=8, n_star=4)
    assert out, "saturation_curve returned empty"
    # GREEN: anchor_dist handles empty input gracefully.
    assert anchor_dist([]) == "(无锚定样本)"
    print("visualize selftest OK")


if __name__ == "__main__":
    _selftest()
