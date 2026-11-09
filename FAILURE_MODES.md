# Failure modes

This file records ways the toolchain can look successful while not measuring a long-horizon reasoning ceiling. It does not add experiment results.

## Synthetic data can go green

`dataset` and `io/generate.py` draw seeded rows. `dataset --realistic` samples an exploit rate inside `[0, 0.139]` or a credit accuracy near `0.85`. Those endpoints are comments in the generator. They are not a replay of a paper's dataset, and a test that only checks "the draw landed inside the interval" passes for any generator that clamps to that interval.

The committed fixtures under `tools/tests/data/` are two rows each, written by hand for the CLI. `analyses/lhr-report.md` is the report command applied to `tests/data/anchor.jsonl`. Its anchor rate of 0.5 is that fixture, `n = 2`.

On `tests/data/verifier.jsonl` the CLI prints `auc_roc` 1.0 and `auprc` 0.25 together. `auc_roc` treats a lower score as the exploit detection. `_auprc` walks scores from high to low. The two summaries do not measure the same ranking. A 1.0 on this file is not evidence that every verifier number is saturated at perfect.

`selftest` checks hand-built examples inside each module. A green selftest means those assertions held. It does not mean a model was run.

## Metric definitions vs papers that were spot-checked

Checked against the arXiv HTML pages on 2026-11-09. No other id in this repository was opened in that pass. Older notes that say "全部 arXiv id 经 abs 页验号" are not re-established here.

### Saturation is not TTSPM Eq. (14)

[arXiv:2505.20522](https://arxiv.org/abs/2505.20522) is "Scaling over Scaling: Exploring Test-Time Scaling Plateau in Large Reasoning Models" (TTSPM). The HTML text gives Eq. (14) as

```
N* = ceil( ln(eps / (F_max * p_x)) / ln(1 - p_x) )
```

with the precondition `eps < F_max * p_x`.

`saturation_point` evaluates a different expression and then clamps to at least 1:

```
N* = max(1, ceil( ln(eps * p_x / F_max) / ln(1 - p_x) ))
```

`p_x` sits in the numerator with `eps`, not in the denominator with `F_max`.

On the documented parameters `p_x = 0.3`, `F_max = 0.9`, `eps = 0.01`, the local expression is 16 and Eq. (14) is 10. `tests/test_metrics.py` locks that pair so the two formulas are not described as the same number.

On the changelog's parameters `p_x = 0.0111`, `F_max = 0.9`, `eps = 0.01`, the local expression is 807. Those parameters violate `eps < F_max * p_x` (`0.01 < 0.00999` is false), so Eq. (14) is outside the region the paper derives. The changelog line that pairs 807 with "文献 808" is not a check of Eq. (14). This pass did not find an 808 in that equation.

### Anchor rate is a local predicate

[arXiv:2610.28361](https://arxiv.org/abs/2610.28361) is FALCA. The abstract and introduction discuss an agent anchoring on an incorrect candidate. They do not define "first 20% of steps" or a neighbourhood radius. `anchor_rate` is the local rule in `metrics/anchor.py`: an incorrect state in the early window, and every later step within `neighbourhood_radius` of it.

### Min-form credit is not PURE's return

[arXiv:2504.15275](https://arxiv.org/abs/2504.15275) is PURE ("Stop Summation: Min-Form Credit Assignment Is All Process Reward Model Needs for Reasoning"). Its min-form return is the minimum of future process rewards (worst step), with a different value after that step. `min_form_credit` is the minimum of per-step label matches (`1.0` if `pred == truth`, else `0.0`). Cohen's kappa and `credit_precision` are standard label agreement and accuracy. They are not a TRCA table.

`weakest_link_dominance` compares the minimum match bit with the all-match bit of the same pairs. Those two bits are equal for every non-empty input, so the function returns 1.0 whenever it is given any labels and 0.0 when given none. A green call is not evidence that a weakest step dominated a trajectory.

## Labels that were not re-checked

These strings appear in code comments, `RESEARCH_PLAN.md`, or `tools/docs/API.md`. This pass did not open them. Do not read an id as "the function implements that paper."

Verifier / calibration / trajectory comments cite, among others, `2605.02964`, `2606.03131`, `2609.01660`, `2607.16727`, `2508.05282`, `2604.14528`, `2602.04288`, `2604.23333`, `2604.09529`, `2604.10585`, and `2608.16156`.

`HARVE_PATTERNS` is a local tuple of 13 names. `pattern_robustness_profile` scores whatever dict the caller passes. It does not load a paper's attack set.

`context_drag` returns the mean normalized Levenshtein distance between consecutive integer sequences. The name says drag. The number goes up when consecutive sequences differ. It is not a tree-edit distance.

`RESEARCH_PLAN.md` is a plan plus a changelog of earlier toolchain versions (test totals 25, 29, 42, 47, 61, 66). Those lines are history. The current totals are the ones in the root README, checked by `tools/tests/test_drift.py`.

## What a green CI run is

CI installs this package with the `dev` and `viz` extras and runs pytest, `selftest`, and the three fixture files plus `saturation --px`. Matplotlib is there so the two PNG tests can write files. A green run means those checks passed on synthetic inputs. It does not mean E1, E2, or E3 was executed.
