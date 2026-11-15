"""Strict JSON reading for the rule table, calendar, manifest and test sets.

Python's json module silently keeps the last of two duplicate keys and accepts NaN and
Infinity. In a rule file either would change a rule without any error, so both are refused.
"""

from __future__ import annotations

import json
from typing import Any


class StrictJSONError(ValueError):
    pass


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictJSONError(f"the key '{key}' appears twice in one object")
        out[key] = value
    return out


def _no_constants(name: str) -> Any:
    raise StrictJSONError(f"{name} is not allowed")


def loads_strict(text: str) -> Any:
    """json.loads that rejects duplicate keys and NaN/Infinity. Raises json.JSONDecodeError for bad
    syntax and StrictJSONError for the two extra checks."""
    return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constants)
