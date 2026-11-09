"""Calibration scores (local code, standard estimators).

``expected_calibration_error`` is equal-width ECE.
``brier_score`` is mean squared error of confidence against a binary
outcome. ArXiv ids previously listed in this module were not re-checked
and are not a claim that these functions reproduce those papers.
See FAILURE_MODES.md.
"""

from __future__ import annotations

from typing import Sequence


def expected_calibration_error(confidences: Sequence[float],
                               outcomes: Sequence[bool],
                               n_bins: int = 10) -> float:
    """Expected Calibration Error (ECE).

    Bins confidences into `n_bins` equally-spaced intervals and compares
    the mean confidence against the observed accuracy within each bin:

        ECE = sum_b (|B_b| / N) * |acc(B_b) - conf(B_b)|

    Parameters
    ----------
    confidences : sequence of float in [0, 1]
        Model-predicted probabilities.
    outcomes : sequence of bool
        Ground-truth binary outcomes.
    n_bins : int
        Number of equally-spaced bins (default 10).

    Returns
    -------
    float
        ECE in [0, 1]. Lower = better calibrated.
    """
    if len(confidences) != len(outcomes):
        raise ValueError("confidences and outcomes must have equal length")
    if not confidences:
        return 0.0
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    n = len(confidences)
    total = 0.0
    for b in range(n_bins):
        lo = b / n_bins
        hi = (b + 1) / n_bins
        # Last bin is closed on both ends (include c == 1.0).
        if b < n_bins - 1:
            idxs = [i for i, c in enumerate(confidences) if lo <= c < hi]
        else:
            idxs = [i for i, c in enumerate(confidences) if lo <= c <= hi]
        if not idxs:
            continue
        acc = sum(1 for i in idxs if outcomes[i]) / len(idxs)
        conf = sum(confidences[i] for i in idxs) / len(idxs)
        total += (len(idxs) / n) * abs(acc - conf)
    return total


def brier_score(confidences: Sequence[float],
                outcomes: Sequence[bool]) -> float:
    """Brier score: mean squared error between confidence and outcome.

    Parameters
    ----------
    confidences : sequence of float in [0, 1]
    outcomes : sequence of bool

    Returns
    -------
    float
        Brier score in [0, 1]. Lower = better.
    """
    if len(confidences) != len(outcomes):
        raise ValueError("confidences and outcomes must have equal length")
    if not confidences:
        return 0.0
    return sum((c - (1.0 if o else 0.0)) ** 2
               for c, o in zip(confidences, outcomes)) / len(confidences)


def reliability_diagram(confidences: Sequence[float],
                        outcomes: Sequence[bool],
                        n_bins: int = 10) -> list[dict[str, float]]:
    """Reliability diagram data (per-bin accuracy vs confidence).

    Returns a list of one dict per populated bin:
      {"bin_lo", "bin_hi", "confidence", "accuracy", "count"}
    """
    if len(confidences) != len(outcomes):
        raise ValueError("confidences and outcomes must have equal length")
    if not confidences:
        return []
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    n = len(confidences)
    rows: list[dict[str, float]] = []
    for b in range(n_bins):
        lo = b / n_bins
        hi = (b + 1) / n_bins
        # Last bin is closed on both ends (include c == 1.0).
        if b < n_bins - 1:
            idxs = [i for i, c in enumerate(confidences) if lo <= c < hi]
        else:
            idxs = [i for i, c in enumerate(confidences) if lo <= c <= hi]
        if not idxs:
            continue
        conf = sum(confidences[i] for i in idxs) / len(idxs)
        acc = sum(1 for i in idxs if outcomes[i]) / len(idxs)
        rows.append({"bin_lo": lo, "bin_hi": hi, "confidence": conf,
                     "accuracy": acc, "count": len(idxs)})
    return rows


def confidence_margin(confidences: Sequence[float],
                      outcomes: Sequence[bool],
                      threshold: float = 0.5) -> float:
    """Mean absolute confidence margin at the decision threshold.

    The margin is |confidence - threshold| for each sample; a high margin
    means the model is confidently (not hesitantly) deciding.

    Parameters
    ----------
    confidences : sequence of float in [0, 1]
    outcomes : sequence of bool (unused except length check)
    threshold : float
        Decision threshold (default 0.5).

    Returns
    -------
    float
        Mean absolute margin in [0, 1].
    """
    if len(confidences) != len(outcomes):
        raise ValueError("confidences and outcomes must have equal length")
    if not confidences:
        return 0.0
    return sum(abs(c - threshold) for c in confidences) / len(confidences)


# ---------------------------------------------------------------------
# Self-test (RED → GREEN).
# ---------------------------------------------------------------------
def _selftest() -> None:
    # RED: a perfectly calibrated model has low ECE.
    conf = [0.1, 0.2, 0.8, 0.9]
    out = [False, False, True, True]
    ece = expected_calibration_error(conf, out)
    assert ece < 0.20, f"selftest RED failed: perfect calibration ECE={ece:.3f}"

    # GREEN: an overconfident model has HIGHER ECE.
    conf_bad = [0.9, 0.9, 0.9, 0.9]  # all high confidence
    out_bad = [False, False, False, True]  # but only 1 true
    ece_bad = expected_calibration_error(conf_bad, out_bad)
    assert ece_bad > ece, "selftest GREEN failed: overconfidence not penalised"

    # GREEN: Brier score in [0, 1] and lower for better predictions.
    brier_good = brier_score(conf, out)
    brier_bad = brier_score(conf_bad, out_bad)
    assert 0.0 <= brier_good <= 1.0
    assert brier_good < brier_bad, "selftest GREEN failed: brier ordering"

    # GREEN: reliability diagram has entries.
    rows = reliability_diagram(conf, out)
    assert len(rows) > 0

    # GREEN: confidence margin positive.
    assert confidence_margin(conf, out) > 0.0

    print(f"calibration selftest OK (ECE={ece:.3f}, Brier={brier_good:.3f})")


if __name__ == "__main__":
    _selftest()
