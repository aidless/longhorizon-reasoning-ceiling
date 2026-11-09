"""IO-layer tests (RED→GREEN).

Run: python3 tests/test_io.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lhr_tools.io.jsonl import read_jsonl, write_jsonl, iter_jsonl, write_json
from lhr_tools.io.schema import validate_rows
from lhr_tools.io.generate import generate, generate_realistic


def test_jsonl_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "d.jsonl"
        rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        write_jsonl(p, rows)
        back = read_jsonl(p)
        assert back == rows
        # iter_jsonl lazy read matches.
        assert list(iter_jsonl(p)) == rows


def test_jsonl_red_invalid_row():
    """RED: a non-object row must raise."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "bad.jsonl"
        p.write_text('{"a": 1}\n[1,2,3]\n', encoding="utf-8")
        try:
            read_jsonl(p)
            assert False, "should have raised"
        except ValueError:
            pass


def test_schema_valid():
    rows = [{"steps": [1, 2, 3], "correct": [3]}]
    assert validate_rows("anchor", rows) == []


def test_schema_red_missing_key():
    rows = [{"steps": [1, 2, 3]}]  # missing 'correct'
    errors = validate_rows("anchor", rows)
    assert len(errors) == 1
    assert "missing key 'correct'" in errors[0]


def test_schema_red_unknown_metric():
    assert len(validate_rows("nope", [])) == 1


def test_generate_deterministic():
    """Same seed → same rows."""
    a = generate("anchor", n=10, seed=42)
    b = generate("anchor", n=10, seed=42)
    assert a == b


def test_generate_red_unknown():
    try:
        generate("nope")
        assert False, "should have raised"
    except ValueError:
        pass


def test_generate_realistic_verifier_range():
    """B5: verifier exploit rate falls in the RHB-observed range."""
    rows = generate_realistic("verifier", n=500, seed=42)
    assert len(rows) == 500
    exploit_rate = sum(1 for r in rows if r["is_exploit"]) / len(rows)
    assert 0.0 <= exploit_rate <= 0.15  # generator range in io/generate.py, not a paper replay


def test_generate_realistic_credit_accuracy():
    """B5: credit accuracy near the TRCA-reported mid-range."""
    rows = generate_realistic("credit", n=500, seed=42)
    accuracy = sum(1 for r in rows if r["pred"] == r["truth"]) / len(rows)
    assert 0.75 <= accuracy <= 0.95


def test_generate_realistic_deterministic():
    """B5: same seed produces identical output."""
    a = generate_realistic("verifier", n=100, seed=7)
    b = generate_realistic("verifier", n=100, seed=7)
    assert a == b


def test_generate_realistic_unknown_metric():
    """B5: unknown metric raises ValueError."""
    try:
        generate_realistic("nope", n=10)
        assert False, "should have raised"
    except ValueError:
        pass


def test_importer_null_id_not_dropped():
    """Regression (v0.4 review ②): a row with trajectory_id=None must NOT
    be dropped. The old code excluded None-keyed groups, silently losing
    those rows (3 rows → 2 trajectories)."""
    from lhr_tools.io.importer import import_trajectory
    rows = [
        {"trajectory_id": "t1", "step_type": "hypothesis",
         "is_correct": False, "confidence": 0.9},
        {"trajectory_id": None, "step_type": "hypothesis",
         "is_correct": False, "confidence": 0.9},
        {"trajectory_id": "t2", "step_type": "conclusion",
         "is_correct": True, "confidence": 0.95},
    ]
    out = import_trajectory("anchor", rows)
    # All 3 rows must survive (each forms a single-step trajectory).
    assert len(out) == 3, f"null-id row dropped: got {len(out)} trajectories, want 3"


def test_importer_mixed_ids_preserve_order():
    """Regression (v0.4 review ②): None-keyed groups must interleave by
    first-appearance, not be appended last."""
    from lhr_tools.io.importer import import_trajectory
    rows = [
        {"trajectory_id": "t1", "step_type": "hypothesis",
         "is_correct": True},
        {"trajectory_id": None, "step_type": "hypothesis",
         "is_correct": False},
        {"trajectory_id": "t2", "step_type": "conclusion",
         "is_correct": True},
    ]
    out = import_trajectory("anchor", rows)
    assert len(out) == 3
    # First trajectory = t1's single correct step → steps=[1].
    assert out[0]["steps"] == [1], f"t1 not first: {out[0]}"
    # Second = the null-id wrong row.
    assert out[1]["steps"] == [0], f"null-id not second: {out[1]}"


def test_importer_verifier_prefers_external_score():
    """Regression (v0.4 review ⑥): when a verifier_score field is present,
    it must be used as the score instead of the model's self-confidence."""
    from lhr_tools.io.importer import import_trajectory
    rows = [
        {"step_type": "hypothesis", "is_correct": False,
         "confidence": 0.9, "verifier_score": 0.15},
    ]
    out = import_trajectory("verifier", rows)
    assert len(out) == 1
    assert out[0]["is_exploit"] is True
    # score comes from verifier_score, not confidence.
    assert abs(out[0]["score"] - 0.15) < 1e-9
    # accepted still mirrors the model's confidence threshold.
    assert out[0]["accepted"] is True


def test_importer_verifier_falls_back_to_confidence():
    """Regression (v0.4 review ⑥): without verifier_score, confidence is
    the proxy fallback."""
    from lhr_tools.io.importer import import_trajectory
    rows = [
        {"step_type": "conclusion", "is_correct": True, "confidence": 0.85},
    ]
    out = import_trajectory("verifier", rows)
    assert len(out) == 1
    assert out[0]["is_exploit"] is False
    assert abs(out[0]["score"] - 0.85) < 1e-9


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
