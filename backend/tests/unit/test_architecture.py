"""Code that checks rules, dates and money must never import the AI client (CLAUDE.md: AI reads, code checks)."""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
NO_AI = [APP / "rules", APP / "services" / "rule_engine.py", APP / "services" / "deadlines.py", APP / "services" / "year_planner.py"]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_rule_code_never_imports_the_ai_client() -> None:
    files = [p for target in NO_AI if target.exists() for p in ([target] if target.is_file() else target.rglob("*.py"))]
    assert files, "expected at least app/rules to exist"
    for path in files:
        bad = {name for name in _imports(path) if name == "anthropic" or name.startswith(("app.ai", "anthropic."))}
        assert not bad, f"{path.relative_to(APP.parent)} imports {bad}"


def test_only_the_ai_package_imports_the_sdk() -> None:
    for path in APP.rglob("*.py"):
        if APP / "ai" in path.parents:
            continue
        assert "anthropic" not in {name.split(".")[0] for name in _imports(path)}, path
