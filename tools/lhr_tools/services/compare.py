"""Cross-configuration comparison (A3).

Runs a metric across multiple configurations (parameter sets) and returns
a comparison table. This supports the E1 ANCOVA design where we sweep
N × P and compare saturation points.

Supported comparison modes:
  - anchor   : vary (frac, radius) over the same trajectory data
  - verifier : vary nothing (scores fixed) — compare across datasets
  - saturation: vary (p_x, f_max) and compare N*
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CompareConfig:
    """One configuration row in a comparison."""
    label: str
    params: dict[str, Any] = field(default_factory=dict)


def compare_anchor(data_path: str | Path,
                   configs: list[CompareConfig]) -> list[dict[str, Any]]:
    """Compute anchor rate for each (frac, radius) configuration."""
    from lhr_tools.io.jsonl import read_jsonl
    from lhr_tools.io.schema import validate_rows
    from lhr_tools.metrics.anchor import Trajectory, anchor_rate, anchored_ids

    rows = read_jsonl(data_path)
    errors = validate_rows("anchor", rows)
    if errors:
        raise ValueError(f"schema validation failed: {errors[:3]}...")

    results = []
    for cfg in configs:
        frac = cfg.params.get("frac", 0.20)
        radius = cfg.params.get("radius", 0)
        trajs = [Trajectory(r["steps"], frozenset(r.get("correct", [])),
                            anchor_fraction=frac, neighbourhood_radius=radius)
                 for r in rows]
        ids = anchored_ids(trajs)
        results.append({
            "label": cfg.label,
            "frac": frac,
            "radius": radius,
            "anchor_rate": anchor_rate(trajs),
            "n_anchored": len(ids),
            "n_total": len(rows),
        })
    return results


def compare_saturation(configs: list[CompareConfig]) -> list[dict[str, Any]]:
    """Compute N* for each (p_x, f_max) configuration."""
    from lhr_tools.metrics.saturation import SaturationParams, saturation_point

    results = []
    for cfg in configs:
        p_x = cfg.params.get("p_x", 0.5)
        f_max = cfg.params.get("f_max", 0.9)
        eps = cfg.params.get("eps", 0.01)
        n_star = saturation_point(SaturationParams(p_x, f_max, eps))
        results.append({
            "label": cfg.label,
            "p_x": p_x,
            "f_max": f_max,
            "eps": eps,
            "N_star": n_star,
        })
    return results


def compare_verifier(data_paths: list[str | Path],
                     labels: list[str]) -> list[dict[str, Any]]:
    """Compare verifier robustness across multiple datasets."""
    from lhr_tools.io.jsonl import read_jsonl
    from lhr_tools.io.schema import validate_rows
    from lhr_tools.metrics.verifier import Verdict, false_accept_rate, false_reject_rate, auc_roc, auprc

    if len(data_paths) != len(labels):
        raise ValueError("data_paths and labels must have equal length")

    results = []
    for path, label in zip(data_paths, labels):
        rows = read_jsonl(path)
        errors = validate_rows("verifier", rows)
        if errors:
            raise ValueError(f"schema validation failed for {label}: {errors[:3]}...")
        verdicts = [Verdict(bool(r["is_exploit"]), bool(r["accepted"]),
                            float(r["score"])) for r in rows]
        results.append({
            "label": label,
            "false_accept_rate": false_accept_rate(verdicts),
            "false_reject_rate": false_reject_rate(verdicts),
            "auc_roc": auc_roc(verdicts),
            "auprc": auprc(verdicts),
            "n": len(rows),
        })
    return results


def format_comparison(rows: list[dict[str, Any]]) -> str:
    """Render comparison results as a Markdown table."""
    if not rows:
        return "(无对比结果)"

    # Column order: label first, then metric columns.
    metric_cols = [k for k in rows[0] if k != "label"]
    lines = ["| " + " | ".join(["label"] + metric_cols) + " |",
             "|" + "---|" * (len(metric_cols) + 1)]
    for r in rows:
        cells = [str(r.get("label", "?"))]
        for col in metric_cols:
            v = r.get(col, "")
            if isinstance(v, float):
                cells.append(f"{v:.4f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------
# Self-test (RED → GREEN).
# ---------------------------------------------------------------------
def _selftest() -> None:
    # RED→GREEN: saturation comparison produces rows in label order.
    cfg = [CompareConfig("A", {"p_x": 0.3, "f_max": 0.9}),
           CompareConfig("B", {"p_x": 0.7, "f_max": 0.9})]
    rows = compare_saturation(cfg)
    assert len(rows) == 2
    assert rows[0]["label"] == "A" and rows[1]["label"] == "B"
    assert rows[0]["N_star"] > rows[1]["N_star"], "higher p_x should saturate sooner"
    # GREEN: format produces a valid Markdown table.
    md = format_comparison(rows)
    assert md.startswith("| label") and "---|" in md
    print("compare selftest OK")


if __name__ == "__main__":
    _selftest()
