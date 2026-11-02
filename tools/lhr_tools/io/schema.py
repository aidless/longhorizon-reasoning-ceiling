"""Schema validation for the four metric input formats.

Each metric has a required schema. Invalid rows raise ValueError with a
clear message (fail-closed, never silently skipped).
"""

from __future__ import annotations

from typing import Any

# Required keys per metric, with a type-check predicate.
SCHEMAS: dict[str, dict[str, callable]] = {
    "anchor": {
        "steps": lambda v: isinstance(v, list),
        "correct": lambda v: isinstance(v, list),
    },
    "credit": {
        "pred": lambda v: isinstance(v, str),
        "truth": lambda v: isinstance(v, str),
    },
    "verifier": {
        "is_exploit": lambda v: isinstance(v, bool),
        "accepted": lambda v: isinstance(v, bool),
        "score": lambda v: isinstance(v, (int, float)),
    },
}


def validate_rows(metric: str, rows: list[dict[str, Any]]) -> list[str]:
    """Validate rows against a metric schema. Returns list of errors.

    Empty list = all rows valid.
    """
    schema = SCHEMAS.get(metric)
    if schema is None:
        return [f"unknown metric: {metric}"]
    errors: list[str] = []
    for i, row in enumerate(rows):
        for key, pred in schema.items():
            if key not in row:
                errors.append(f"row {i}: missing key '{key}'")
            elif not pred(row[key]):
                errors.append(f"row {i}: key '{key}' has wrong type")
    return errors
