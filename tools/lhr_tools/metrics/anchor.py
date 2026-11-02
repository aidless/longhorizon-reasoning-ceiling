"""Anchor-rate measurement (E1).

Defines the early-error anchoring rate per FALCA (arXiv:2610.28361):
a trajectory is "anchored" when the model locks onto an incorrect
candidate early (within the first 20% of steps) and stays in its
neighbourhood without exploring new regions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class Trajectory:
    """One model search trajectory.

    steps: the sequence of candidate states (as hashable objects).
    correct: the set of states that are genuinely correct answers.
    """

    steps: Sequence[object]
    correct: frozenset
    anchor_fraction: float = 0.20
    neighbourhood_radius: int = 0

    # --- helpers -----------------------------------------------------
    def _is_correct(self, state: object) -> bool:
        return state in self.correct

    def _within(self, a: object, b: object, radius: int) -> bool:
        """Neighbourhood test.

        radius == 0: strict equality — the model stays locked on the
        same candidate (no re-exploration).
        radius > 0: cheap distance test for integer states only.
        Non-integer states with radius > 0 raise a clear ValueError so
        the silent no-op (v0.4 review ⑤) is surfaced instead of being
        mistaken for "no re-exploration".
        """
        if a == b:
            return True
        if radius == 0:
            return False
        if isinstance(a, int) and isinstance(b, int):
            return abs(a - b) <= radius
        raise ValueError(
            f"neighbourhood_radius={radius} requires integer states, "
            f"got {type(a).__name__}/{type(b).__name__}")


def _is_anchored(traj: Trajectory) -> bool:
    """FALCA anchoring test on a single trajectory.

    The model anchors early if:
      1. within the first `anchor_fraction` of steps it commits to an
         incorrect candidate; AND
      2. all subsequent steps stay within `neighbourhood_radius` of that
         candidate (no re-exploration of a new region).
    """
    if len(traj.steps) < 3:
        return False
    k = max(2, int(len(traj.steps) * traj.anchor_fraction))
    for i in range(k):
        candidate = traj.steps[i]
        if traj._is_correct(candidate):
            continue
        # Candidate is incorrect: check that all later steps stay near it.
        later = traj.steps[i + 1:]
        if all(traj._within(s, candidate, traj.neighbourhood_radius)
               for s in later):
            return True
    return False


def anchor_rate(trajectories: Sequence[Trajectory]) -> float:
    """Fraction of trajectories that exhibit early-error anchoring."""
    if not trajectories:
        return 0.0
    n = sum(1 for t in trajectories if _is_anchored(t))
    return n / len(trajectories)


def anchored_ids(trajectories: Sequence[Trajectory]) -> list[int]:
    """Indices of anchored trajectories (for sub-group analysis)."""
    return [i for i, t in enumerate(trajectories) if _is_anchored(t)]


# ---------------------------------------------------------------------
# Self-test (RED → GREEN): run as `python -m lhr_tools.anchor`.
# ---------------------------------------------------------------------
def _selftest() -> None:
    good = Trajectory([1, 2, 3, 4], frozenset({4}))
    anchored = Trajectory([1, 1, 1, 1], frozenset({2}))
    # RED: an obviously anchored trajectory must be detected.
    assert _is_anchored(anchored), "selftest RED failed: anchored missed"
    # GREEN: a genuinely correct path must not be flagged.
    assert not _is_anchored(good), "selftest GREEN failed: false positive"
    # GREEN: rate on mixed set.
    rate = anchor_rate([good, anchored])
    assert abs(rate - 0.5) < 1e-9, f"rate wrong: {rate}"
    print("anchor selftest OK")


if __name__ == "__main__":
    _selftest()
