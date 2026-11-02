"""Early-step credit precision (E2).

Measures how precisely the credit assigned to early steps matches human
annotations, using Cohen's kappa (inter-annotator agreement), following
the TRCA (arXiv:2608.16156) diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class StepCredit:
    """Credit assigned to one early step, compared to ground truth.

    pred: credit label from the method (e.g. 'positive'/'negative').
    truth: human-annotated label.
    """

    pred: str
    truth: str


def cohens_kappa(pairs: Sequence[StepCredit]) -> float:
    """Cohen's kappa over categorical labels."""
    if not pairs:
        return 0.0
    labels = sorted({p.pred for p in pairs} | {p.truth for p in pairs})
    n = len(pairs)
    # Observed agreement.
    obs = sum(1 for p in pairs if p.pred == p.truth) / n
    # Expected agreement (marginal products).
    exp = 0.0
    for lab in labels:
        p_pred = sum(1 for p in pairs if p.pred == lab) / n
        p_truth = sum(1 for p in pairs if p.truth == lab) / n
        exp += p_pred * p_truth
    denom = 1.0 - exp
    if denom == 0.0:
        return 1.0 if obs == 1.0 else 0.0
    return (obs - exp) / denom


def credit_precision(pairs: Sequence[StepCredit]) -> float:
    """Accuracy of credit labels against ground truth."""
    if not pairs:
        return 0.0
    return sum(1 for p in pairs if p.pred == p.truth) / len(pairs)


# ---------------------------------------------------------------------
# C4: min-form credit + weakest-link dominance (arXiv:2504.15275 PURE)
# ---------------------------------------------------------------------
def min_form_credit(pairs: Sequence[StepCredit]) -> float:
    """Min-form credit: minimum over per-step precision.

    PURE (arXiv:2504.15275) shows credit assignment via a min-form
    operator is more robust to early-step information asymmetry. The
    min-form credit is the minimum over steps of per-step precision
    (1.0 if the step's credit matches ground truth, else 0.0).

    This captures the "weakest link" view: a chain's credit is only as
    strong as its weakest step.

    Parameters
    ----------
    pairs : sequence of StepCredit

    Returns
    -------
    float
        Min-form credit in [0, 1].
    """
    if not pairs:
        return 0.0
    step_precisions = [1.0 if p.pred == p.truth else 0.0 for p in pairs]
    return min(step_precisions)


def weakest_link_dominance(pairs: Sequence[StepCredit]) -> float:
    """Fraction of trajectories where the weakest link determines outcome.

    In a PURE-style analysis, the weakest step (lowest per-step
    reliability) dominates the chain's success. This function reports the
    fraction of pairs where the minimum step precision equals the
    chain-level outcome (i.e. the weakest link is the binding constraint).

    Parameters
    ----------
    pairs : sequence of StepCredit

    Returns
    -------
    float
        Weakest-link dominance in [0, 1].
    """
    if not pairs:
        return 0.0
    step_precisions = [1.0 if p.pred == p.truth else 0.0 for p in pairs]
    weakest = min(step_precisions)
    chain_outcome = 1.0 if all(p.pred == p.truth for p in pairs) else 0.0
    # Weakest link dominates if its precision equals the chain outcome.
    return 1.0 if weakest == chain_outcome else 0.0


# ---------------------------------------------------------------------
# Self-test (RED → GREEN).
# ---------------------------------------------------------------------
def _selftest() -> None:
    # RED: perfectly mismatched labels → kappa < 0.5.
    bad = [StepCredit("positive", "negative") for _ in range(10)]
    assert cohens_kappa(bad) < 0.5, "selftest RED failed: bad labels not penalised"
    # GREEN: perfect agreement → kappa ≈ 1.
    good = [StepCredit("positive", "positive") for _ in range(5)] + \
           [StepCredit("negative", "negative") for _ in range(5)]
    assert cohens_kappa(good) > 0.9, f"kappa wrong: {cohens_kappa(good)}"
    # GREEN: accuracy also reflects agreement.
    assert credit_precision(good) == 1.0
    # GREEN (C4): min-form credit = 1 on perfect, 0 on any mismatch.
    assert min_form_credit(good) == 1.0
    mixed = [StepCredit("positive", "positive"), StepCredit("negative", "positive")]
    assert min_form_credit(mixed) == 0.0
    assert weakest_link_dominance(mixed) == 1.0
    print(f"credit selftest OK (kappa={cohens_kappa(good):.2f})")


if __name__ == "__main__":
    _selftest()
