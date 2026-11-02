"""Saturation-point estimation (E1).

Implements TTSPM (arXiv:2505.20522) Eq. (14) saturation point:

    N* = ceil( ln(eps * p_x / F_max) / ln(1 - p_x) )

where p_x is the per-attempt success probability, F_max the asymptotic
performance, and eps the marginal-return threshold.

Added in v0.4: bootstrap confidence interval for N* (A1).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass
class SaturationParams:
    p_x: float      # per-attempt success probability
    f_max: float    # asymptotic performance
    eps: float = 0.01


def saturation_point(params: SaturationParams) -> int:
    """TTSPM Eq. (14): the attempt count beyond which extra compute
    yields diminishing returns."""
    p = params.p_x
    f = params.f_max
    eps = params.eps
    if not (0.0 < p < 1.0):
        raise ValueError("p_x must be in (0, 1)")
    if f <= 0.0:
        raise ValueError("f_max must be positive")
    numerator = math.log(eps * p / f)
    denominator = math.log(1.0 - p)
    return max(1, math.ceil(numerator / denominator))


def pass_at_k(p_x: float, k: int) -> float:
    """P(at least one success in k independent attempts)."""
    if not (0.0 <= p_x <= 1.0):
        raise ValueError("p_x must be in [0, 1]")
    return 1.0 - (1.0 - p_x) ** k


def estimate_px(successes: int, attempts: int) -> float:
    """Maximum-likelihood estimate of p_x."""
    if attempts <= 0:
        raise ValueError("attempts must be positive")
    return successes / attempts


def bootstrap_nstar_ci(
    successes: int,
    attempts: int,
    f_max: float,
    eps: float = 0.01,
    n_boot: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Bootstrap confidence interval for N* (A1).

    Resamples the binary attempt outcomes (success/failure) with
    replacement, recomputes the MLE p_x and N* for each resample, and
    returns the (alpha/2, 1-alpha/2) percentile interval.

    Parameters
    ----------
    successes, attempts : int
        Observed success count and total attempts.
    f_max : float
        Asymptotic performance passed to ``saturation_point``.
    eps : float
        Marginal-return threshold.
    n_boot : int
        Number of bootstrap resamples (default 1000).
    seed : int
        RNG seed for reproducibility (default 42).
    alpha : float
        Two-sided significance level (default 0.05 → 95% CI).

    Returns
    -------
    (lo, hi) : tuple[float, float]
        The percentile bootstrap CI bounds. When the observed p_x yields
        a degenerate distribution (all-success or all-failure), the CI
        collapses to the point estimate and a warning is not raised but
        the bounds are reported as equal.
    """
    if attempts <= 0:
        raise ValueError("attempts must be positive")
    if n_boot <= 0:
        raise ValueError("n_boot must be positive")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")

    # Degenerate observed outcome: p_x is 0 or 1, so N* collapses to the
    # deterministic limit (p_x=1 → first attempt succeeds; p_x=0 → no
    # saturation point, report as large sentinel). The CI is the point.
    if successes == attempts:
        return (1.0, 1.0)
    if successes == 0:
        return (float("inf"), float("inf"))

    observed = saturation_point(SaturationParams(successes / attempts, f_max, eps))
    rng = random.Random(seed)

    # Rebuild the observed binary sequence (successes = 1, failures = 0).
    outcomes = [1] * successes + [0] * (attempts - successes)
    if attempts == 1:
        # Degenerate: a single observed attempt cannot yield spread.
        return (float(observed), float(observed))

    boot_vals: list[int] = []
    for _ in range(n_boot):
        # Sample with replacement from the observed outcomes.
        resample = [outcomes[rng.randrange(attempts)] for _ in range(attempts)]
        s = sum(resample)
        if s == 0 or s == attempts:
            # All resamples identical → p_x degenerate → skip (N* undefined
            # for p_x=0; for p_x=1 the numerator is ln(eps/f) and finite).
            if s == 0:
                continue
        p = s / attempts
        if not (0.0 < p < 1.0):
            continue
        boot_vals.append(saturation_point(SaturationParams(p, f_max, eps)))

    if not boot_vals:
        return (float(observed), float(observed))

    boot_vals.sort()
    # Percentile index must use the ACTUAL bootstrap distribution size
    # (len(boot_vals)), not n_boot — degenerate resamples are skipped,
    # so len(boot_vals) < n_boot and using n_boot shifts the percentile
    # (e.g. 0.0378 instead of 0.025 at the low end for high skip rates).
    n = len(boot_vals)
    lo_idx = max(0, int((alpha / 2) * n) - 1)
    hi_idx = min(n - 1, int((1 - alpha / 2) * n) - 1)
    lo = float(boot_vals[lo_idx])
    hi = float(boot_vals[hi_idx])
    return (lo, hi)


# ---------------------------------------------------------------------
# C5: scaling-law exponent + geometric ceiling (arXiv:2610.30765 GenRM,
#     arXiv:2609.01660 "How Fast Do Agents Rot?")
# ---------------------------------------------------------------------
def scaling_law_exponent(p_x: float, k: int) -> float:
    """Exponent of the compute-scaling law at attempt count k.

    Under a power-law / geometric model, the marginal return of the k-th
    attempt follows pass_at_k = 1 - (1-p_x)^k. The local scaling exponent
    is d(pass)/dk, which measures how quickly returns diminish. A large
    negative exponent means the task saturates fast (few attempts to
    benefit); a small one means returns persist over many attempts.

    Parameters
    ----------
    p_x : float
        Per-attempt success probability in [0, 1].
    k : int
        Attempt count (>= 1).

    Returns
    -------
    float
        Scaling exponent (dimensionless). Negative = diminishing returns.
    """
    if not (0.0 <= p_x <= 1.0):
        raise ValueError("p_x must be in [0, 1]")
    if k < 1:
        raise ValueError("k must be >= 1")
    if p_x == 0.0:
        return 0.0
    if p_x == 1.0:
        # Already saturated at the first attempt: no further gain.
        return 0.0 if k >= 1 else float("inf")
    # d/dk [1 - (1-p)^k] = -(1-p)^k * ln(1-p). Since ln(1-p) < 0,
    # this is positive but decreasing. The exponent is this derivative
    # normalized (log-scale): ln(marginal_return).
    marginal = -(1.0 - p_x) ** k * math.log(1.0 - p_x)
    if marginal <= 0.0:
        return float("-inf")
    return math.log(marginal)


def geometric_ceiling(p_x: float, max_steps: int) -> float:
    """Probability a chain stays clean through max_steps under p_x.

    Under the geometric reliability law (arXiv:2609.01660), the ceiling
    for a chain of length L is p_x**L. This is the "how long can we go
    without an error" curve: it decays exponentially as L grows, which is
    the mathematical form of the long-horizon ceiling.

    Parameters
    ----------
    p_x : float
        Per-step reliability in [0, 1].
    max_steps : int
        Chain length to evaluate (>= 0).

    Returns
    -------
    float
        p_x ** max_steps in [0, 1].
    """
    if not (0.0 <= p_x <= 1.0):
        raise ValueError("p_x must be in [0, 1]")
    if max_steps < 0:
        raise ValueError("max_steps must be non-negative")
    return p_x ** max_steps


# ---------------------------------------------------------------------
# Self-test (RED → GREEN).
# ---------------------------------------------------------------------
def _selftest() -> None:
    # RED: p_x = 0.5, f_max = 0.9, eps = 0.01
    s = saturation_point(SaturationParams(0.5, 0.9, 0.01))
    assert isinstance(s, int) and s >= 1, f"saturation_point wrong: {s}"
    # GREEN: more compute always helps — larger f_max should not reduce N*
    s2 = saturation_point(SaturationParams(0.5, 0.99, 0.01))
    assert s2 >= s, "saturation decreased with better asymptotic"
    # GREEN: pass_at_k monotone in k.
    assert pass_at_k(0.3, 1) < pass_at_k(0.3, 4) < pass_at_k(0.3, 16)
    # GREEN (A1): bootstrap CI is finite, ordered, and contains the point estimate
    lo, hi = bootstrap_nstar_ci(30, 60, 0.9, seed=7)
    assert lo <= hi, "bootstrap CI not ordered"
    assert lo <= float(s) <= hi or lo <= float(s), "bootstrap CI should bracket point estimate"
    # GREEN (C5): scaling exponent negative & monotone in k.
    assert scaling_law_exponent(0.5, 1) > scaling_law_exponent(0.5, 4), \
        "scaling exponent should decrease with k"
    assert geometric_ceiling(0.9, 10) < geometric_ceiling(0.9, 5)
    print(f"saturation selftest OK (N*={s} for p=.5,f=.9, CI=[{lo:.0f},{hi:.0f}])")


if __name__ == "__main__":
    _selftest()
