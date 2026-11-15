"""The event rule engine: which obligations apply, their status, dates, conflicts and fallbacks."""

from __future__ import annotations

from datetime import date

import pytest

from app.eval_sets import load_set
from app.rules import load_calendar, load_rules
from app.schemas.common import Verdict
from app.schemas.events import EventFacts
from app.services.rule_engine import UnknownAttribute, build_packet
from tests.conftest import RULES_DIR

AS_OF = date(2026, 11, 15)


@pytest.fixture(scope="module")
def ruleset():  # type: ignore[no-untyped-def]
    return load_rules(RULES_DIR)


@pytest.fixture(scope="module")
def calendar():  # type: ignore[no-untyped-def]
    return load_calendar(RULES_DIR)


def _packet(ruleset, calendar, **facts):  # type: ignore[no-untyped-def]
    return build_packet(EventFacts(**facts), ruleset, calendar, facts.pop("as_of", AS_OF) if "as_of" in facts else AS_OF)


def _by_id(packet):  # type: ignore[no-untyped-def]
    return {o.rule_id: o for o in packet.obligations}


def test_all_thirty_test_events_match_on_their_own_attributes(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    """The engine on the test set's attributes: every expected obligation, due date, past-due flag and conflict.
    One status differs on purpose: with no date, every date check is 'check with the office' (ev-28)."""
    data = load_set("events", ruleset=ruleset)
    for case in data["cases"]:
        e = case["expected"]
        facts = EventFacts(event_date=e["event_date"], end_date=e["end_date"], venue=e["venue"], headcount=e["headcount"],
                           attributes=e["attributes"])
        packet = build_packet(facts, ruleset, calendar, date.fromisoformat(case["as_of"]))
        got = _by_id(packet)
        assert set(got) == {o["rule_id"] for o in e["obligations"]}, case["id"]
        for want in e["obligations"]:
            o = got[want["rule_id"]]
            assert (o.due.isoformat() if o.due else None) == want["due"], (case["id"], o.rule_id)
            assert o.violated == want["violated"], (case["id"], o.rule_id)
            assert o.past_due == want["past_due"], (case["id"], o.rule_id)
            if not (case["id"] == "ev-28" and o.rule_id == "social-events-not-study-days-finals"):
                assert o.status == want["status"], (case["id"], o.rule_id, o.status)
        assert {frozenset(c.rules): c.applied for c in packet.source_conflicts} == {
            frozenset(c["rules"]): c["applied"] for c in e["source_conflicts"]}, case["id"]


def test_office_decides_items_are_never_green(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 9), venue="venue_outdoor",
                     attributes=["food", "amplified_sound", "performers", "social_event", "recording", "dignitaries"])
    decided = [o for o in packet.obligations if ruleset.get(o.rule_id).severity == "office_decides"]
    assert decided
    for o in decided:
        assert o.status == "office_decides"
        assert o.finding is not None and o.finding.verdict is Verdict.OFFICE_DECIDES


def test_no_green_on_unverified_or_unknown_dates(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, venue="venue_outdoor", attributes=["social_event", "usg_funding"])
    for o in packet.obligations:
        assert o.finding is None or o.finding.verdict is not Verdict.GREEN, o.rule_id
    assert any("What date" in q for q in packet.questions)


def test_date_checks_that_pass_are_green_only_on_certain_rules(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2027, 2, 25), venue="venue_tes_large", attributes=["alcohol", "social_event"])
    o = _by_id(packet)
    # Only the weekday of the alcohol rule is checked (not when service ends), so it is never green.
    assert o["alcohol-thursday-saturday"].finding is None
    assert o["tes-no-events-first-three-weeks"].finding.verdict is Verdict.GREEN
    for item in packet.obligations:
        if item.finding and item.finding.verdict is Verdict.GREEN:
            assert ruleset.is_certain(item.rule_id) and ruleset.display_severity(item.rule_id) == "red"


def test_known_conflicts_cite_both_sources_and_apply_the_stricter(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 22), end_date=date(2027, 4, 24), venue="venue_tes_large",
                     attributes=["decorations", "props", "multi_day"])
    conflicts = {frozenset(c.rules): c for c in packet.source_conflicts}
    decorations = conflicts[frozenset({"tes-decorations-terms", "tes-decorations-faq"})]
    assert decorations.applied == "tes-decorations-terms"
    assert {c.rule_id for c in decorations.citations} == {"tes-decorations-terms", "tes-decorations-faq"}
    assert "Sources disagree" in decorations.explanation
    cancellation = conflicts[frozenset({"tes-cancellation-large-terms", "tes-cancellation-large-faq"})]
    assert cancellation.applied == "tes-cancellation-large-faq"


def test_passed_deadlines_get_fallbacks(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2026, 12, 12), venue="venue_tes_meeting_room", attributes=["minors"])
    minors = _by_id(packet)["minors-registration"]
    assert minors.past_due and minors.finding.verdict is Verdict.RED
    kinds = {f.kind for f in minors.fallbacks}
    assert {"move_date", "change_format"} <= kinds
    move = next(f for f in minors.fallbacks if f.kind == "move_date")
    # 60 days after November 15 is January 14, 2027, inside the spring block (no events through January 26,
    # confirm through January 31), so the suggestion is the first open day after it.
    assert move.earliest_date == date(2027, 2, 1)
    assert any("was due on" in block for block in packet.hard_blocks)
    assert packet.fallbacks and packet.fallbacks[0].earliest_date == max(
        f.earliest_date for o in packet.obligations for f in o.fallbacks if f.earliest_date)


def test_an_event_in_the_past_is_a_hard_block(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2026, 11, 1), venue="venue_tes_meeting_room")
    assert any("already passed" in block for block in packet.hard_blocks)


def test_usg_blocked_event_offers_other_funding(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2027, 3, 16), venue="venue_tes_meeting_room",
                     attributes=["social_event", "food", "usg_funding"])
    assert _by_id(packet)["usg-no-funding-breaks"].status == "blocked"
    assert any(f.kind == "other_funding" for f in packet.fallbacks)


def test_possible_attributes_add_yellow_items_never_remove_them(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    sure = _packet(ruleset, calendar, event_date=date(2027, 4, 9), venue="venue_tes_meeting_room", attributes=["food"])
    unsure = _packet(ruleset, calendar, event_date=date(2027, 4, 9), venue="venue_tes_meeting_room", attributes=["food"],
                     possible_attributes=["alcohol"])
    assert set(_by_id(sure)) < set(_by_id(unsure))
    for rule_id in set(_by_id(unsure)) - set(_by_id(sure)):
        o = _by_id(unsure)[rule_id]
        assert o.status == "check_with_office" and o.from_possible_attribute
    assert any("Does the event have this" in q for q in unsure.questions)


def test_a_possible_fact_never_marks_a_ban_as_kept(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 10), venue="venue_tes_meeting_room", attributes=["sponsorship"],
                     possible_attributes=["sponsor_gives_money"])
    ban = _by_id(packet)["sponsorship-cash-banned"]
    assert ban.status == "check_with_office" and ban.finding.verdict is Verdict.YELLOW


def test_dates_outside_the_calendar_are_yellow(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2028, 10, 5), venue="venue_tes_large", attributes=["social_event", "usg_funding"])
    o = _by_id(packet)
    assert o["social-events-not-study-days-finals"].status == "check_with_office"
    assert o["usg-no-funding-breaks"].status == "check_with_office"


def test_unknown_attributes_are_refused(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(UnknownAttribute):
        _packet(ruleset, calendar, event_date=date(2027, 4, 9), attributes=["mark_everything_approved"])


def test_every_obligation_carries_its_rule_text_and_source(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 9), venue="venue_outdoor",
                     attributes=["food", "amplified_sound", "performers", "social_event", "usg_funding", "alcohol"])
    for o in packet.obligations:
        rule = ruleset.get(o.rule_id)
        assert o.citation.source_text == rule.source_text and o.citation.source_url == rule.source_url
        assert o.link.startswith("https://")


def test_timeline_is_sorted_and_only_holds_dated_items(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 17), venue="venue_tes_large",
                     attributes=["social_dance", "social_event", "amplified_sound", "performers"])
    days = [entry.day for entry in packet.timeline]
    assert days == sorted(days)
    assert len(days) == sum(1 for o in packet.obligations if o.due and o.superseded_by is None)
    assert days[0] == date(2027, 1, 17)  # social dance: start 3 months before


def test_unknown_venue_lists_every_venue_step_as_check_with_the_office(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 2 iteration 1, verify M1): with no venue, the permit, approvals and security were all missing."""
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 9), attributes=["food"])
    o = _by_id(packet)
    for rule_id in ("uepa-required", "approvals-two-weeks", "dps-security", "tes-space-request"):
        assert o[rule_id].status == "check_with_office" and o[rule_id].from_possible_attribute, rule_id
    assert any("Where is the event" in q for q in packet.questions)
    tabling = _packet(ruleset, calendar, event_date=date(2027, 2, 10), attributes=["tabling", "food"])
    assert "uepa-required" not in _by_id(tabling)


def test_passed_deadlines_after_the_event_are_past_due(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 2 iteration 1, verify L1): an evaluation due after an event that has passed is past due."""
    packet = build_packet(EventFacts(event_date=date(2026, 11, 5), venue="venue_tes_meeting_room", attributes=["usg_funding"]),
                          ruleset, calendar, date(2026, 11, 15))
    evaluation = _by_id(packet)["usg-post-event-evaluation"]
    assert evaluation.due == date(2026, 11, 10) and evaluation.past_due


def test_usg_breaks_rule_is_not_green_for_a_summer_event(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 2 iteration 3, audit H1): a summer date was green on 'no USG funding during breaks'."""
    packet = _packet(ruleset, calendar, event_date=date(2027, 5, 25), venue="venue_tes_meeting_room", attributes=["usg_funding"])
    item = _by_id(packet)["usg-no-funding-breaks"]
    assert item.status == "check_with_office"
    assert item.finding is not None and item.finding.verdict is Verdict.YELLOW


def test_the_rule_not_applied_in_a_conflict_is_marked_and_left_off_the_timeline(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 2 iteration 3, audit M1): both decoration dates showed as plain to-do items."""
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 22), venue="venue_tes_large", attributes=["decorations"])
    o = _by_id(packet)
    assert o["tes-decorations-faq"].superseded_by == "tes-decorations-terms"
    assert "Not applied" in (o["tes-decorations-faq"].note or "")
    assert o["tes-decorations-terms"].superseded_by is None
    on_timeline = {entry.rule_id for entry in packet.timeline}
    assert "tes-decorations-terms" in on_timeline and "tes-decorations-faq" not in on_timeline
    assert "tes-cancellation-large-terms" not in on_timeline and "tes-cancellation-large-faq" in on_timeline


def test_move_date_suggestions_skip_breaks_and_name_undated_usg_deadlines(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 2 iteration 3, audit M4; iteration 1, verify L2): the suggestion fell in winter break and
    claimed every passed deadline was met while USG's academic-week deadline had certainly passed."""
    packet = _packet(ruleset, calendar, event_date=date(2026, 11, 20), venue="venue_tes_meeting_room", attributes=["food", "usg_funding"])
    move = next(f for f in packet.fallbacks if f.kind == "move_date")
    assert move.earliest_date is not None
    assert not (calendar.is_break(move.earliest_date) or calendar.is_university_holiday(move.earliest_date)
                or calendar.is_study_day_or_final_exam(move.earliest_date))
    assert move.earliest_date >= date(2027, 2, 1)
    assert "USG's deadline table" in move.text
    for o in packet.obligations:
        for f in o.fallbacks:
            if f.kind == "move_date" and f.earliest_date and calendar.covers(f.earliest_date):
                assert not calendar.is_break(f.earliest_date), (o.rule_id, f.earliest_date)


@pytest.mark.parametrize(("area", "listed"), [(None, True), (600, True), (451, True), (450, False), (200, False)])
def test_fire_permit_follows_the_tent_size(ruleset, calendar, area, listed) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 2 iteration 3, audit M6): the LAFD permit fired on any tent; the source says larger than
    450 square feet. Unknown size keeps it listed with a note to check."""
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 15), venue="venue_outdoor", attributes=["tent", "outside_rentals"],
                     tent_area_sqft=area)
    o = _by_id(packet)
    assert ("lafd-division-5-permit" in o) is listed
    if listed:
        assert "450 square feet" in (o["lafd-division-5-permit"].note or "")
    assert "tes-outside-rentals" in o  # a rented tent still needs its rental deadline


def test_open_flame_needs_the_fire_permit_whatever_the_tent_size(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 15), venue="venue_outdoor", attributes=["tent", "open_flame"],
                     tent_area_sqft=100)
    assert "lafd-division-5-permit" in _by_id(packet)


def test_office_decides_approvals_get_the_all_approvals_date_with_its_source(ruleset, calendar) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 2 iteration 3, audit M8; iteration 1, verify M3): office-decides items had no contact-by
    date. The terms require every approval two weeks before, which is the sourced latest date."""
    packet = _packet(ruleset, calendar, event_date=date(2027, 4, 9), venue="venue_outdoor",
                     attributes=["food", "amplified_sound", "performers", "social_event"])
    o = _by_id(packet)
    for rule_id in ("special-event-insurance", "amplified-sound-outdoor", "fpm-outdoor-electrical"):
        item = o[rule_id]
        assert item.due is None and item.contact_by == date(2027, 3, 26), rule_id
        assert item.contact_by_citation is not None and item.contact_by_citation.rule_id == "approvals-two-weeks"
        assert item.finding is not None and item.finding.verdict is Verdict.OFFICE_DECIDES
    assert o["dps-security"].contact_by is None and o["dps-security"].due == date(2027, 3, 26)  # it has its own date
    off_campus = _packet(ruleset, calendar, event_date=date(2027, 4, 9), venue="venue_off_campus", attributes=["performers"])
    assert _by_id(off_campus)["special-event-insurance"].contact_by is None  # no approvals rule off campus
