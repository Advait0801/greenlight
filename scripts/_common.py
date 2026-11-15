"""Shared helpers for the scripts in this folder.

Scripts run from the repository root with the backend's dependencies installed:

    python scripts/<name>.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
RULES_DIR = REPO_ROOT / "rules"
SOURCES_DIR = RULES_DIR / "sources"
EVAL_DIR = REPO_ROOT / "data" / "eval"
DEMO_DIR = REPO_ROOT / "data" / "demo"


def use_backend() -> None:
    """Make `import app...` work from a script."""
    path = str(BACKEND_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)
