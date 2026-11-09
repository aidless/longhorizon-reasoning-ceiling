"""Synthetic data generation.

Seeded rows for smoke tests. This is not model output.

``generate_realistic_rows`` draws an exploit rate or a credit accuracy
from numeric ranges written below. Those ranges are notes in this file.
They were not re-checked against a paper in the honesty pass, and the
generator does not replay a published dataset. See FAILURE_MODES.md.
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


# Numeric ranges stored in this file. Not a replay of a paper dataset.
_EXPLOIT_RANGE = (0.0, 0.139)
_CREDIT_ACCURACY = 0.85


def generate_realistic_rows(metric: str, n: int = 100, seed: int = 42,
                            **kwargs: Any) -> list[dict[str, Any]]:
    """Synthetic rows whose knobs are drawn from ranges in this file.

    Unlike ``generate`` (fixed default rates), this draw is:

      - verifier: exploit rate uniform on ``_EXPLOIT_RANGE``
      - credit: accuracy within 0.05 of ``_CREDIT_ACCURACY``
      - anchor: anchoring probability uniform on [0.3, 0.7]

    Default ``n`` is 100. The rows are still synthetic.
    """
    rng = random.Random(seed)

    if metric == "verifier":
        exploit_rate = rng.uniform(*_EXPLOIT_RANGE)
        quality = rng.uniform(0.75, 0.95)
        return generate_verifier_rows(n=n, seed=seed, exploit_rate=exploit_rate,
                                      verifier_quality=quality)
    if metric == "credit":
        accuracy = _CREDIT_ACCURACY + rng.uniform(-0.05, 0.05)
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
    """Dispatch to ``generate_realistic_rows`` (synthetic preset)."""
    fn = REALISTIC_GENERATORS.get(metric)
    if fn is None:
        raise ValueError(f"unknown metric: {metric}")
    return fn(n=n, seed=seed, **kwargs)
