"""Phase 0, iteration 4 (break): a 'read' rule whose deadline or limit no longer says what its quote says.

The loader checks that every number in a 'read' rule appears *somewhere* in its quoted source
text. It does not check that the number is paired with the right unit, direction or phrase, so a
rule can carry a different deadline or limit than the quote beside it and still load as certain
(and red). Each test changes one field on a private copy of rules/ (the `rules_copy` fixture) and
expects the table to be refused with a RuleLoadError that names the rule.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.rules import RuleLoadError, load_rules
from app.rules.snapshots import HEADER_END


def _edit_rule(rules_dir: Path, file: str, rule_id: str, change: Callable[[dict[str, Any]], None]) -> None:
    path = rules_dir / file
    data = json.loads(path.read_text(encoding="utf-8"))
    change(next(rule for rule in data["rules"] if rule["id"] == rule_id))
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _refused(rules_dir: Path, rule_id: str) -> None:
    try:
        ruleset = load_rules(rules_dir)
    except RuleLoadError as exc:
        assert any(rule_id in problem for problem in exc.problems), exc.problems
        return
    pytest.fail(
        f"'{rule_id}' loaded without error and is shown as {ruleset.display_severity(rule_id)} "
        f"(certain: {ruleset.is_certain(rule_id)}), although its deadline or limit differs from its quoted text"
    )


# ---- deadlines: the unit, the number-unit pair and the direction are not compared with the quote ----


@pytest.mark.parametrize(
    ("file", "rule_id", "unit"),
    [
        ("events.json", "approvals-two-weeks", "days"),  # "at least two weeks before" -> 2 days
        ("events.json", "social-dance-start", "weeks"),  # "at least 3 months before" -> 3 weeks
        ("events.json", "minors-registration", "hours"),  # "at least 60 days before" -> 60 hours
    ],
)
def test_deadline_unit_must_be_the_unit_the_quote_states(rules_copy: Path, file: str, rule_id: str, unit: str) -> None:
    """Today each of these loads as a certain red deadline, with the original quote shown beside a
    date that is days or weeks later than the source allows."""
    _edit_rule(rules_copy, file, rule_id, lambda r: r.update(unit=unit))
    _refused(rules_copy, rule_id)


def test_deadline_offset_must_be_the_number_given_for_its_unit(rules_copy: Path) -> None:
    """usg-incomplete-48-hours quotes "2 business days is equivalent to 48 hours". `offset: 2` with
    `unit: hours` passes because a 2 appears in the quote, though the quote never says 2 hours."""
    _edit_rule(rules_copy, "funding.json", "usg-incomplete-48-hours", lambda r: r.update(offset=2))
    _refused(rules_copy, "usg-incomplete-48-hours")


def test_deadline_direction_must_match_the_quote(rules_copy: Path) -> None:
    """"At least two weeks before the event" turned into "two weeks after" loads as certain."""
    _edit_rule(rules_copy, "events.json", "approvals-two-weeks", lambda r: r.update(direction="after"))
    _refused(rules_copy, "approvals-two-weeks")


# ---- limits: a number is accepted if it appears anywhere in the quote ----------------------------


@pytest.mark.parametrize(
    ("file", "rule_id", "key", "value"),
    [
        # "Amplified sound cannot exceed 90 dBA, when measured 45 feet from the source."
        ("events.json", "amplified-sound-90-dba", "max_dba", 45),
        # "You can table for two (2) consecutive days per week. You can not exceed six (6) days per month."
        ("events.json", "tabling-limits", "max_days_per_week", 6),
        # "Consist of at least 10 currently enrolled USC students, including 5 student officers."
        ("recognition.json", "recognition-ten-students", "min_students", 5),
    ],
)
def test_limit_must_be_the_number_its_own_phrase_states(
    rules_copy: Path, file: str, rule_id: str, key: str, value: int
) -> None:
    """Swapping a limit for another number from the same quote loads silently. A club of 5 students
    would then meet the 10-student recognition minimum."""
    _edit_rule(rules_copy, file, rule_id, lambda r: r["params"].update({key: value}))
    _refused(rules_copy, rule_id)


def test_number_written_as_a_string_in_params_is_checked(rules_copy: Path) -> None:
    """`tent_area_sqft_over: "4500"` (source: 450 Sq Ft) skips the number check because it is a
    string; code that does int() on it gets a tenfold threshold."""
    _edit_rule(rules_copy, "events.json", "lafd-division-5-permit", lambda r: r["params"].update(tent_area_sqft_over="4500"))
    _refused(rules_copy, "lafd-division-5-permit")


def test_negative_number_in_params_is_refused(rules_copy: Path) -> None:
    """`range_weeks: [3, -6]` passes because "3-6 weeks" contains the characters "-6"."""
    _edit_rule(rules_copy, "events.json", "tes-space-request", lambda r: r["params"].update(range_weeks=[3, -6]))
    _refused(rules_copy, "tes-space-request")


# ---- snapshots: the text a 'read' rule is matched against is not checked against its recorded hash --


def test_edited_snapshot_is_refused(rules_copy: Path) -> None:
    """Change "$35" to "$53" in the guidelines snapshot and in usg-food-cap. The rule still 'matches
    its snapshot exactly' and load_rules (and so validate_rules.py and the app) accepts a $53 food
    cap as read and certain. Only a unit test on the repository files compares snapshots with the
    manifest; the loader should refuse a snapshot whose text differs from what was recorded."""
    snapshot = rules_copy / "sources" / "usg-funding-guidelines.txt"
    text = snapshot.read_text(encoding="utf-8")
    head, sep, body = text.partition(HEADER_END)
    assert "$35 per person" in body
    snapshot.write_text(head + sep + body.replace("$35 per person", "$53 per person"), encoding="utf-8")

    def change(rule: dict[str, Any]) -> None:
        rule["source_text"] = rule["source_text"].replace("$35", "$53")
        rule["params"]["max_usd_per_person"] = 53

    _edit_rule(rules_copy, "funding.json", "usg-food-cap", change)
    with pytest.raises(RuleLoadError) as caught:
        load_rules(rules_copy)
    assert any("usg-funding-guidelines" in problem for problem in caught.value.problems), caught.value.problems


# ---- a rule file in rules/ that the loader never reads ----------------------------------------------


def test_unknown_rule_file_in_the_rules_folder_is_not_ignored(rules_copy: Path) -> None:
    """Exit criterion: "Every rule in rules/ has source_url, source_text, effective_date, verified."
    A new rules/travel.json (say, a later phase's travel rules) holding a rule with none of those
    fields is never read: load_rules and validate_rules.py report OK, and its obligations are
    silently missing from every check."""
    (rules_copy / "travel.json").write_text(
        json.dumps({"domain": "funding", "description": "Travel rules.", "rules": [{"id": "travel-traveller-details", "title": "Traveller details"}]}),
        encoding="utf-8",
    )
    with pytest.raises(RuleLoadError) as caught:
        load_rules(rules_copy)
    assert any("travel.json" in problem for problem in caught.value.problems), caught.value.problems
