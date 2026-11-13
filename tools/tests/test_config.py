"""Config-layer tests (RED→GREEN).

Run: python3 tests/test_config.py
"""

from __future__ import annotations
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lhr_tools.config.loader import DEFAULTS, Config

DEFAULT_YAML = (Path(__file__).resolve().parent.parent
                / "lhr_tools" / "config" / "default.yaml")


def test_load_packaged_default_yaml():
    """YAML 加载路径：打包的 default.yaml 能读出完整配置。"""
    assert DEFAULT_YAML.exists(), f"缺少默认配置: {DEFAULT_YAML}"
    cfg = Config.load(DEFAULT_YAML)
    assert cfg.get("anchor", "frac") == 0.20
    assert cfg.get("anchor", "radius") == 0
    assert cfg.get("saturation", "f_max") == 0.9
    assert cfg.get("saturation", "eps") == 0.01
    assert cfg.get("dataset", "seed") == 42
    assert cfg.get("dataset", "n") == 100
    # 三节齐全，与内置 DEFAULTS 对齐。
    assert set(DEFAULTS) <= set(cfg.data)


def test_yaml_file_overrides_defaults():
    """YAML 里的值覆盖默认值，未出现的键保留默认。"""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "c.yaml"
        p.write_text("anchor:\n  frac: 0.35\n", encoding="utf-8")
        cfg = Config.load(p)
        assert cfg.get("anchor", "frac") == 0.35
        assert cfg.get("anchor", "radius") == 0
        assert cfg.get("saturation", "f_max") == 0.9


def test_yaml_without_pyyaml_raises_clear_error():
    """缺 pyyaml 时必须给出明确错误，而不是 JSONDecodeError。"""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "c.yaml"
        p.write_text("anchor:\n  frac: 0.35\n", encoding="utf-8")
        # sys.modules["yaml"] = None 让 import yaml 抛 ImportError。
        with mock.patch.dict(sys.modules, {"yaml": None}):
            try:
                Config.load(p)
            except RuntimeError as e:
                assert "pyyaml" in str(e).lower(), f"错误信息未提示 pyyaml: {e}"
            else:
                raise AssertionError("缺少 pyyaml 时应抛出 RuntimeError")


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
