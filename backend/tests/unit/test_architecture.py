"""Code that checks rules, dates and money must never import the AI client (CLAUDE.md: AI reads, code checks)."""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
# The only modules outside app/ai that may use the AI client: intake (reading uploads into typed JSON)
# and drafting. Add a module here only if it reads or drafts, never if it checks. Everything else under
# app/ (rules, services, deadlines, planner, API routes) is checked, whatever its file name.
AI_ALLOWED: set[Path] = {
    APP / "services" / "event_intake.py",  # reads event sentences (Phase 2)
    APP / "services" / "recognition_intake.py",  # reads constitutions (Phase 1)
}
# Money check (Phase 3): reading quotes and the fund, and drafting the application.
AI_ALLOWED |= {APP / "services" / "quote_intake.py", APP / "services" / "fund_reading.py", APP / "services" / "application_draft.py"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            if node.module == "app":  # from app import ai
                names.update(f"app.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) == "__import__" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                names.add(first.value)
    return names


def _uses_ai(path: Path) -> set[str]:
    return {name for name in _imports(path) if name in ("anthropic", "app.ai") or name.startswith(("app.ai.", "anthropic."))}


def test_only_intake_and_drafting_modules_import_the_ai_client() -> None:
    """Regression (phase 0 iteration 3, code audit L): the guard covers every module, not fixed file names."""
    for path in APP.rglob("*.py"):
        if APP / "ai" in path.parents or path in AI_ALLOWED:
            continue
        bad = _uses_ai(path)
        assert not bad, f"{path.relative_to(APP.parent)} imports {bad}; checking code never uses the AI"


def test_the_guard_sees_every_import_form(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    for line in ("from app import ai", "import app.ai.client", "from app.ai.schemas import ExtractedField", "import anthropic"):
        sample.write_text(line + "\n", encoding="utf-8")
        assert _uses_ai(sample), line


def test_only_the_ai_package_imports_the_sdk() -> None:
    for path in APP.rglob("*.py"):
        if APP / "ai" in path.parents:
            continue
        assert "anthropic" not in {name.split(".")[0] for name in _imports(path)}, path
