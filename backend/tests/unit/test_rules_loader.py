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
        "usg-vendor-list",
        "usg-events-per-semester-cap",
        "usc-business-days-definition",
        "usc-approved-caterers",
    ):
        assert ruleset.get(rule_id).verified == "unverified"
        assert ruleset.display_severity(rule_id) == "yellow"
        assert ruleset.uncertain_reasons(rule_id)


def test_rules_resting_on_unverified_rules_are_yellow(ruleset) -> None:  # type: ignore[no-untyped-def]
    for rule_id in ("usg-deadline-vendor", "usg-deadline-travel", "usg-post-event-evaluation", "usg-approved-vendor"):
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
    assert normalize("\ufb01le") != "file"  # no compatibility folding: a ligature is not "fi"
    assert normalize("\uff13\uff15") != "35"  # nor are full-width digits
    assert normalize("cafe\u0301") == normalize("caf\u00e9")  # same character, composed or not


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


def test_duplicate_json_keys_are_rejected(rules_copy: Path) -> None:
    path = rules_copy / "funding.json"
    text = path.read_text(encoding="utf-8")
    # Add a second "severity" to the first rule; plain json.loads would silently keep the last one.
    patched = text.replace('"severity": "yellow",', '"severity": "yellow", "severity": "info",', 1)
    assert patched != text
    path.write_text(patched, encoding="utf-8")
    _expect_problem(rules_copy, "funding.json", "appears twice")


def test_nan_in_params_is_rejected(rules_copy: Path) -> None:
    path = rules_copy / "funding.json"
    text = path.read_text(encoding="utf-8")
    patched = text.replace('"max_usd_per_person": 35', '"max_usd_per_person": NaN', 1)
    assert patched != text
    path.write_text(patched, encoding="utf-8")
    _expect_problem(rules_copy, "funding.json", "NaN is not allowed")


def test_empty_rule_file_is_rejected(rules_copy: Path) -> None:
    _edit(rules_copy, "outside_money.json", lambda d: d.update(rules=[]))
    _expect_problem(rules_copy, "outside_money.json", "has no rules")


def test_raw_files_match_the_manifest_and_re_derive_the_snapshots() -> None:
    """Every committed raw download has the recorded SHA-256 and re-extracts to the committed text."""
    import hashlib
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("fetch_sources", RULES_DIR.parent / "scripts" / "fetch_sources.py")
    assert spec and spec.loader
    sys.path.insert(0, str(RULES_DIR.parent / "scripts"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entries = json.loads((RULES_DIR / "sources" / "manifest.json").read_text())["sources"]
    for entry in entries:
        if entry.get("manual"):
            continue
        raw = (RULES_DIR / "sources" / entry["raw"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["id"]
        committed = (RULES_DIR / "sources" / entry["snapshot"]).read_text(encoding="utf-8").partition(HEADER_END)[2]
        derived = module.to_text(raw, entry["format"]).replace("\r\n", "\n").replace("\r", "\n")
        assert derived.strip() == committed.strip(), entry["id"]


def test_vendor_and_caterer_rules_rest_on_their_unverified_lists(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 1, M3): a rule that uses an unverified list must not show as certain."""
    assert "usg-vendor-list" in ruleset.get("usg-approved-vendor").depends_on
    assert "usc-approved-caterers" in ruleset.get("food-approved-provider").depends_on
    assert ruleset.display_severity("usg-approved-vendor") == "yellow"
    assert ruleset.display_severity("food-approved-provider") == "yellow"


def test_business_day_deadlines_rest_on_the_business_day_assumption(ruleset) -> None:  # type: ignore[no-untyped-def]
    business_day_rules = [rule for rule in ruleset if rule.unit == "business_days"]
    assert business_day_rules
    for rule in business_day_rules:
        assert "usc-business-days-definition" in rule.depends_on, rule.id
        assert ruleset.display_severity(rule.id) == "yellow", rule.id


def test_every_figure_in_a_message_is_in_the_quoted_source(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 1, L4): phone numbers in a message must come from the rule's own source text."""
    import re

    for rule in ruleset:
        for phone in re.findall(r"\d{3}-\d{3}-\d{4}", rule.message):
            assert phone in rule.source_text, (rule.id, phone)


def test_verification_notes_are_plain_language(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 1, L3): notes shown to officers carry no file paths or planning references."""
    for rule in ruleset:
        note = rule.verification_note or ""
        for developer_text in ("PROJECT_CONTEXT", "PLAN.md", "rules/", ".json", ".txt"):
            assert developer_text not in note, (rule.id, developer_text)


def test_confirmed_calendar_makes_calendar_only_rules_certain(ruleset) -> None:  # type: ignore[no-untyped-def]
    """The user confirmed the calendar on 2026-11-14; rules that rest only on it are now certain."""
    assert ruleset.get("usc-academic-calendar-2026-27").verified == "read"
    for rule_id in ("usg-no-funding-breaks", "social-events-not-study-days-finals"):
        assert ruleset.is_certain(rule_id), rule_id
        assert ruleset.display_severity(rule_id) == "red", rule_id


@pytest.mark.parametrize(
    ("file", "rule_id", "change"),
    [
        ("events.json", "lafd-division-5-permit", lambda p: p.update(tent_area_sqft_over=4500)),
        ("events.json", "tes-rso-deposits", lambda p: p["deposit_usd"].update(venue_outdoor=1)),
        ("events.json", "alcohol-thursday-saturday", lambda p: p.update(service_ends_hours_before_end=3)),
        ("events.json", "classroom-requests-week-4", lambda p: p.update(requests_open_week=9)),
        ("funding.json", "usg-fund-closure", lambda p: p.update(utilization_threshold_percent=75)),
    ],
)
def test_every_number_in_params_must_be_in_the_quoted_text(rules_copy: Path, file: str, rule_id: str, change) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 3, code audit H1): not only max_/min_/threshold_ keys are checked."""
    _edit(rules_copy, file, lambda d: change(_rule(d, rule_id)["params"]))
    _expect_problem(rules_copy, rule_id, "is not a number the quoted source text states")


def test_deadline_offset_must_be_in_the_quoted_text(rules_copy: Path) -> None:
    """Regression (phase 0 iteration 3, code audit M2): removing the offset check must fail a test."""
    _edit(rules_copy, "events.json", lambda d: _rule(d, "minors-registration").update(offset=61))
    _expect_problem(rules_copy, "minors-registration", "offset 61 is not a number the quoted source text states")


def test_usg_deadline_rules_pin_their_anchors_and_offsets(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 3, funding audit H1 and test gap): every USG deadline the sources
    give is encoded with its own anchor and offset, and the page's two deadlines are linked."""
    expected = {
        "usg-deadline-vendor": ("initial_payment_due_date", 6, "academic_weeks"),
        "usg-deadline-travel": ("initial_payment_due_date", 9, "academic_weeks"),
        "usg-page-deadline-event-date": ("event_date", 6, "academic_weeks"),
        "usg-page-deadline-nine-weeks-payment": ("initial_payment_due_date", 9, "academic_weeks"),
        "usg-faq-deadline-new-vendors-travel": ("event_date", 8, "academic_weeks"),
    }
    for rule_id, (anchor, offset, unit) in expected.items():
        rule = ruleset.get(rule_id)
        assert (rule.anchor, rule.offset, rule.unit, rule.direction) == (anchor, offset, unit, "before"), rule_id
    assert ruleset.get("usg-page-deadline-event-date").params["whichever_first_rules"] == ["usg-page-deadline-nine-weeks-payment"]
    assert ruleset.get("usg-deadline-vendor").conflicts_with == ["usg-page-deadline-event-date"]
    assert set(ruleset.get("usg-faq-deadline-new-vendors-travel").conflicts_with or []) == {"usg-deadline-travel", "usg-approved-vendor"}


def test_summer_usg_funding_is_flagged(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 3, funding audit H2): a USG-funded summer event is not a silent pass."""
    rule = ruleset.get("usg-faq-no-summer-funding")
    assert rule.kind == "blocked_period" and "usg_funding" in rule.triggers
    assert "summer" in rule.params["blocked"]
    assert ruleset.display_severity(rule.id) == "yellow"
    assert ruleset.get("usg-no-funding-breaks").params["also_blocks_submissions"] is True


def test_alcohol_ineligibility_is_about_budget_lines_not_events(ruleset) -> None:
    """Regression (phase 0 iteration 3, funding audit M7): alcohol served at an event is not a USG expense."""
    rule = ruleset.get("usg-ineligible-alcohol")
    assert rule.triggers == ["alcoholic_drinks"]
    assert "alcoholic_drinks" in ruleset.vocabulary["line_item_categories"]
    assert "alcohol" not in ruleset.vocabulary["line_item_categories"]


def test_venue_cap_checks_what_usg_is_asked_to_pay(ruleset) -> None:
    """Regression (phase 0 iteration 3, funding audit M6)."""
    rule = ruleset.get("usg-venue-personnel-cap")
    assert "usg_requested" in (rule.check or "")
    assert "for an event" not in rule.message


def test_sterno_is_not_banned_with_candles(ruleset) -> None:
    """Regression (phase 0 iteration 3, events audit H1): canned heat gets the fire permit and the
    office's guidelines, never the red candle ban."""
    open_flame = {rule.id for rule in ruleset if "open_flame" in rule.triggers}
    assert open_flame == {"lafd-division-5-permit", "sterno-guidelines"}
    assert ruleset.get("no-candles-flames").triggers == ["candles"]
    assert ruleset.get("sterno-guidelines").severity == "office_decides"


def test_due_date_placeholder_only_on_deadline_rules(rules_copy: Path) -> None:
    """Regression (phase 0 iteration 3, events audit M3): no made-up date behind a non-deadline rule."""
    _edit(rules_copy, "events.json", lambda d: _rule(d, "campus-filming").update(fix_template="Contact them by {due_date}."))
    _expect_problem(rules_copy, "campus-filming", "no deadline to compute it from")


def test_new_event_rules_from_the_third_audit(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 3, events audit M1, M2, M4, M5, M6, M7)."""
    assert ruleset.get("tes-outdoor-deposit-section-c2").conflicts_with == ["tes-rso-deposits"]
    assert ruleset.get("parking-reservation-required").conflicts_with == ["parking-transportation"]
    for rule_id in ("alcohol-no-sales", "alcohol-end-times", "alcohol-not-main-focus", "tabling-blocked-days"):
        assert rule_id in ruleset
    assert ruleset.get("classroom-requests-week-4").severity == "yellow"
    assert ruleset.get("tabling-limits").params["days_in_a_week_must_be_consecutive"] is True


def test_banned_verdicts_come_from_named_facts(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 3, outside-money audit M): every event or outside-money ban names
    the fact that breaks it, so the verdict never comes from the model's judgment."""
    facts = ruleset.vocabulary["facts"]
    for rule in ruleset:
        if rule.kind == "banned" and rule.domain in ("events", "outside_money"):
            fact = rule.params.get("violated_when")
            assert fact, rule.id
            assert fact in facts or any(fact in group for group in ruleset.vocabulary.values()), rule.id


def test_free_drawing_rules_are_required_steps(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 3, outside-money audit H2)."""
    rule = ruleset.get("free-drawing-wording")
    assert (rule.kind, rule.severity, rule.triggers) == ("requirement", "red", ["prize_drawing"])
    for words in ("free tickets", "never a 'raffle'", "beneficiary"):
        assert words in rule.message


def test_manual_deadline_table_is_intact_and_its_doubtful_rows_are_recorded(ruleset) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 0 iteration 3, outside-money audit H1 and M): the hand transcription matches its
    hash, every deadline is a Wednesday, the rows run Monday to Friday, and the rows a person must
    compare with the sheet are recorded on the rule that uses the table."""
    import csv
    import hashlib
    from datetime import date as Date

    entry = next(e for e in json.loads((RULES_DIR / "sources" / "manifest.json").read_text())["sources"] if e["id"] == "usg-funding-deadlines")
    body = (RULES_DIR / "sources" / entry["snapshot"]).read_text(encoding="utf-8").partition(HEADER_END)[2].lstrip("\n")
    assert hashlib.sha256(body.encode("utf-8")).hexdigest() == entry["sha256"]
    rows = list(csv.DictReader(line for line in body.splitlines() if not line.startswith("#")))
    short_after_recess = []
    for row in rows:
        start, end = Date.fromisoformat(row["event_week_start"]), Date.fromisoformat(row["event_week_end"])
        assert start.weekday() == 0, row
        for key in ("deadline_6_week", "deadline_9_week"):
            if row[key] not in ("", "N/A"):
                assert Date.fromisoformat(row[key]).weekday() == 2, row  # Wednesday
        if row["deadline_6_week"] not in ("", "N/A") and row["deadline_9_week"] not in ("", "N/A"):
            gap = (Date.fromisoformat(row["deadline_6_week"]) - Date.fromisoformat(row["deadline_9_week"])).days
            if start >= Date(2027, 3, 22) and gap != 21:
                short_after_recess.append(row["event_week_start"])
        assert end >= start
    params = ruleset.get("usg-academic-week-definition").params
    assert set(short_after_recess) <= set(params["rows_to_confirm"])
    assert "Saturday or Sunday" in params["date_to_row"]
