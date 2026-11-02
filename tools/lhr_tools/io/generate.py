"""Synthetic data generation for the toolchain.

Generates deterministic (seeded) trajectories / verdicts for smoke-testing
the toolchain without needing a real model run. Seed is fixed by default
so output is reproducible.

B5 adds ``generate_realistic_rows`` — a generator that reproduces the
empirical distribution reported in the literature (RHB arXiv:2605.02964
exploit-rate spread; TRCA arXiv:2608.16156 credit accuracy) so the
toolchain can be exercised on data that resembles real model output.
"""

from __future__ import annotations

import random
from typing import Any


def generate_anchor_rows(n: int = 10, seed: int = 42,
                         anchor_prob: float = 0.5) -> list[dict[str, Any]]:
    """Generate trajectory rows for the `anchor` metric.

    With probability `anchor_prob`, a trajectory is anchored (model locks
    onto an incorrect candidate); otherwise it wanders to the correct one.
    """
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        if rng.random() < anchor_prob:
            # Anchored: lock onto a wrong candidate (value 1, correct is 2).
            rows.append({"steps": [1] * rng.randint(4, 8), "correct": [2]})
        else:
            # Wandering: steps toward correct (value 4).
            rows.append({"steps": [1, 2, 3, 4], "correct": [4]})
    return rows


def generate_credit_rows(n: int = 10, seed: int = 42,
                         accuracy: float = 0.8) -> list[dict[str, Any]]:
    """Generate step-credit rows with a controllable accuracy."""
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        truth = "positive" if rng.random() < 0.5 else "negative"
        pred = truth if rng.random() < accuracy else (
            "negative" if truth == "positive" else "positive")
        rows.append({"pred": pred, "truth": truth})
    return rows


def generate_verifier_rows(n: int = 10, seed: int = 42,
                           exploit_rate: float = 0.3,
                           verifier_quality: float = 0.9) -> list[dict[str, Any]]:
    """Generate verifier verdict rows.

    verifier_quality = probability the verifier judges correctly
    (exploit → rejected, honest → accepted).
    """
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        is_exploit = rng.random() < exploit_rate
        if is_exploit:
            accepted = rng.random() >= verifier_quality  # exploit should be rejected
            score = 0.1 if not accepted else 0.8
        else:
            accepted = rng.random() < verifier_quality  # honest should be accepted
            score = 0.9 if accepted else 0.2
        rows.append({"is_exploit": is_exploit, "accepted": accepted,
                     "score": score})
    return rows


# Literature-calibrated parameters (B5).
# RHB arXiv:2605.02964: 13 frontier models, exploit rate 0%–13.9%.
# TRCA arXiv:2608.16156: credit accuracy typically 72%–96%.
_RHB_EXPLOIT_RANGE = (0.0, 0.139)
_TRCA_CREDIT_ACCURACY = 0.85  # mid-range


def generate_realistic_rows(metric: str, n: int = 100, seed: int = 42,
                            **kwargs: Any) -> list[dict[str, Any]]:
    """Generate data calibrated to literature-reported distributions.

    Unlike ``generate`` (which uses round default parameters), this
    reproduces the *empirical spread* seen in real model runs:

      - verifier: exploit rate drawn uniformly from [0%, 13.9%]
        (RHB arXiv:2605.02964, 13 frontier models)
      - credit: accuracy drawn from a narrow band around 85%
        (TRCA arXiv:2608.16156 effective-transition signal ~72%)
      - anchor: anchoring probability drawn from a wide band

    Parameters mirror ``generate`` but default ``n`` is larger (100) to
    give the toolchain a realistic sample size.
    """
    rng = random.Random(seed)

    if metric == "verifier":
        # Exploit rate uniform in the RHB-observed range.
        exploit_rate = rng.uniform(*_RHB_EXPLOIT_RANGE)
        # Verifier quality high but not perfect (real judges err).
        quality = rng.uniform(0.75, 0.95)
        return generate_verifier_rows(n=n, seed=seed, exploit_rate=exploit_rate,
                                      verifier_quality=quality)
    if metric == "credit":
        accuracy = _TRCA_CREDIT_ACCURACY + rng.uniform(-0.05, 0.05)
        return generate_credit_rows(n=n, seed=seed, accuracy=accuracy)
    if metric == "anchor":
        anchor_prob = rng.uniform(0.3, 0.7)
        return generate_anchor_rows(n=n, seed=seed, anchor_prob=anchor_prob)
    raise ValueError(f"unknown metric: {metric}")


GENERATORS = {
    "anchor": generate_anchor_rows,
    "credit": generate_credit_rows,
    "verifier": generate_verifier_rows,
}

REALISTIC_GENERATORS = {
    "anchor": lambda n, seed, **kw: generate_realistic_rows("anchor", n=n, seed=seed, **kw),
    "credit": lambda n, seed, **kw: generate_realistic_rows("credit", n=n, seed=seed, **kw),
    "verifier": lambda n, seed, **kw: generate_realistic_rows("verifier", n=n, seed=seed, **kw),
}


def generate(metric: str, n: int = 10, seed: int = 42,
             **kwargs: Any) -> list[dict[str, Any]]:
    """Dispatch to the appropriate generator."""
    fn = GENERATORS.get(metric)
    if fn is None:
        raise ValueError(f"unknown metric: {metric}")
    return fn(n=n, seed=seed, **kwargs)


def generate_realistic(metric: str, n: int = 100, seed: int = 42,
                       **kwargs: Any) -> list[dict[str, Any]]:
    """Dispatch to the literature-calibrated generator (B5)."""
    fn = REALISTIC_GENERATORS.get(metric)
    if fn is None:
        raise ValueError(f"unknown metric: {metric}")
    return fn(n=n, seed=seed, **kwargs)
