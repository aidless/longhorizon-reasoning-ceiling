"""Real reasoning-trajectory importer (B6).

Converts raw reasoning-trajectory JSONL (each row = one reasoning step)
into the toolchain's per-metric row format so the metrics can run on
*real* model output rather than only synthetic data.

Expected input schema (one JSON object per line)::

    {
      "step_type": "hypothesis" | "check" | "conclusion",
      "is_correct": bool,
      "confidence": float,       # optional, [0, 1]
      "step_text": str           # optional, raw text
    }

Each logical *trajectory* is a run of consecutive steps; the importer
groups rows into trajectories by an optional ``trajectory_id`` field
(present → group by it; absent → every row is its own trajectory).
"""

from __future__ import annotations

from typing import Any

# Step-type → anchor encoding. A step is "anchored" (locks onto an
# incorrect candidate) when it is a hypothesis/check step that is wrong
# and is followed by more wrong steps of the same kind.
_ANCHOR_STEP_TYPES = ("hypothesis", "check")

_VERIFIER_SCORE_DEFAULT = 0.5  # when confidence is absent


def _group_by_trajectory(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group rows into trajectories.

    Uses ``trajectory_id`` when present; otherwise each row is its own
    single-step trajectory.
    """
    has_ids = any("trajectory_id" in r for r in rows)
    if not has_ids:
        return [[r] for r in rows]

    groups: dict[Any, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(r.get("trajectory_id"), []).append(r)
    # Preserve first-seen order. Rows with a NULL trajectory_id still form
    # their own single-row trajectory (they must NOT be dropped — see
    # v0.4 review ②). We sort by first-appearance index so None-keyed
    # groups interleave correctly with id-keyed ones.
    first_index: dict[Any, int] = {}
    for i, r in enumerate(rows):
        gid = r.get("trajectory_id")
        if gid not in first_index:
            first_index[gid] = i
    order = sorted(groups, key=lambda gid: first_index[gid])
    return [groups[gid] for gid in order]


def to_anchor_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw steps to ``anchor``-metric rows.

    Each trajectory becomes ``{"steps": [...], "correct": [...]}`` where
    steps are 0/1 (wrong/correct) and ``correct`` lists the indices of
    correct steps.
    """
    out: list[dict[str, Any]] = []
    for traj in _group_by_trajectory(rows):
        steps: list[int] = []
        correct: list[int] = []
        for i, r in enumerate(traj):
            is_correct = bool(r.get("is_correct", False))
            steps.append(1 if is_correct else 0)
            if is_correct:
                correct.append(i)
        out.append({"steps": steps, "correct": correct})
    return out


def to_credit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw steps to ``credit``-metric rows.

    Each step becomes ``{"pred": label, "truth": label}`` where the
    model's own prediction confidence over 0.5 maps to "positive",
    else "negative"; truth comes from ``is_correct``.
    """
    out: list[dict[str, Any]] = []
    for r in rows:
        conf = r.get("confidence", _VERIFIER_SCORE_DEFAULT)
        pred = "positive" if conf >= 0.5 else "negative"
        truth = "positive" if bool(r.get("is_correct", False)) else "negative"
        out.append({"pred": pred, "truth": truth})
    return out


def to_verifier_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw steps to ``verifier``-metric rows.

    A step is an "exploit" when it is a wrong hypothesis/check that the
    model nevertheless accepted as valid (confidence high but incorrect).
    ``accepted`` mirrors the model's confidence threshold.

    ``score`` should reflect the *verifier's* independent judgment, not
    the model's own self-assessment. When the input provides a
    ``verifier_score`` field (the genuine verifier signal), use it;
    otherwise fall back to ``confidence`` with a semantic note (v0.4
    review ⑥: self-confidence is a proxy, not a verifier score).
    """
    out: list[dict[str, Any]] = []
    for r in rows:
        conf = r.get("confidence", _VERIFIER_SCORE_DEFAULT)
        is_correct = bool(r.get("is_correct", False))
        step_type = str(r.get("step_type", ""))
        is_exploit = (not is_correct) and (step_type in _ANCHOR_STEP_TYPES)
        accepted = conf >= 0.5
        # Prefer the verifier's own score when present; else fall back to
        # self-confidence (proxy).
        score = r.get("verifier_score", conf)
        out.append({"is_exploit": is_exploit, "accepted": accepted,
                    "score": float(score)})
    return out


# Metric → converter dispatch.
CONVERTERS = {
    "anchor": to_anchor_rows,
    "credit": to_credit_rows,
    "verifier": to_verifier_rows,
}


def import_trajectory(metric: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw reasoning steps to the given metric's row format.

    ``metric`` must be one of ``anchor`` / ``credit`` / ``verifier``.
    """
    conv = CONVERTERS.get(metric)
    if conv is None:
        raise ValueError(f"unknown metric: {metric}")
    return conv(rows)
