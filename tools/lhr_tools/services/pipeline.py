"""Pipeline orchestration.

Loads config → reads data → validates schema → dispatches to a metric
function → returns a structured result dict. This is the service layer:
it wires the other layers together without being a CLI itself.

Note: `saturation` is parameter-driven. It derives a local N* from
p_x/f_max/eps rather than from a JSONL file, and that expression is not
TTSPM Eq. (14). `_run_saturation` raises ValueError so callers use
`lhr_tools.cli._cmd_saturation`. anchor, credit, and verifier are the
data-driven metrics this pipeline dispatches. trajectory and calibration
are computed from JSONL in the CLI, not here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lhr_tools.config.loader import Config
from lhr_tools.io.jsonl import read_jsonl
from lhr_tools.io.schema import validate_rows
from lhr_tools.metrics.anchor import Trajectory, anchor_rate, anchored_ids
from lhr_tools.metrics.credit import StepCredit, cohens_kappa, credit_precision
from lhr_tools.metrics.saturation import SaturationParams, saturation_point
from lhr_tools.metrics.verifier import Verdict, false_accept_rate, false_reject_rate, auc_roc, auprc


def _run_anchor(rows, **kwargs):
    trajectories = [Trajectory(r["steps"],
                               frozenset(r.get("correct", [])),
                               anchor_fraction=kwargs.get("frac", 0.20),
                               neighbourhood_radius=kwargs.get("radius", 0))
                    for r in rows]
    ids = anchored_ids(trajectories)
    return {"value": anchor_rate(trajectories),
            "n_anchored": len(ids),
            "anchored_indices": ids}


def _run_saturation(rows, **kwargs):
    # rows is unused here; saturation derives from CLI params, not data.
    # Kept for interface uniformity; pass_at_k computed from p_x if given.
    raise ValueError("saturation is parameter-driven, not data-driven")


def _run_credit(rows, **kwargs):
    pairs = [StepCredit(r["pred"], r["truth"]) for r in rows]
    return {"cohens_kappa": cohens_kappa(pairs),
            "precision": credit_precision(pairs)}


def _run_verifier(rows, **kwargs):
    verdicts = [Verdict(bool(r["is_exploit"]), bool(r["accepted"]),
                        float(r["score"])) for r in rows]
    return {"false_accept_rate": false_accept_rate(verdicts),
            "false_reject_rate": false_reject_rate(verdicts),
            "auc_roc": auc_roc(verdicts),
            "auprc": auprc(verdicts),
            "n_exploit": sum(1 for v in verdicts if v.is_exploit),
            "n_honest": sum(1 for v in verdicts if not v.is_exploit)}


# Metric → (compute function, required schema name, needs config?)
_DISPATCH: dict[str, tuple[Any, str, bool]] = {
    "anchor": (_run_anchor, "anchor", True),
    "saturation": (_run_saturation, "saturation", True),
    "credit": (_run_credit, "credit", False),
    "verifier": (_run_verifier, "verifier", False),
}


def run_metric(metric: str, data_path: str | Path,
               config: Config | None = None) -> dict[str, Any]:
    """Run one metric over a JSONL data file and return the result dict."""
    if metric not in _DISPATCH:
        raise ValueError(f"unknown metric: {metric}")
    fn, schema_name, needs_config = _DISPATCH[metric]
    rows = read_jsonl(data_path)
    errors = validate_rows(schema_name, rows)
    if errors:
        raise ValueError(f"schema validation failed: {errors[:3]}...")

    cfg = config or Config.load()
    if needs_config:
        kwargs: dict[str, Any] = {}
        if metric == "anchor":
            kwargs = {"frac": cfg.get("anchor", "frac", 0.20),
                      "radius": cfg.get("anchor", "radius", 0)}
        elif metric == "saturation":
            kwargs = {"f_max": cfg.get("saturation", "f_max", 0.9),
                      "eps": cfg.get("saturation", "eps", 0.01)}
        result = fn(rows, **kwargs)
    else:
        result = fn(rows)

    result["metric"] = metric
    result["n"] = len(rows)
    result["data_file"] = str(data_path)
    return result


def run_all(metric: str, data_path: str | Path,
            config: Config | None = None) -> dict[str, Any]:
    """Alias for run_metric (kept for interface symmetry)."""
    return run_metric(metric, data_path, config)
