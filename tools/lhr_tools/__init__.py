"""lhr_tools — Long-Horizon Reasoning evaluation toolchain.

A reusable toolchain for measuring the key quantities in the
longhorizon-reasoning-ceiling project:

- anchor rate (early-error anchoring, FALCA 2610.28361)
- saturation point N* (TTSPM 2505.20522, Eq. 14)
- early-step credit precision (TRCA 2608.16156)
- verifier false-accept / false-reject (RHB 2605.02964)

Every public function is deterministic and testable.
"""

__version__ = "0.1.0"
