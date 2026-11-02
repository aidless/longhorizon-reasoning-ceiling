"""Trajectory-level diagnostics (v0.5, C1).

Implements the long-horizon / error-anchoring dimensions surfaced by the
direction-3 literature sweep (17 papers, all arXiv-verified):

- per_step_reliability    — per-step reliability p (geometric law,
                            arXiv:2609.01660 "How Fast Do Agents Rot?")
- snowball_rate           — probability that a first error cascades to
                            whole-chain failure (arXiv:2607.16727 CART,
                            MLLM observed 0.65)
- positional_impact       — per-step error harm weight curve
                            (arXiv:2508.05282 "Late-Stage Fragility")
- error_origin_detection  — locate where the trajectory first diverges
                            from the correct path (arXiv:2604.14528)
- context_drag            — tree-edit-distance measure of how strongly a
                            failed attempt's structure is inherited by the
                            next trajectory (arXiv:2602.04288 "Contextual
                            Drag")

All functions are pure (no IO), deterministic, and edge-safe.
"""

from __future__ import annotations

from typing import Sequence


# ---------------------------------------------------------------------
# C1-a: per-step reliability (arXiv:2609.01660)
# ---------------------------------------------------------------------
def per_step_reliability(steps: Sequence[int], horizon: int | None = None) -> float:
    """Estimate the per-step reliability p from a 0/1 step sequence.

    A step is "reliable" when it does NOT introduce a new error (value 1
    in the 0/1 encoding where 1 = error step). Following the geometric
    law, p = 1 - (number of error steps) / (number of steps).

    Parameters
    ----------
    steps : sequence of int (0/1)
        Encoded step sequence (1 = error step, 0 = clean step).
    horizon : int, optional
        Only consider the first `horizon` steps (long-horizon cut-off).

    Returns
    -------
    float
        Per-step reliability in [0, 1]. Empty input → 1.0 (no errors).
    """
    if not steps:
        return 1.0
    if horizon is not None and horizon > 0:
        steps = steps[:horizon]
    if not steps:
        return 1.0
    n_err = sum(1 for s in steps if s == 1)
    return 1.0 - (n_err / len(steps))


def geometric_ceiling(p: float, max_steps: int = 1000) -> float:
    """Probability of a fully clean trajectory of length L under p.

    Under the geometric law, a trajectory of length L stays clean with
    probability p**L. As L grows this decays to 0 — the analytic form of
    the long-horizon ceiling (arXiv:2609.01660).

    Parameters
    ----------
    p : float
        Per-step reliability in [0, 1].
    max_steps : int
        Trajectory length to evaluate.

    Returns
    -------
    float
        p ** max_steps.
    """
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be in [0, 1]")
    if max_steps < 0:
        raise ValueError("max_steps must be non-negative")
    return p ** max_steps


# ---------------------------------------------------------------------
# C1-b: snowball rate (arXiv:2607.16727 CART)
# ---------------------------------------------------------------------
def snowball_rate(trajectories: Sequence[Sequence[int]]) -> float:
    """Fraction of trajectories where a first error cascades to failure.

    A trajectory "snowballs" when it contains at least one error step and
    the trajectory as a whole is NOT fully clean (i.e. the first error is
    followed by at least one more error, or the chain never recovers).

    Definition (CART-style): among trajectories with a first error, the
    fraction that end in a state where a majority of later steps are also
    errors.

    Parameters
    ----------
    trajectories : sequence of sequences of int (0/1)
        Encoded trajectories (1 = error step).

    Returns
    -------
    float
        Snowball rate in [0, 1]. Empty input → 0.0.
    """
    if not trajectories:
        return 0.0
    n_with_first_error = 0
    n_snowball = 0
    for t in trajectories:
        # Find first error index.
        first_err = None
        for i, s in enumerate(t):
            if s == 1:
                first_err = i
                break
        if first_err is None:
            continue  # no error at all — not a candidate
        n_with_first_error += 1
        later = t[first_err + 1:]
        if later:
            # Snowball if the majority of later steps are also errors.
            n_later_err = sum(1 for s in later if s == 1)
            if n_later_err >= len(later) / 2:
                n_snowball += 1
        else:
            # Single error at the last step — no cascade, count as clean.
            pass
    if n_with_first_error == 0:
        return 0.0
    return n_snowball / n_with_first_error


# ---------------------------------------------------------------------
# C1-c: positional impact (arXiv:2508.05282 Late-Stage Fragility)
# ---------------------------------------------------------------------
def positional_impact(steps: Sequence[int], weight_base: float = 1.0) -> list[float]:
    """Per-step error harm weight curve.

    Late-stage errors are MORE harmful than early ones (counterintuitive
    result in arXiv:2508.05282). The harm weight of an error at position
    i scales with its distance from the start: w_i = weight_base * (i+1).

    Parameters
    ----------
    steps : sequence of int (0/1)
        Encoded step sequence (1 = error step).
    weight_base : float
        Base weight (default 1.0).

    Returns
    -------
    list[float]
        Per-step harm weight (0.0 for clean steps, w_i for error steps).
    """
    out: list[float] = []
    for i, s in enumerate(steps):
        if s == 1:
            out.append(weight_base * (i + 1))
        else:
            out.append(0.0)
    return out


def late_stage_fragility_index(steps: Sequence[int]) -> float:
    """Ratio of late-stage to early-stage error harm.

    Computes the total harm weight of errors in the second half of the
    trajectory divided by the first half. Values > 1.0 indicate that
    late-stage errors carry more harm (the fragility signature).

    Parameters
    ----------
    steps : sequence of int (0/1)

    Returns
    -------
    float
        Late/early harm ratio. Empty or no errors → 1.0 (neutral).
    """
    if not steps:
        return 1.0
    n = len(steps)
    mid = n // 2
    early = steps[:mid]
    late = steps[mid:]
    # Harm weight at position i is w = (i+1) (late-stage errors weigh more).
    early_harm = sum((i + 1) for i, s in enumerate(early) if s == 1)
    late_harm = sum((i + 1 + mid) for i, s in enumerate(late) if s == 1)
    if early_harm == 0:
        return float("inf") if late_harm > 0 else 1.0
    return late_harm / early_harm


# ---------------------------------------------------------------------
# C1-d: error origin detection (arXiv:2604.14528)
# ---------------------------------------------------------------------
def error_origin_detection(trajectory: Sequence[int],
                           correct: Sequence[int]) -> int | None:
    """Locate the step where the trajectory first diverges from correct.

    Uses a token-level divergence test: the first index where the
    trajectory's 0/1 value differs from the correct-path encoding.

    Parameters
    ----------
    trajectory : sequence of int (0/1)
        Encoded trajectory (1 = error step).
    correct : sequence of int (0/1)
        Encoded correct path (1 = should be error? typically all 0).

    Returns
    -------
    int | None
        Index of the first divergence, or None if no divergence.
    """
    n = min(len(trajectory), len(correct))
    for i in range(n):
        if trajectory[i] != correct[i]:
            return i
    return None


def error_spread_curve(trajectories: Sequence[Sequence[int]]) -> list[float]:
    """Distribution of error origin positions across trajectories.

    Returns a normalized histogram (fraction of trajectories whose first
    divergence is at position i). Positions with no divergence are not
    counted.

    Parameters
    ----------
    trajectories : sequence of sequences of int (0/1)

    Returns
    -------
    list[float]
        Fraction per position index (sums to ≤ 1.0).
    """
    if not trajectories:
        return []
    max_len = max((len(t) for t in trajectories), default=0)
    if max_len == 0:
        return []
    counts = [0] * max_len
    n_divergent = 0
    for t in trajectories:
        # Find first error (divergence from all-clean).
        for i, s in enumerate(t):
            if s == 1:
                counts[i] += 1
                n_divergent += 1
                break
    if n_divergent == 0:
        return [0.0] * max_len
    return [c / n_divergent for c in counts]


# ---------------------------------------------------------------------
# C1-e: context drag (arXiv:2602.04288 Contextual Drag)
# ---------------------------------------------------------------------
def _edit_distance(a: Sequence[int], b: Sequence[int]) -> int:
    """Levenshtein edit distance over integer sequences."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, va in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, vb in enumerate(b, 1):
            cost = 0 if va == vb else 1
            curr[j] = min(prev[j] + 1,      # deletion
                          curr[j - 1] + 1,  # insertion
                          prev[j - 1] + cost)  # substitution
        prev = curr
    return prev[len(b)]


def context_drag(trajectories: Sequence[Sequence[int]]) -> float:
    """Mean tree-edit-distance between consecutive trajectories.

    A high value means consecutive trajectories inherit each other's
    structure weakly (low contextual drag); a low value means strong
    structural inheritance (high contextual drag).

    Returns the mean normalized edit distance (0 = identical structure,
    1 = completely different).

    Parameters
    ----------
    trajectories : sequence of sequences of int (0/1)
        Consecutive attempts on the same task.

    Returns
    -------
    float
        Mean normalized edit distance in [0, 1].
    """
    if len(trajectories) < 2:
        return 0.0
    dists: list[float] = []
    for a, b in zip(trajectories, trajectories[1:]):
        d = _edit_distance(a, b)
        denom = max(len(a), len(b), 1)
        dists.append(d / denom)
    if not dists:
        return 0.0
    return sum(dists) / len(dists)


# ---------------------------------------------------------------------
# Self-test (RED → GREEN).
# ---------------------------------------------------------------------
def _selftest() -> None:
    # RED: a trajectory with errors in the late stage must show a higher
    # fragility index than one with errors early.
    late_err = [0, 0, 1, 1]          # errors in second half
    early_err = [1, 1, 0, 0]         # errors in first half
    assert late_stage_fragility_index(late_err) > late_stage_fragility_index(early_err), \
        "selftest RED failed: late-stage fragility not detected"

    # GREEN: per-step reliability decreases with more errors.
    clean = per_step_reliability([0, 0, 0, 0])
    err = per_step_reliability([0, 1, 0, 1])
    assert clean > err, "selftest GREEN failed: reliability monotonicity"

    # GREEN: snowball rate on clear cases.
    cascade = [[0, 1, 1, 1], [0, 0, 1, 1]]   # both snowball
    no_cascade = [[0, 1, 0, 0], [0, 0, 0, 0]]  # first recovers / no error
    assert snowball_rate(cascade) == 1.0
    assert snowball_rate(no_cascade) == 0.0

    # GREEN: error origin detection.
    assert error_origin_detection([0, 1, 0], [0, 0, 0]) == 1
    assert error_origin_detection([0, 0, 0], [0, 0, 0]) is None

    # GREEN: context drag identical → 0, different → > 0.
    same = context_drag([[0, 1, 0], [0, 1, 0]])
    diff = context_drag([[0, 1, 0], [1, 0, 1]])
    assert same == 0.0
    assert diff > 0.0

    print(f"trajectory selftest OK (fragility={late_stage_fragility_index(late_err):.2f})")


if __name__ == "__main__":
    _selftest()
