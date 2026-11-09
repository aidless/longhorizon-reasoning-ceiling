"""Drift check: README claims vs this tree.

Run: python3 tests/test_drift.py
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import lhr_tools  # noqa: E402
from lhr_tools.cli import build_parser  # noqa: E402


def _cli_commands() -> set[str]:
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("CLI parser has no subcommands")


def _test_count() -> int:
    total = 0
    for path in sorted((TOOLS / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        total += sum(
            1
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )
    return total


def _pyproject_version() -> str:
    for line in (TOOLS / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise AssertionError("pyproject.toml has no version")


def test_claims_match_tree():
    """Version, CLI count, and test count in the READMEs match the tree."""
    version = _pyproject_version()
    assert lhr_tools.__version__ == version
    n_commands = len(_cli_commands())
    n_tests = _test_count()
    for name in ("README.md", "tools/README.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert f"package version {version}" in text, name
        assert f"{n_commands} CLI commands" in text, name
        assert f"{n_tests}/{n_tests}" in text, name
        assert "STATUS: WORK-IN-PROGRESS" in text, name
        for banned in ("零依赖", "零第三方", "zero-dependency"):
            assert banned not in text, f"{name} still says {banned}"
    root = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "STATUS: WORK-IN-PROGRESS — not A yet" in root
    assert "img.shields.io" not in root
    assert "pypi.org" not in root.lower()
    modes = (ROOT / "FAILURE_MODES.md").read_text(encoding="utf-8")
    assert "2505.20522" in modes
    assert "synthetic" in modes.lower()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = []
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
        except AssertionError as e:
            failed.append(t.__name__)
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
