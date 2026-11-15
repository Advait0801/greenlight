"""The USG screen must list every place a rule is broken (final review F3).

"Reasons you may cite" was de-duplicated by rule id only, so of two lines from vendors not on USG's list only one was
shown, while the drafted reason cites every place for a ticked rule. The frontend has no test runner, so this reads
the page source.
"""

from __future__ import annotations

from tests.conftest import REPO_ROOT

PAGE = REPO_ROOT / "frontend" / "src" / "pages" / "UsgScreen.tsx"


def test_reasons_are_kept_per_rule_and_place() -> None:
    source = PAGE.read_text(encoding="utf-8")
    assert "current.reasons.map((r) => [`${r.rule_id}|${r.where}`, r])" in source
    assert "current.reasons.map((r) => [r.rule_id, r])" not in source
    assert "key={`${r.rule_id}|${r.where}`}" in source
