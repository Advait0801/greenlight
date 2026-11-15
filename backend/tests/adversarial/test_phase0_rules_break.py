"""Phase 0, iteration 2 (break): malformed rule files, manifest and snapshots.

Every test works on a private copy of rules/ (the `rules_copy` fixture) and describes the correct
behaviour: a malformed rule table is refused with a RuleLoadError that names the problem, never
loaded with a silently changed number, and never a crash with a raw Python exception.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.rules import RuleLoadError, load_rules
from tests.conftest import clear_caches


def _edit_rule(rules_dir: Path, file: str, rule_id: str, change: Callable[[dict[str, Any]], None]) -> None:
    path = rules_dir / file
    data = json.loads(path.read_text(encoding="utf-8"))
    change(next(rule for rule in data["rules"] if rule["id"] == rule_id))
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _edit_manifest(rules_dir: Path, change: Callable[[dict[str, Any]], None]) -> None:
    path = rules_dir / "sources" / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _refused(rules_dir: Path, *fragments: str) -> list[str]:
    """The table must be refused with a RuleLoadError (not any other exception) naming the problem."""
    with pytest.raises(RuleLoadError) as caught:
        load_rules(rules_dir)
    text = "\n".join(caught.value.problems)
    for fragment in fragments:
        assert fragment in text, text
    return caught.value.problems


# ---- type coercion turns a malformed number into a different deadline or cap -----------------------


@pytest.mark.parametrize("bad_offset", [True, "60", 60.0], ids=["boolean", "string", "float"])
def test_deadline_offset_of_the_wrong_type_is_refused(rules_copy: Path, bad_offset: object) -> None:
    """`"offset": true` currently loads as a 1-day deadline (60 days in the source); a string or a
    float is silently converted. An offset must be a JSON integer."""
    _edit_rule(rules_copy, "events.json", "minors-registration", lambda r: r.update(offset=bad_offset))
    _refused(rules_copy, "minors-registration", "offset")


def test_effective_date_given_as_a_number_is_refused(rules_copy: Path) -> None:
    """A Unix timestamp is not an ISO date; it is currently accepted and converted."""
    _edit_rule(rules_copy, "funding.json", "usg-food-cap", lambda r: r.update(effective_date=1792540800))
    _refused(rules_copy, "usg-food-cap", "effective_date")


def test_cap_that_contradicts_its_quoted_source_is_refused(rules_copy: Path) -> None:
    """The source text says $35 per person. A rule marked 'read' whose cap is 53 must not load:
    the number the checks use has to be the number in the quoted text."""
    _edit_rule(rules_copy, "funding.json", "usg-food-cap", lambda r: r["params"].update(max_usd_per_person=53))
    _refused(rules_copy, "usg-food-cap")


@pytest.mark.parametrize("bad_cap", ["35", -35, True], ids=["string", "negative", "boolean"])
def test_cap_that_is_not_a_positive_number_is_refused(rules_copy: Path, bad_cap: object) -> None:
    _edit_rule(rules_copy, "funding.json", "usg-food-cap", lambda r: r["params"].update(max_usd_per_person=bad_cap))
    _refused(rules_copy, "usg-food-cap")


def test_source_text_cut_in_the_middle_of_a_number_is_refused(rules_copy: Path) -> None:
    """'exceed a $3' is a substring of '...exceed a $35 per person...', so it passes as 'read' today,
    and the citation shown to the officer reads '$3'. An exact quote starts and ends on a word
    boundary of the snapshot."""
    _edit_rule(rules_copy, "funding.json", "usg-food-cap", lambda r: r.update(source_text="exceed a $3"))
    _refused(rules_copy, "usg-food-cap", "not in the snapshot")


def test_academic_week_deadline_without_its_dependency_is_not_shown_as_certain(rules_copy: Path) -> None:
    """PROJECT_CONTEXT 7: 'Academic week' is not defined, so no academic-week deadline may be shown
    as a certain red. Today certainty rests only on a hand-written depends_on; drop it and the rule
    shows red. Either refuse the table or show the rule yellow."""
    _edit_rule(rules_copy, "funding.json", "usg-deadline-vendor", lambda r: r.update(depends_on=[]))
    try:
        ruleset = load_rules(rules_copy)
    except RuleLoadError:
        return
    assert ruleset.display_severity("usg-deadline-vendor") == "yellow"


# ---- manifest and snapshots ----------------------------------------------------------------------


@pytest.mark.parametrize("bad_snapshot", [5, ["usg-funding-guidelines.txt"]], ids=["number", "list"])
def test_manifest_snapshot_of_the_wrong_type_is_a_load_error_not_a_crash(rules_copy: Path, bad_snapshot: object) -> None:
    """Currently raises TypeError ('unsupported operand type(s) for /')."""
    _edit_manifest(rules_copy, lambda d: d["sources"][0].update(snapshot=bad_snapshot))
    _refused(rules_copy, "snapshot")


def test_manifest_that_is_not_utf8_is_a_load_error_not_a_crash(rules_copy: Path) -> None:
    """Currently raises UnicodeDecodeError."""
    (rules_copy / "sources" / "manifest.json").write_bytes(b"\xff\xfe\x00 not a manifest")
    _refused(rules_copy, "manifest.json")


def test_snapshot_that_is_not_utf8_is_a_load_error_not_a_crash(rules_copy: Path) -> None:
    """Currently raises UnicodeDecodeError."""
    (rules_copy / "sources" / "tes-faq.txt").write_bytes(b"\xff\xfe\x00" + bytes(range(256)))
    _refused(rules_copy, "tes-faq")


def test_source_without_a_version_date_is_refused(rules_copy: Path) -> None:
    """rules/README.md: effective_date 'must equal version_date in the manifest'. Without a
    version_date the check is skipped and any effective_date loads."""
    _edit_manifest(rules_copy, lambda d: next(s for s in d["sources"] if s["id"] == "tes-faq").pop("version_date"))
    _refused(rules_copy, "version")


def test_app_starts_degraded_when_the_manifest_is_malformed(rules_copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """app/main.py: 'Start anyway so /health can explain the problem'. A manifest entry with a
    non-string snapshot currently crashes the app at startup instead."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    _edit_manifest(rules_copy, lambda d: d["sources"][0].update(snapshot=5))
    monkeypatch.setenv("RULES_DIR", str(rules_copy))
    clear_caches()
    try:
        with TestClient(create_app(), raise_server_exceptions=False) as broken:
            health = broken.get("/health")
            assert health.status_code == 503
            assert health.json()["rules"]["loaded"] is False
            assert broken.get("/rules").status_code == 503
    finally:
        monkeypatch.delenv("RULES_DIR")
        clear_caches()
