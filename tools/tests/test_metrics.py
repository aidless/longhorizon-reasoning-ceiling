"""Measurement-layer tests (RED→GREEN).

Run: python3 tests/test_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lhr_tools.metrics.anchor import Trajectory, anchor_rate, _is_anchored
from lhr_tools.metrics.saturation import SaturationParams, saturation_point, pass_at_k, bootstrap_nstar_ci
from lhr_tools.metrics.credit import StepCredit, cohens_kappa, credit_precision
from lhr_tools.metrics.verifier import Verdict, false_accept_rate, false_reject_rate, auc_roc, auprc
from lhr_tools.metrics.trajectory import (
    per_step_reliability, geometric_ceiling, snowball_rate,
    positional_impact, late_stage_fragility_index,
    error_origin_detection, error_spread_curve, context_drag,
)
from lhr_tools.metrics.calibration import (
    expected_calibration_error, brier_score, reliability_diagram,
    confidence_margin,
)


def test_anchor_red():
    t = Trajectory([1, 1, 1, 1], frozenset({2}))
    assert _is_anchored(t)


def test_anchor_green():
    t = Trajectory([1, 2, 3, 4], frozenset({4}))
    assert not _is_anchored(t)


def test_anchor_rate_mixed():
    t1 = Trajectory([1, 1, 1, 1], frozenset({2}))
    t2 = Trajectory([1, 2, 3, 4], frozenset({4}))
    assert abs(anchor_rate([t1, t2]) - 0.5) < 1e-9


def test_anchor_within_radius_zero_non_int_noop():
    # radius=0: strict equality, non-int states compared by identity —
    # no ValueError (documented cheap test).
    t = Trajectory(["a", "a", "a"], frozenset({"b"}), neighbourhood_radius=0)
    assert _is_anchored(t)


def test_anchor_within_radius_positive_non_int_raises():
    # radius>0 with non-int states must raise a clear ValueError, not
    # silently return False (v0.4 review ⑤ fixed). Use steps that
    # actually differ so _within(a,b,radius>0) reaches the non-int check.
    t = Trajectory(["a", "b", "b"], frozenset({"c"}), neighbourhood_radius=2)
    try:
        _is_anchored(t)
        assert False, "should have raised for non-int with radius>0"
    except ValueError:
        pass


def test_saturation_red():
    try:
        saturation_point(SaturationParams(0.0, 0.9))
        assert False, "should have raised"
    except ValueError:
        pass


def test_saturation_green():
    s = saturation_point(SaturationParams(0.5, 0.9, 0.01))
    assert isinstance(s, int) and s >= 1
    assert pass_at_k(0.3, 1) < pass_at_k(0.3, 4) < pass_at_k(0.3, 16)


def test_saturation_bootstrap_ci():
    """A1: bootstrap CI is finite, ordered, brackets the point estimate,
    and is deterministic for a fixed seed."""
    lo, hi = bootstrap_nstar_ci(30, 60, 0.9, seed=7)
    assert lo <= hi, "CI not ordered"
    n_star = saturation_point(SaturationParams(0.5, 0.9, 0.01))
    assert lo <= float(n_star) <= hi, "CI should bracket point estimate"
    # Determinism
    lo2, hi2 = bootstrap_nstar_ci(30, 60, 0.9, seed=7)
    assert (lo, hi) == (lo2, hi2), "bootstrap not deterministic for fixed seed"


def test_saturation_bootstrap_degenerate():
    """A1: degenerate outcomes collapse to deterministic limits."""
    lo_all_success, hi_all_success = bootstrap_nstar_ci(60, 60, 0.9, seed=1)
    assert (lo_all_success, hi_all_success) == (1.0, 1.0)
    lo_all_fail, hi_all_fail = bootstrap_nstar_ci(0, 60, 0.9, seed=1)
    assert lo_all_fail == float("inf") and hi_all_fail == float("inf")


def test_saturation_bootstrap_high_skip_index():
    """Regression (v0.4 review ①): percentile index must use len(boot_vals),
    not n_boot. With a high degenerate-skip rate (1/40 → ~365/1000 skipped),
    the OLD code used n_boot as denominator, shifting the low percentile to
    0.0378 instead of 0.025 and inflating the CI lower bound (91 vs 65)."""
    lo, hi = bootstrap_nstar_ci(1, 40, 0.9, seed=7)
    # With the corrected denominator, the lower bound must drop well below
    # the buggy value (91). It should sit near the true 2.5th percentile.
    assert lo < 91, f"CI lower bound not corrected: lo={lo} (expect < 91)"
    assert lo <= hi, "CI not ordered"



def test_credit_red():
    bad = [StepCredit("positive", "negative") for _ in range(10)]
    assert cohens_kappa(bad) < 0.5


def test_credit_green():
    good = [StepCredit("positive", "positive") for _ in range(5)] + \
           [StepCredit("negative", "negative") for _ in range(5)]
    assert cohens_kappa(good) > 0.9
    assert credit_precision(good) == 1.0


def test_verifier_red():
    bad = [Verdict(True, True, 0.9), Verdict(True, True, 0.8),
           Verdict(False, True, 0.7), Verdict(False, True, 0.6)]
    assert false_accept_rate(bad) == 1.0


def test_verifier_green():
    good = [Verdict(True, False, 0.1), Verdict(False, True, 0.9)]
    assert false_accept_rate(good) == 0.0
    assert false_reject_rate(good) == 0.0
    assert auc_roc(good) == 1.0


def test_verifier_auprc_range():
    mixed = [Verdict(True, False, 0.1), Verdict(True, True, 0.8),
             Verdict(False, True, 0.9), Verdict(False, False, 0.2)]
    v = auprc(mixed)
    assert 0.0 <= v <= 1.0


def test_verifier_auc_ties():
    """RED→GREEN for tie handling: perfectly tied scores must give AUC=0.5.

    The naive two-pointer sweep (no tie correction) returns 0.0 here,
    which is a bug — a verifier whose scores carry no signal should be
    indistinguishable from a coin flip.
    """
    tied = [Verdict(True, False, 0.5), Verdict(False, True, 0.5)]
    assert abs(auc_roc(tied) - 0.5) < 1e-9, f"AUC on ties wrong: {auc_roc(tied)}"


def test_verifier_auc_perfect_separation():
    """Perfect separation (honest high, exploit low) must give AUC=1."""
    good = [Verdict(True, False, 0.1), Verdict(False, True, 0.9)]
    assert abs(auc_roc(good) - 1.0) < 1e-9


def test_verifier_auc_reversed():
    """Reversed scores (exploit high, honest low) must give AUC=0."""
    bad = [Verdict(True, True, 0.9), Verdict(False, False, 0.1)]
    assert abs(auc_roc(bad) - 0.0) < 1e-9


# ---------------------------------------------------------------------
# C1: trajectory diagnostics (v0.5)
# ---------------------------------------------------------------------
def test_trajectory_reliability():
    assert per_step_reliability([0, 0, 0, 0]) == 1.0
    assert per_step_reliability([0, 1, 0, 1]) == 0.5
    assert per_step_reliability([]) == 1.0
    assert per_step_reliability([0, 1, 1, 1], horizon=2) == 0.5


def test_trajectory_geometric_ceiling():
    assert abs(geometric_ceiling(0.9, 10) - 0.3487) < 1e-3
    assert geometric_ceiling(1.0, 100) == 1.0
    assert geometric_ceiling(0.0, 5) == 0.0
    try:
        geometric_ceiling(1.5, 5)
        assert False
    except ValueError:
        pass


def test_trajectory_snowball():
    assert snowball_rate([[0, 1, 1, 1], [0, 0, 1, 1]]) == 1.0
    assert snowball_rate([[0, 1, 0, 0], [0, 0, 0, 0]]) == 0.0
    assert snowball_rate([]) == 0.0


def test_trajectory_positional_impact():
    assert positional_impact([0, 1, 0, 1]) == [0.0, 2.0, 0.0, 4.0]


def test_trajectory_fragility():
    late = late_stage_fragility_index([0, 0, 1, 1])
    early = late_stage_fragility_index([1, 1, 0, 0])
    assert late == float("inf")
    assert early == 0.0
    assert late_stage_fragility_index([0, 0, 0, 0]) == 1.0


def test_trajectory_origin():
    assert error_origin_detection([0, 1, 0], [0, 0, 0]) == 1
    assert error_origin_detection([0, 0, 0], [0, 0, 0]) is None


def test_trajectory_spread():
    curve = error_spread_curve([[0, 1, 0], [0, 0, 1]])
    assert curve == [0.0, 0.5, 0.5]


def test_trajectory_context_drag():
    assert context_drag([[0, 1, 0], [0, 1, 0]]) == 0.0
    assert context_drag([[0, 1, 0], [1, 0, 1]]) > 0.0
    assert context_drag([[0, 1, 0]]) == 0.0


# ---------------------------------------------------------------------
# C2: calibration metrics (v0.5)
# ---------------------------------------------------------------------
def test_calibration_ece():
    conf = [0.1, 0.2, 0.8, 0.9]
    out = [False, False, True, True]
    assert abs(expected_calibration_error(conf, out) - 0.15) < 1e-9
    assert expected_calibration_error([], []) == 0.0
    conf_bad = [0.9, 0.9, 0.9, 0.9]
    out_bad = [False, False, False, True]
    assert expected_calibration_error(conf_bad, out_bad) > expected_calibration_error(conf, out)


def test_calibration_brier():
    conf = [0.1, 0.2, 0.8, 0.9]
    out = [False, False, True, True]
    assert abs(brier_score(conf, out) - 0.025) < 1e-9
    assert brier_score([], []) == 0.0
    try:
        brier_score([0.5], [True, False])
        assert False
    except ValueError:
        pass


def test_calibration_reliability_diagram():
    conf = [0.1, 0.2, 0.8, 0.9]
    out = [False, False, True, True]
    rows = reliability_diagram(conf, out)
    assert len(rows) > 0
    for row in rows:
        assert 0.0 <= row["accuracy"] <= 1.0
        assert row["count"] > 0


def test_calibration_confidence_margin():
    conf = [0.1, 0.2, 0.8, 0.9]
    out = [False, False, True, True]
    assert confidence_margin(conf, out) > 0.0
    assert confidence_margin([], []) == 0.0


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
