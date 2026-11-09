# Long-Horizon Reasoning Evaluation Toolchain

[![CI](https://github.com/aidless/longhorizon-reasoning-ceiling/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/longhorizon-reasoning-ceiling/actions/workflows/ci.yml)

lhr-tools is metric plumbing for ceiling probes: anchor, saturation, credit, verifier, trajectory, and calibration.
It runs on synthetic JSONL and on scalar parameters. It does not report a measured ceiling on a live model; no such run is in this repository.
STATUS: WORK-IN-PROGRESS — not A yet. A passing toolchain is not a research conclusion.

同一句话：这是天花板探针的指标管线，输入是合成 JSONL 或标量参数。仓库里没有实模型测量结果。STATUS: WORK-IN-PROGRESS — not A yet.

## Gaps (why this is not A)

- No live-model trajectories and no committed ceiling measurement. `experiments/` holds designs, not runs.
- Local formulas are not verified reproductions of the cited papers. The saturation expression is not TTSPM Eq. (14). Details are in [FAILURE_MODES.md](FAILURE_MODES.md).
- ArXiv ids other than the three spot-checks in FAILURE_MODES were not re-verified in this pass.
- `dataset --realistic` draws numbers from ranges written in code. A green test on that draw is not a paper replication.
- [analyses/lhr-report.md](analyses/lhr-report.md) is a two-row fixture render, not an evaluation.
- This package is not published on PyPI. The badge above is the GitHub Actions workflow, not a download or a score.
- PNG tests need matplotlib. Core metric functions do not import it. PyYAML is a package dependency for YAML config files.

## Claims locked to this tree

| Claim | Value |
| --- | --- |
| package version 0.5.1 | `tools/pyproject.toml` and `lhr_tools.__version__` |
| 13 CLI commands | subcommands of `lhr-tools` |
| 72/72 | module-level `test_*` functions under `tools/tests/` |

`tools/tests/test_drift.py` fails if a README above drifts from those three facts.

## Offline path

From a fresh clone, with network only for the one install (no model download). `python3 -m venv` needs the stdlib venv module (`python3-venv` on Debian/Ubuntu). Python is >= 3.10.

```bash
cd tools
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,viz]"
python -m pytest tests/ -q
python -m lhr_tools.cli selftest
lhr-tools anchor tests/data/anchor.jsonl
lhr-tools credit tests/data/credit.jsonl
lhr-tools verifier tests/data/verifier.jsonl
lhr-tools saturation --px 0.3 --fmax 0.9 --eps 0.01
```

`tests/data/*.jsonl` are two-row synthetic fixtures. `saturation` does not read a file. `dataset` writes more synthetic rows; the output directory must already exist. `verifier`, `anchor`, `credit`, `trajectory`, `calibration`, and `report` take positional input paths, not `--input`.

```bash
mkdir -p data
lhr-tools dataset anchor --n 10 --seed 42 --output data/anchor.jsonl
lhr-tools anchor data/anchor.jsonl > data/anchor.json
lhr-tools report data/anchor.json --output analyses/lhr-report.md
```

`report` without `--output` writes `analyses/lhr-report.md` under the current directory. The path is not resolved against the install location.

CI (`.github/workflows/ci.yml`) runs `python -m pytest tests/ -q` on Python 3.10, 3.11, and 3.12 after `pip install -e ".[dev,viz]"`, then `selftest` and the fixture commands above.

## Layout

```
README.md                 problem statement, claims, offline path
FAILURE_MODES.md          synthetic false greens and citation gaps
RESEARCH_PLAN.md          plan and changelog; not a result
experiments/              E1–E3 designs; not runs
analyses/lhr-report.md    fixture render
tools/                    lhr-tools package, tests, API notes
```

## License

MIT. See [LICENSE](LICENSE).
