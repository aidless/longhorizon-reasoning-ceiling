"""CLI-layer tests (RED→GREEN).

Run: python3 tests/test_cli.py
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lhr_tools.cli import main


def _run(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(args)
    return rc, buf.getvalue()


def test_cli_anchor_end_to_end():
    """Full CLI round-trip on real JSONL input."""
    with tempfile.TemporaryDirectory() as tmp:
        traj = Path(tmp) / "traj.jsonl"
        traj.write_text(
            '{"steps":[1,1,1,1],"correct":[2]}\n'
            '{"steps":[1,2,3,4],"correct":[4]}\n', encoding="utf-8")
        rc, out = _run(["anchor", str(traj)])
        assert rc == 0
        result = json.loads(out)
        assert abs(result["value"] - 0.5) < 1e-9


def test_cli_saturation():
    rc, out = _run(["saturation", "--px", "0.5", "--fmax", "0.9"])
    assert rc == 0
    result = json.loads(out)
    assert result["metric"] == "saturation_point"
    assert result["N_star"] >= 1


def test_cli_saturation_no_params():
    """Regression (v0.4 review ③): no --px / --successes must raise a
    clear ValueError, not a bare TypeError."""
    try:
        _run(["saturation"])
        assert False, "should have raised"
    except ValueError as e:
        assert "需要 --px 或" in str(e) or "需要 --px" in str(e)


def test_cli_visualize_saturation_no_params():
    """Regression (v0.4 review ③): visualize saturation with no params
    must raise a clear ValueError, not a bare TypeError."""
    try:
        _run(["visualize", "saturation"])
        assert False, "should have raised"
    except ValueError as e:
        assert "需要 --px" in str(e)


def test_cli_credit():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "c.jsonl"
        p.write_text('{"pred":"positive","truth":"positive"}\n'
                     '{"pred":"negative","truth":"negative"}\n',
                     encoding="utf-8")
        rc, out = _run(["credit", str(p)])
        assert rc == 0
        result = json.loads(out)
        assert result["cohens_kappa"] > 0.9


def test_cli_verifier():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "v.jsonl"
        p.write_text('{"is_exploit":true,"accepted":false,"score":0.1}\n'
                     '{"is_exploit":false,"accepted":true,"score":0.9}\n',
                     encoding="utf-8")
        rc, out = _run(["verifier", str(p)])
        assert rc == 0
        result = json.loads(out)
        assert result["false_accept_rate"] == 0.0


def test_cli_dataset():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "d.jsonl"
        rc, _ = _run(["dataset", "anchor", "--n", "5", "--seed", "42",
                      "--output", str(p)])
        assert rc == 0
        rows = [json.loads(line) for line in p.read_text().splitlines()]
        assert len(rows) == 5
        assert all("steps" in r and "correct" in r for r in rows)


def test_cli_dataset_realistic():
    # B5 fix: --realistic flag now reachable from CLI (was API-only).
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "d.jsonl"
        rc, _ = _run(["dataset", "verifier", "--n", "50", "--seed", "7",
                      "--realistic", "--output", str(p)])
        assert rc == 0
        rows = [json.loads(line) for line in p.read_text().splitlines()]
        assert len(rows) == 50
        assert all("is_exploit" in r and "accepted" in r for r in rows)
        # Exploit rate must fall in the RHB-observed band (0%, 13.9%).
        ex = sum(1 for r in rows if r["is_exploit"]) / len(rows)
        assert 0.0 <= ex <= 0.15


def test_cli_config_show():
    rc, out = _run(["config", "--show"])
    assert rc == 0
    cfg = json.loads(out)
    assert "anchor" in cfg and "saturation" in cfg and "dataset" in cfg


def test_cli_selftest():
    rc, out = _run(["selftest"])
    assert rc == 0
    assert "通过" in out


def test_cli_report_default_output():
    """RED→GREEN: report with no --output defaults to project analyses/."""
    with tempfile.TemporaryDirectory() as tmp:
        # Write result JSONs to tmp.
        r1 = Path(tmp) / "r1.json"
        r1.write_text(json.dumps({"metric": "anchor", "value": 0.5,
                                  "n": 2, "data_file": "x.jsonl"}),
                      encoding="utf-8")
        rc, out = _run(["report", str(r1)])
        assert rc == 0
        # Default output is project analyses/lhr-report.md.
        assert "analyses" in out, f"should mention analyses dir, got: {out}"
        assert Path(out.split("报告已写入 ")[1].strip()).exists()


def test_cli_red_unknown_command():
    """RED: unknown command must exit nonzero."""
    try:
        rc, _ = _run(["nonexistent"])
        assert rc != 0, "unknown command should fail"
    except SystemExit:
        pass  # argparse exits with code 2 on unknown subcommand


def test_cli_visualize_saturation():
    """A2: visualize saturation produces a PNG."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "sat.png"
        rc, _ = _run(["visualize", "saturation", "--px", "0.3",
                      "--fmax", "0.9", "--output", str(out)])
        assert rc == 0
        assert out.exists(), "visualize should write PNG"
        assert out.stat().st_size > 0


def test_cli_visualize_anchor():
    """A2: visualize anchor from JSONL produces a PNG."""
    with tempfile.TemporaryDirectory() as tmp:
        traj = Path(tmp) / "traj.jsonl"
        traj.write_text(
            '{"steps":[1,1,1,1],"correct":[2]}\n'
            '{"steps":[1,2,3,4],"correct":[4]}\n', encoding="utf-8")
        out = Path(tmp) / "anchor.png"
        rc, _ = _run(["visualize", "anchor", str(traj), "--output", str(out)])
        assert rc == 0
        assert out.exists()


def test_cli_compare_saturation():
    """A3: compare saturation across p_x values produces a Markdown table."""
    rc, out = _run(["compare", "saturation", "--px-list", "0.3,0.7"])
    assert rc == 0
    assert "N_star" in out
    assert "p_x=0.3" in out and "p_x=0.7" in out


def test_cli_compare_anchor():
    """A3: compare anchor across frac values produces a Markdown table."""
    with tempfile.TemporaryDirectory() as tmp:
        traj = Path(tmp) / "traj.jsonl"
        traj.write_text(
            '{"steps":[1,1,1,1],"correct":[2]}\n'
            '{"steps":[1,2,3,4],"correct":[4]}\n', encoding="utf-8")
        rc, out = _run(["compare", "anchor", str(traj), "--frac-list", "0.1,0.2"])
        assert rc == 0
        assert "anchor_rate" in out


def test_cli_compare_verifier():
    """A3: compare verifier across datasets produces a Markdown table."""
    with tempfile.TemporaryDirectory() as tmp:
        p1 = Path(tmp) / "v1.jsonl"
        p2 = Path(tmp) / "v2.jsonl"
        p1.write_text('{"is_exploit":true,"accepted":false,"score":0.1}\n'
                      '{"is_exploit":false,"accepted":true,"score":0.9}\n',
                      encoding="utf-8")
        p2.write_text('{"is_exploit":true,"accepted":true,"score":0.9}\n'
                      '{"is_exploit":false,"accepted":false,"score":0.1}\n',
                      encoding="utf-8")
        rc, out = _run(["compare", "verifier", str(p1), str(p2),
                        "--labels", "good,bad"])
        assert rc == 0
        assert "auc_roc" in out
        assert "good" in out and "bad" in out


def test_cli_import_verifier():
    """B6: import raw trajectory JSONL → verifier row JSONL."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.jsonl"
        raw.write_text('{"trajectory_id":"t1","step_type":"hypothesis",'
                       '"is_correct":false,"confidence":0.9}\n'
                       '{"trajectory_id":"t1","step_type":"conclusion",'
                       '"is_correct":true,"confidence":0.95}\n',
                       encoding="utf-8")
        out_path = Path(tmp) / "out.jsonl"
        rc, out = _run(["import", "verifier", str(raw),
                        "--output", str(out_path)])
        assert rc == 0
        assert "导入" in out
        rows = [json.loads(line) for line in out_path.read_text().splitlines()]
        assert len(rows) == 2
        assert rows[0]["is_exploit"] is True   # 错误 hypothesis → exploit
        assert rows[1]["is_exploit"] is False  # 正确 conclusion → 非 exploit


def test_cli_import_red_unknown_metric():
    """B6: import with unknown metric raises (argparse choices)."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.jsonl"
        raw.write_text('{"is_correct":true}\n', encoding="utf-8")
        out_path = Path(tmp) / "out.jsonl"
        try:
            _run(["import", "nope", str(raw), "--output", str(out_path)])
            assert False, "should have raised"
        except SystemExit:
            pass  # argparse rejects the choice


def test_cli_trajectory_end_to_end():
    """C1: trajectory command runs on a steps JSONL."""
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "traj.jsonl"
        data.write_text('{"steps":[0,1,1,1]}\n{"steps":[0,0,0,0]}\n', encoding="utf-8")
        rc, out = _run(["trajectory", str(data)])
        assert rc == 0
        result = json.loads(out)
        assert result["metric"] == "trajectory"
        assert result["n_trajectories"] == 2
        assert 0.0 <= result["mean_per_step_reliability"] <= 1.0


def test_cli_calibration_end_to_end():
    """C2: calibration command runs on a confidence/outcome JSONL."""
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "cal.jsonl"
        data.write_text('{"confidence":0.9,"outcome":true}\n'
                        '{"confidence":0.1,"outcome":false}\n', encoding="utf-8")
        rc, out = _run(["calibration", str(data)])
        assert rc == 0
        result = json.loads(out)
        assert result["metric"] == "calibration"
        assert result["n_samples"] == 2
        assert 0.0 <= result["ece"] <= 1.0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = []
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
        except AssertionError as e:
            failed.append(t.__name__)
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
