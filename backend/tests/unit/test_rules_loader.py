"""The rule table: every rule has its source, every 'read' rule matches its snapshot exactly,
unverified rules are shown yellow, and malformed rules are rejected with a clear message."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app.rules import RuleLoadError, load_rules
from app.rules.snapshots import HEADER_END, load_manifest, normalize, snapshot_text
from tests.conftest import RULES_DIR

REQUIRED = ("source_url", "source_text", "effective_date", "verified")


@pytest.fixture(scope="module")
def ruleset():  # type: ignore[no-untyped-def]
    return load_rules(RULES_DIR)


def raw_rules() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name in ("funding", "events", "outside_money", "recognition"):
        out.extend(json.loads((RULES_DIR / f"{name}.json").read_text(encoding="utf-8"))["rules"])
    return out


def test_all_rule_files_load(ruleset) -> None:  # type: ignore[no-untyped-def]
    domains = {rule.domain for rule in ruleset}
    assert domains == {"funding", "events", "outside_money", "recognition"}
    assert len(ruleset) > 200


@pytest.mark.parametrize("field", REQUIRED)
def test_every_rule_has_required_field_in_the_file(field: str) -> None:
    missing = [rule.get("id") for rule in raw_rules() if not rule.get(field)]
    assert missing == []


def test_every_read_rule_matches_its_snapshot_exactly() -> None:
    """Independent of the loader: re-read each snapshot and look for the quote."""
    sources = load_manifest(RULES_DIR / "sources")
    failures = []
    for rule in raw_rules():
        if rule["verified"] != "read":
            continue
        source = sources[rule["source_url"].split("#")[0]]
        body = (RULES_DIR / "sources" / source.snapshot).read_text(encoding="utf-8").partition(HEADER_END)[2]
        if normalize(rule["source_text"]) not in normalize(body):
            failures.append(rule["id"])
    assert failures == []


def test_effective_date_is_the_source_version_date(ruleset) -> None:  # type: ignore[no-untyped-def]
    for rule in ruleset:
        source = ruleset.source_for(rule)
        assert source.version_date == rule.effective_date.isoformat(), rule.id


def test_open_questions_are_unverified_and_yellow(ruleset) -> None:  # type: ignore[no-untyped-def]
    # PROJECT_CONTEXT section 8: deadline table / academic weeks, Spring 2027 calendar,
    # approved vendor list, four funded events per semester.
    for rule_id in (
        "usg-academic-week-definition",
        "usc-academic-calendar-2026-27",
        "usg-vendor-list",
        "usg-events-per-semester-cap",
    ):
        assert ruleset.get(rule_id).verified == "unverified"
        assert ruleset.display_severity(rule_id) == "yellow"
        assert ruleset.uncertain_reasons(rule_id)


def test_rules_resting_on_unverified_rules_are_yellow(ruleset) -> None:  # type: ignore[no-untyped-def]
    for rule_id in ("usg-deadline-vendor", "usg-deadline-travel", "usg-no-funding-breaks", "classroom-requests-week-4"):
        rule = ruleset.get(rule_id)
        assert rule.verified == "read" and rule.severity == "red"
        assert ruleset.display_severity(rule_id) == "yellow"
        assert ruleset.uncertain_reasons(rule_id)


def test_nothing_is_ever_green(ruleset) -> None:  # type: ignore[no-untyped-def]
    assert {ruleset.display_severity(rule.id) for rule in ruleset} <= {"red", "yellow", "office_decides", "info"}


def test_known_source_conflicts_are_encoded(ruleset) -> None:  # type: ignore[no-untyped-def]
    pairs = {("tes-decorations-terms", "tes-decorations-faq"), ("tes-cancellation-large-terms", "tes-cancellation-large-faq")}
    for first, second in pairs:
        assert ruleset.get(first).conflicts_with == [second]
        assert ruleset.get(second).conflicts_with == [first]
    assert (ruleset.get("tes-decorations-terms").offset, ruleset.get("tes-decorations-faq").offset) == (3, 2)
    assert (ruleset.get("tes-cancellation-large-terms").offset, ruleset.get("tes-cancellation-large-faq").offset) == (3, 4)


def test_discretionary_rules_are_office_decides(ruleset) -> None:  # type: ignore[no-untyped-def]
    for rule_id in ("dps-security", "usg-over-4000-case-by-case", "special-event-insurance", "amplified-sound-outdoor"):
        assert ruleset.get(rule_id).severity == "office_decides"


def test_key_numbers_match_the_sources(ruleset) -> None:  # type: ignore[no-untyped-def]
    assert ruleset.get("usg-food-cap").params["max_usd_per_person"] == 35
    assert ruleset.get("usg-hotel-cap").params["max_usd_per_night"] == 400
    assert ruleset.get("usg-yearly-cap").params["max_usd_per_year"] == 8000
    assert ruleset.get("usg-venue-personnel-cap").params["max_usd"] == 4000
    assert (ruleset.get("minors-registration").offset, ruleset.get("minors-registration").unit) == (60, "days")
    assert (ruleset.get("tes-final-payment").offset, ruleset.get("tes-final-payment").unit) == (21, "days")
    assert (ruleset.get("social-dance-start").offset, ruleset.get("social-dance-start").unit) == (3, "months")
    assert (ruleset.get("usg-deadline-travel").offset, ruleset.get("usg-deadline-travel").unit) == (9, "academic_weeks")


def test_every_snapshot_in_the_manifest_exists_and_has_a_fetch_date() -> None:
    sources = load_manifest(RULES_DIR / "sources")
    raw = {entry["id"]: entry for entry in json.loads((RULES_DIR / "sources" / "manifest.json").read_text())["sources"]}
    for source in sources.values():
        assert source.fetched_at and source.sha256 and source.version_date, source.id
        assert snapshot_text(RULES_DIR / "sources", source), source.id
        if not source.fetchable:
            # A source scripts cannot fetch is only allowed as a labelled manual transcription.
            assert raw[source.id].get("manual") is True and source.note, source.id


def test_rules_resting_on_a_manual_snapshot_are_unverified(ruleset) -> None:  # type: ignore[no-untyped-def]
    rule = ruleset.get("usg-academic-week-definition")
    assert rule.params["deadline_table_snapshot"] == "usg-funding-deadlines.txt"
    assert rule.verified == "unverified"


# ---- normalisation ------------------------------------------------------------------------------


def test_normalize_collapses_whitespace_and_line_break_hyphens() -> None:
    assert normalize("full-\n  time  faculty") == "full-time faculty"
    assert normalize("fund‐\nraise") == "fund‐raise"
    assert normalize("a  \n\t b c") == "a b c"
    assert normalize("Sat - \nTue") == "Sat - Tue"  # a spaced dash is not a broken word
    assert normalize("ﬁle") == "file"  # ligature from PDF extraction


# ---- malformed rules are rejected with clear errors --------------------------------------------


def _edit(rules_dir: Path, file: str, change: Callable[[dict[str, Any]], None]) -> None:
    path = rules_dir / file
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _rule(data: dict[str, Any], rule_id: str) -> dict[str, Any]:
    return next(rule for rule in data["rules"] if rule["id"] == rule_id)


def _expect_problem(rules_dir: Path, *fragments: str) -> list[str]:
    with pytest.raises(RuleLoadError) as caught:
        load_rules(rules_dir)
    text = "\n".join(caught.value.problems)
    for fragment in fragments:
        assert fragment in text, text
    return caught.value.problems


@pytest.mark.parametrize("field", REQUIRED)
def test_rule_missing_a_required_field_does_not_load(rules_copy: Path, field: str) -> None:
    _edit(rules_copy, "funding.json", lambda d: _rule(d, "usg-food-cap").pop(field))
    _expect_problem(rules_copy, "usg-food-cap", f"missing {field}")


def test_one_bad_rule_stops_the_whole_table(rules_copy: Path) -> None:
    _edit(rules_copy, "events.json", lambda d: _rule(d, "minors-registration").update(verified="maybe"))
    problems = _expect_problem(rules_copy, "minors-registration", "verified")
    assert len(problems) == 1


def test_read_rule_whose_text_is_not_in_the_snapshot_is_rejected(rules_copy: Path) -> None:
    _edit(rules_copy, "funding.json", lambda d: _rule(d, "usg-food-cap").update(
        source_text="Food requests should not exceed a $40 per person maximum based on expected attendance."))
    _expect_problem(rules_copy, "usg-food-cap", "not in the snapshot")


def test_unverified_rule_may_paraphrase_but_needs_a_note(rules_copy: Path) -> None:
    def change(d: dict[str, Any]) -> None:
        rule = _rule(d, "usg-food-cap")
        rule.update(verified="unverified", source_text="Paraphrase: food is capped per person.")
        rule.pop("verification_note", None)

    _edit(rules_copy, "funding.json", change)
    _expect_problem(rules_copy, "usg-food-cap", "verification_note")


@pytest.mark.parametrize(
    ("change", "fragments"),
    [
        (lambda r: r.update(effective_date="2026-02-30"), ["effective_date"]),
        (lambda r: r.update(effective_date="2026-01-01"), ["differs from the source's version date"]),
        (lambda r: r.update(severity="green"), ["severity"]),
        (lambda r: r.update(source_url="http://example.com/x"), ["https"]),
        (lambda r: r.update(source_url="https://example.com/not-in-manifest"), ["not in rules/sources/manifest.json"]),
        (lambda r: r.update(id="Usg Food Cap"), ["lowercase"]),
        (lambda r: r.update(colour="red"), ["colour"]),
        (lambda r: r.update(triggers=["food", "fooood"]), ["not in vocabulary.json", "fooood"]),
        (lambda r: r.update(anchor="event_date", offset=2, unit="weeks", direction="before"), ["only allowed on deadline rules"]),
        (lambda r: r.update(depends_on=["no-such-rule"]), ["unknown rule 'no-such-rule'"]),
        (lambda r: r.update(conflicts_with=["usg-hotel-cap"]), ["does not list it back"]),
        (lambda r: r.update(params={"cap_quote": "$99 per person"}), ["is not part of source_text"]),
        (lambda r: r.update(params={"see_rules": ["ghost-rule"]}), ["unknown rule 'ghost-rule'"]),
        (lambda r: r.update(source_text=""), ["missing source_text"]),
        (lambda r: r.update(domain="events"), ["domain"]),
        (lambda r: r.update(trigger_mode="all"), ["at least two triggers"]),
    ],
)
def test_malformed_rule_is_rejected(rules_copy: Path, change: Callable[[dict[str, Any]], None], fragments: list[str]) -> None:
    _edit(rules_copy, "funding.json", lambda d: change(_rule(d, "usg-food-cap")))
    _expect_problem(rules_copy, *fragments)


def test_deadline_rule_without_offset_is_rejected(rules_copy: Path) -> None:
    _edit(rules_copy, "events.json", lambda d: _rule(d, "minors-registration").pop("offset"))
    _expect_problem(rules_copy, "minors-registration", "needs offset")


def test_duplicate_rule_id_is_rejected(rules_copy: Path) -> None:
    def change(d: dict[str, Any]) -> None:
        d["rules"].append(dict(_rule(d, "usg-food-cap")))

    _edit(rules_copy, "funding.json", change)
    _expect_problem(rules_copy, "already used")


def test_depends_on_loop_is_rejected(rules_copy: Path) -> None:
    def change(d: dict[str, Any]) -> None:
        _rule(d, "usg-food-cap")["depends_on"] = ["usg-hotel-cap"]
        _rule(d, "usg-hotel-cap")["depends_on"] = ["usg-food-cap"]

    _edit(rules_copy, "funding.json", change)
    _expect_problem(rules_copy, "loop")


def test_invalid_json_is_reported_with_position(rules_copy: Path) -> None:
    (rules_copy / "events.json").write_text('{"domain": "events", "rules": [', encoding="utf-8")
    _expect_problem(rules_copy, "events.json", "not valid JSON", "line 1")


def test_missing_rule_file_is_reported(rules_copy: Path) -> None:
    (rules_copy / "recognition.json").unlink()
    _expect_problem(rules_copy, "recognition.json", "not found")


def test_file_with_wrong_domain_is_rejected(rules_copy: Path) -> None:
    _edit(rules_copy, "outside_money.json", lambda d: d.update(domain="events"))
    _expect_problem(rules_copy, "outside_money.json", "expected 'outside_money'")


def test_rule_entry_that_is_not_an_object_is_reported(rules_copy: Path) -> None:
    _edit(rules_copy, "outside_money.json", lambda d: d["rules"].append("not a rule"))
    _expect_problem(rules_copy, "rules[", "expected a JSON object")


def test_missing_snapshot_file_rejects_read_rules(rules_copy: Path) -> None:
    (rules_copy / "sources" / "tes-faq.txt").unlink()
    _expect_problem(rules_copy, "snapshot file tes-faq.txt is missing")


def test_tampered_snapshot_rejects_rules_quoting_it(rules_copy: Path) -> None:
    path = rules_copy / "sources" / "usg-funding-guidelines.txt"
    path.write_text(path.read_text(encoding="utf-8").replace("$35 per person", "$45 per person"), encoding="utf-8")
    _expect_problem(rules_copy, "usg-food-cap", "not in the snapshot")


def test_broken_manifest_is_reported(rules_copy: Path) -> None:
    (rules_copy / "sources" / "manifest.json").write_text("[]", encoding="utf-8")
    _expect_problem(rules_copy, "manifest.json")
