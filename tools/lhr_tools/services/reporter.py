"""Report generation.

Turns one or more metric result dicts into a Markdown report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_DISCLAIMER = (
    "> Formats the metric JSON passed to this command. "
    "Not a live-model ceiling measurement."
)

_METRIC_TITLES = {
    "anchor": "早期误差锚定率",
    "saturation": "饱和点 N*",
    "credit": "早期步 credit 精度",
    "verifier": "验证器对抗鲁棒性",
}


def format_value(v: Any) -> str:
    """Format a scalar value for display."""
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def result_to_md(result: dict[str, Any]) -> str:
    """Render a single metric result dict as a Markdown table."""
    metric = result.get("metric", "unknown")
    title = _METRIC_TITLES.get(metric, metric)
    lines = [f"## {title}", ""]
    # Key metrics first, then metadata.
    meta_keys = {"metric", "n", "data_file"}
    for k, v in result.items():
        if k in meta_keys:
            continue
        lines.append(f"- **{k}**: {format_value(v)}")
    lines.append("")
    lines.append(f"*n = {result.get('n', '?')}，数据：`{result.get('data_file', '')}`*")
    lines.append("")
    return "\n".join(lines)


def generate_report(results: list[dict[str, Any]],
                    output: str | Path | None = None) -> str:
    """Generate a Markdown report from multiple results.

    If `output` is given, writes to file and returns the path as string.
    """
    parts = ["# 长程推理评估报告", "", _DISCLAIMER, ""]
    for r in results:
        parts.append(result_to_md(r))
    md = "\n".join(parts)
    if output is not None:
        p = Path(output)
        p.write_text(md, encoding="utf-8")
        return str(p)
    return md
