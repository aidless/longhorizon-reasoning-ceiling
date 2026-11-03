"""Configuration loading.

Loads YAML/JSON config with defaults and environment-variable overrides.
YAML files require PyYAML; JSON files are parsed with the stdlib.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Default config (mirrors lhr_tools/config/default.yaml).
DEFAULTS: dict[str, Any] = {
    "anchor": {"frac": 0.20, "radius": 0},
    "saturation": {"f_max": 0.9, "eps": 0.01},
    "dataset": {"seed": 42, "n": 100},
}


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    """Load a config file (YAML or JSON, chosen by file suffix)."""
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                f"读取 YAML 配置 {path} 需要 PyYAML："
                "请先安装 pyyaml（pip install 'pyyaml>=6.0'）。"
            ) from exc
        return yaml.safe_load(text) or {}
    return json.loads(text) or {}


@dataclass
class Config:
    """Loaded configuration with defaults merged in."""

    data: dict[str, Any] = field(
        default_factory=lambda: copy.deepcopy(DEFAULTS))

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        """Load config from a file, else use defaults, then apply env overrides."""
        cfg = copy.deepcopy(DEFAULTS)
        if path is not None:
            p = Path(path)
            if p.exists():
                loaded = _load_yaml_or_json(p)
                # Deep merge loaded over defaults.
                for k, v in loaded.items():
                    if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
        # Env overrides: LHR_<SECTION>_<KEY>.
        env_prefix = "LHR_"
        for env_key, env_val in os.environ.items():
            if not env_key.startswith(env_prefix):
                continue
            parts = env_key[len(env_prefix):].lower().split("_")
            if len(parts) >= 2 and parts[0] in cfg:
                section = parts[0]
                key = "_".join(parts[1:])
                if isinstance(cfg[section], dict):
                    cfg[section][key] = _coerce(env_val)
        return cls(data=cfg)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a config value from a section."""
        return self.data.get(section, {}).get(key, default)

    def section(self, name: str) -> dict[str, Any]:
        return self.data.get(name, {})


def _coerce(value: str) -> Any:
    """Coerce env string to bool/int/float/str."""
    low = value.lower()
    if low in ("true", "yes", "1"):
        return True
    if low in ("false", "no", "0"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


# ---------------------------------------------------------------------
# Self-test (RED → GREEN).
# ---------------------------------------------------------------------
def _selftest() -> None:
    import tempfile

    # RED: env override must change the value.
    os.environ["LHR_ANCHOR_FRAC"] = "0.5"
    cfg = Config.load()
    assert cfg.get("anchor", "frac") == 0.5, "selftest RED failed: env override"
    del os.environ["LHR_ANCHOR_FRAC"]
    # GREEN: default restored after env cleared.
    cfg2 = Config.load()
    assert cfg2.get("anchor", "frac") == 0.20, "selftest GREEN failed: default"
    # GREEN: file loading.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                     delete=False) as f:
        json.dump({"anchor": {"frac": 0.30}}, f)
        p = f.name
    cfg3 = Config.load(p)
    assert cfg3.get("anchor", "frac") == 0.30
    print("config selftest OK")


if __name__ == "__main__":
    _selftest()
