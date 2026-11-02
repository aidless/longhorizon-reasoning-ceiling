"""CLI entry point for the lhr_tools toolchain.

Command tree:
  anchor       — compute anchor rate from a trajectory JSONL
  saturation   — estimate the TTSPM saturation point N* (parameter-driven:
                 --px / --successes+--attempts, no data file)
  credit       — early-step credit precision (Cohen's kappa)
  verifier     — verifier robustness (false-accept / false-reject / AUC)
  trajectory   — trajectory-level diagnostics (per-step reliability,
                 snowball rate, positional impact, fragility, context drag)
  calibration  — verifier / predictor calibration (ECE, Brier, reliability)
  dataset      — generate / validate synthetic dataset
  report       — generate a Markdown report from results JSON
  config       — show / validate configuration
  import       — convert raw reasoning trajectory JSONL → metric-row JSONL
  selftest     — run all module self-tests (RED→GREEN)

Data-driven metrics (anchor/credit/verifier) read a JSONL file; the
saturation metric is the sole exception — it takes scalar parameters.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lhr_tools.services import pipeline
from lhr_tools.services import reporter


def _cmd_anchor(args: argparse.Namespace) -> int:
    from lhr_tools.config.loader import Config

    cfg = Config.load(args.config)
    result = pipeline.run_metric("anchor", args.input, cfg)
    print(json.dumps(result, indent=2))
    return 0


def _cmd_saturation(args: argparse.Namespace) -> int:
    if args.successes is not None and args.attempts is not None:
        p_x = args.successes / args.attempts
    else:
        p_x = args.px
    if p_x is None:
        raise ValueError("saturation 需要 --px 或 --successes/--attempts")
    from lhr_tools.metrics.saturation import (
        SaturationParams, saturation_point, pass_at_k)
    params = SaturationParams(p_x, args.fmax, args.eps)
    n_star = saturation_point(params)
    result = {
        "metric": "saturation_point",
        "N_star": n_star,
        "p_x": p_x,
        "f_max": params.f_max,
        "eps": params.eps,
        "pass_at_1": pass_at_k(p_x, 1),
        "pass_at_4": pass_at_k(p_x, 4),
        "pass_at_8": pass_at_k(p_x, 8),
        "pass_at_16": pass_at_k(p_x, 16),
        "pass_at_32": pass_at_k(p_x, 32),
    }
    print(json.dumps(result, indent=2))
    return 0


def _cmd_credit(args: argparse.Namespace) -> int:
    result = pipeline.run_metric("credit", args.input)
    print(json.dumps(result, indent=2))
    return 0


def _cmd_verifier(args: argparse.Namespace) -> int:
    result = pipeline.run_metric("verifier", args.input)
    print(json.dumps(result, indent=2))
    return 0


def _cmd_dataset(args: argparse.Namespace) -> int:
    from lhr_tools.io import generate
    from lhr_tools.io.jsonl import write_jsonl
    from lhr_tools.io.schema import validate_rows

    if args.realistic:
        rows = generate.generate_realistic(args.metric, n=args.n, seed=args.seed)
    else:
        rows = generate.generate(args.metric, n=args.n, seed=args.seed)
    errors = validate_rows(args.metric, rows)
    if errors:
        print(f"schema errors: {errors[:3]}", file=sys.stderr)
        return 1
    write_jsonl(args.output, rows)
    print(f"已生成 {len(rows)} 行 → {args.output}"
          + ("（文献校准分布，B5）" if args.realistic else ""))
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    from lhr_tools.services.compare import (
        CompareConfig, compare_anchor, compare_saturation,
        compare_verifier, format_comparison)

    if args.metric == "saturation":
        # Build configs from --px list (comma-separated).
        px_list = [float(x) for x in args.px_list.split(",")] if args.px_list else [0.3, 0.7]
        fmax = args.fmax
        configs = [CompareConfig(f"p_x={p}", {"p_x": p, "f_max": fmax})
                   for p in px_list]
        rows = compare_saturation(configs)
    elif args.metric == "anchor":
        if not args.input:
            raise ValueError("anchor compare 需要 --input 数据文件")
        # Build configs from --frac list (comma-separated) × --radius.
        frac_list = [float(x) for x in args.frac_list.split(",")] if args.frac_list else [0.1, 0.2]
        radius = args.radius
        configs = [CompareConfig(f"frac={f},r={radius}", {"frac": f, "radius": radius})
                   for f in frac_list]
        rows = compare_anchor(args.input, configs)
    elif args.metric == "verifier":
        # Collect inputs from both the positional single `input` and the
        # `inputs` list (argparse can route args ambiguously).
        all_inputs = []
        if args.input:
            all_inputs.append(args.input)
        all_inputs.extend(args.inputs)
        if not all_inputs:
            raise ValueError("verifier compare 需要数据文件列表")
        labels = args.labels.split(",") if args.labels else [f"ds{i+1}" for i in range(len(all_inputs))]
        if len(labels) != len(all_inputs):
            raise ValueError(f"labels 数量({len(labels)})与数据文件数量({len(all_inputs)})不一致")
        rows = compare_verifier(all_inputs, labels)
    else:
        raise ValueError(f"unknown compare metric: {args.metric}")

    md = format_comparison(rows)
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"对比表已写入 {args.output}")
    else:
        print(md)
    return 0


def _cmd_visualize(args: argparse.Namespace) -> int:
    from lhr_tools.services.visualize import render

    if args.metric == "verifier":
        # verifier ROC needs raw verdict data — read from input JSONL.
        from lhr_tools.io.jsonl import read_jsonl
        from lhr_tools.metrics.verifier import Verdict
        rows = read_jsonl(args.input)
        verdicts = [Verdict(bool(r["is_exploit"]), bool(r["accepted"]),
                            float(r["score"])) for r in rows]
        from lhr_tools.services.visualize import roc_curve
        out = roc_curve(verdicts, args.output)
    else:
        # Run the metric through the pipeline to get a result dict,
        # then visualize from the aggregate.
        if args.input:
            result = pipeline.run_metric(args.metric, args.input)
        else:
            # saturation / anchor from CLI params when no input given.
            if args.metric == "saturation":
                from lhr_tools.metrics.saturation import SaturationParams, saturation_point
                if args.successes is not None and args.attempts is not None:
                    p_x = args.successes / args.attempts
                else:
                    p_x = args.px
                if p_x is None:
                    raise ValueError("visualize saturation 需要 --px 或 --successes/--attempts")
                n_star = saturation_point(SaturationParams(p_x, args.fmax, args.eps))
                result = {"metric": "saturation", "p_x": p_x, "f_max": args.fmax,
                          "eps": args.eps, "N_star": n_star}
            else:
                raise ValueError(f"{args.metric} 需要 --input 数据文件")
        out = render(args.metric, result, args.output)

    if isinstance(out, str) and out.endswith(".png"):
        print(f"图已写入 {out}")
    else:
        print(out)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    results = []
    for path in args.inputs:
        with open(path, "r", encoding="utf-8") as f:
            results.append(json.load(f))
    # Default output to the project analyses/ directory when not given.
    if args.output is None:
        project_root = Path(__file__).resolve().parent.parent.parent
        analyses = project_root / "analyses"
        analyses.mkdir(parents=True, exist_ok=True)
        args.output = str(analyses / "lhr-report.md")
    out = reporter.generate_report(results, args.output)
    print(f"报告已写入 {out}")
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    from lhr_tools.config.loader import Config

    cfg = Config.load(args.config)
    if args.show:
        print(json.dumps(cfg.data, indent=2))
    else:
        # Validate: round-trip should preserve values.
        for section in ("anchor", "saturation", "dataset"):
            assert section in cfg.data, f"missing section: {section}"
        print("配置有效（anchor/saturation/dataset 三节齐全）")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    """Import raw reasoning trajectory JSONL → metric row JSONL (B6)."""
    from lhr_tools.io.importer import import_trajectory
    from lhr_tools.io.jsonl import read_jsonl, write_jsonl

    rows = read_jsonl(args.input)
    out = import_trajectory(args.metric, rows)
    write_jsonl(args.output, out)
    print(f"导入 {len(rows)} 行 → {len(out)} 行 ({args.metric}) → {args.output}")
    return 0


def _cmd_trajectory(args: argparse.Namespace) -> int:
    """Trajectory-level diagnostics (C1, v0.5)."""
    from lhr_tools.io.jsonl import read_jsonl
    from lhr_tools.metrics import trajectory

    rows = read_jsonl(args.input)
    trajectories = [r["steps"] for r in rows]
    result = {
        "metric": "trajectory",
        "n_trajectories": len(trajectories),
        "mean_per_step_reliability": trajectory.per_step_reliability(
            [s for t in trajectories for s in t]),
        "snowball_rate": trajectory.snowball_rate(trajectories),
        "mean_context_drag": trajectory.context_drag(trajectories),
    }
    print(json.dumps(result, indent=2))
    return 0


def _cmd_calibration(args: argparse.Namespace) -> int:
    """Verifier / predictor calibration (C2, v0.5)."""
    from lhr_tools.io.jsonl import read_jsonl
    from lhr_tools.metrics import calibration

    rows = read_jsonl(args.input)
    confidences = [float(r["confidence"]) for r in rows]
    outcomes = [bool(r["outcome"]) for r in rows]
    result = {
        "metric": "calibration",
        "n_samples": len(rows),
        "ece": calibration.expected_calibration_error(confidences, outcomes),
        "brier": calibration.brier_score(confidences, outcomes),
        "confidence_margin": calibration.confidence_margin(confidences, outcomes),
        "n_bins": len(calibration.reliability_diagram(confidences, outcomes)),
    }
    print(json.dumps(result, indent=2))
    return 0


def _cmd_selftest(_args: argparse.Namespace) -> int:
    from lhr_tools.metrics.anchor import _selftest as anchor_st
    from lhr_tools.metrics.saturation import _selftest as sat_st
    from lhr_tools.metrics.credit import _selftest as credit_st
    from lhr_tools.metrics.verifier import _selftest as verifier_st
    from lhr_tools.metrics.trajectory import _selftest as trajectory_st
    from lhr_tools.metrics.calibration import _selftest as calibration_st
    from lhr_tools.config.loader import _selftest as config_st
    for st in (anchor_st, sat_st, credit_st, verifier_st, trajectory_st,
               calibration_st, config_st):
        st()
    print("全部 selftest 通过（RED→GREEN）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lhr-tools",
        description="Long-Horizon Reasoning evaluation toolchain")
    p.add_argument("--config", default=None, help="config YAML/JSON path")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("anchor", help="compute anchor rate from trajectories")
    a.add_argument("input", help="JSONL with {steps, correct}")
    a.add_argument("--frac", type=float, default=None)
    a.add_argument("--radius", type=int, default=None)
    a.set_defaults(func=_cmd_anchor)

    s = sub.add_parser("saturation", help="estimate TTSPM saturation point")
    s.add_argument("--px", type=float, default=None)
    s.add_argument("--successes", type=int, default=None)
    s.add_argument("--attempts", type=int, default=None)
    s.add_argument("--fmax", type=float, default=0.9)
    s.add_argument("--eps", type=float, default=0.01)
    s.set_defaults(func=_cmd_saturation)

    c = sub.add_parser("credit", help="early-step credit precision")
    c.add_argument("input", help="JSONL with {pred, truth}")
    c.set_defaults(func=_cmd_credit)

    v = sub.add_parser("verifier", help="verifier robustness")
    v.add_argument("input", help="JSONL with {is_exploit, accepted, score}")
    v.set_defaults(func=_cmd_verifier)

    d = sub.add_parser("dataset", help="generate synthetic dataset")
    d.add_argument("metric", choices=["anchor", "credit", "verifier"])
    d.add_argument("--n", type=int, default=10)
    d.add_argument("--seed", type=int, default=42)
    d.add_argument("--realistic", action="store_true",
                   help="use literature-calibrated distributions (B5, n default 100)")
    d.add_argument("--output", required=True)
    d.set_defaults(func=_cmd_dataset)

    r = sub.add_parser("report", help="generate Markdown report")
    r.add_argument("inputs", nargs="+", help="result JSON files")
    r.add_argument("--output", default=None,
                   help="output .md path (default: project analyses/lhr-report.md)")
    r.set_defaults(func=_cmd_report)

    vz = sub.add_parser("visualize", help="render metric output as a plot")
    vz.add_argument("metric", choices=["anchor", "saturation", "verifier"])
    vz.add_argument("input", nargs="?", default=None,
                    help="JSONL data file (required for anchor/verifier)")
    vz.add_argument("--output", default=None, help="output .png path")
    vz.add_argument("--px", type=float, default=None, help="saturation: p_x")
    vz.add_argument("--successes", type=int, default=None, help="saturation: successes")
    vz.add_argument("--attempts", type=int, default=None, help="saturation: attempts")
    vz.add_argument("--fmax", type=float, default=0.9, help="saturation: F_max")
    vz.add_argument("--eps", type=float, default=0.01, help="saturation: eps")
    vz.set_defaults(func=_cmd_visualize)

    cm = sub.add_parser("compare", help="compare across configurations")
    cm.add_argument("metric", choices=["anchor", "saturation", "verifier"])
    cm.add_argument("input", nargs="?", default=None,
                    help="JSONL data file (anchor compare)")
    cm.add_argument("inputs", nargs="*", help="JSONL data files (verifier compare)")
    cm.add_argument("--px-list", default=None, help="saturation: comma-separated p_x values")
    cm.add_argument("--frac-list", default=None, help="anchor: comma-separated frac values")
    cm.add_argument("--radius", type=int, default=0, help="anchor: neighbourhood radius")
    cm.add_argument("--fmax", type=float, default=0.9, help="saturation: F_max")
    cm.add_argument("--labels", default=None, help="verifier: comma-separated labels")
    cm.add_argument("--output", default=None, help="output .md path")
    cm.set_defaults(func=_cmd_compare)

    cf = sub.add_parser("config", help="show / validate configuration")
    cf.add_argument("--show", action="store_true", help="dump config as JSON")
    cf.set_defaults(func=_cmd_config)

    imp = sub.add_parser("import", help="import raw reasoning trajectory JSONL")
    imp.add_argument("metric", choices=["anchor", "credit", "verifier"],
                     help="target metric row format")
    imp.add_argument("input", help="raw trajectory JSONL (step rows)")
    imp.add_argument("--output", required=True, help="output metric-row JSONL")
    imp.set_defaults(func=_cmd_import)

    tj = sub.add_parser("trajectory", help="trajectory-level diagnostics")
    tj.add_argument("input", help="JSONL with {steps: [0/1,...]}")
    tj.set_defaults(func=_cmd_trajectory)

    cal = sub.add_parser("calibration", help="verifier / predictor calibration")
    cal.add_argument("input", help="JSONL with {confidence, outcome}")
    cal.set_defaults(func=_cmd_calibration)

    st = sub.add_parser("selftest", help="run all self-tests")
    st.set_defaults(func=_cmd_selftest)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
