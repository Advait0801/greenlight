"""Phase 2, iteration 2 (break): the event packet's rule engine.

Each test describes the correct behaviour (PROJECT_CONTEXT 4C, 7 "Event rules", 9; PLAN.md Phase 2) and
fails against the engine as built on phase-2/event-packet at 62bc37d.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.rules import get_calendar, get_ruleset
from app.schemas.common import Verdict
from app.schemas.events import EventFacts, EventPacket, PacketObligation
from app.services.rule_engine import build_packet

AS_OF = date(2026, 11, 15)


def _packet(as_of: date = AS_OF, **facts: Any) -> EventPacket:
    return build_packet(EventFacts(**facts), get_ruleset(), get_calendar(), as_of)


def _item(packet: EventPacket, rule_id: str) -> PacketObligation:
    found = [o for o in packet.obligations if o.rule_id == rule_id]
    assert found, f"{rule_id} is not in the packet: {[o.rule_id for o in packet.obligations]}"
    return found[0]


def _is_green(item: PacketObligation) -> bool:
    return item.finding is not None and item.finding.verdict is Verdict.GREEN


# --- Wrong greens ---------------------------------------------------------------------------------


@pytest.mark.parametrize("event_date", ["2028-01-15", "2027-08-30"])
def test_first_three_weeks_rule_is_not_green_outside_spring_2027(event_date: str) -> None:
    """The 'no club events in the first 3 weeks' rule is hard-coded to January 1-26, 2027 and skips the
    calendar-coverage check. January 15, 2028 is in the first 3 weeks of January 2028 (the source's own
    wording: 'the first 3 weeks of the January'), and August 30, 2027 is the first week of Fall 2027
    (PROJECT_CONTEXT 7: 'First 3 weeks of a semester'). Neither date is covered by Greenlight's calendar.
    Both are shown green ('Meets the rule'). They must be at least yellow (check with the office)."""
    packet = _packet(event_date=event_date, venue="venue_outdoor", headcount=50)
    item = _item(packet, "tes-no-events-first-three-weeks")
    assert not _is_green(item), (item.status, item.finding)
    assert item.status in ("check_with_office", "blocked"), item.status


def test_tabling_hours_not_green_when_the_time_is_unknown() -> None:
    """tabling-hours is 'between the hours of 10:00 a.m. - 2:00 p.m. Monday through Friday'. The engine
    checks only the weekday and shows the rule green, though the event facts carry no time at all. A
    table from 3 to 5 p.m. on a Monday breaks the rule and is shown as 'Meets the rule'."""
    packet = _packet(event_date="2027-03-01", headcount=5, attributes=["tabling"])
    item = _item(packet, "tabling-hours")
    assert not _is_green(item), item.finding


def test_alcohol_weekday_rule_not_green_when_service_end_is_unknown() -> None:
    """alcohol-thursday-saturday's rule text also says 'Alcohol service must end at least one hour before
    the event's scheduled end time'. Only the weekday is checked, yet the whole rule is shown green on a
    Thursday. A half-checked rule must not be shown as met."""
    packet = _packet(event_date="2027-03-04", venue="venue_tes_large", headcount=50, attributes=["alcohol"])
    item = _item(packet, "alcohol-thursday-saturday")
    assert not _is_green(item), item.finding


# --- Silently missing obligations -----------------------------------------------------------------


@pytest.mark.parametrize(("fact", "rule_id"), [
    ("prohibited_decoration", "tes-decorations-prohibited"),
    ("alcohol_is_main_focus", "alcohol-not-main-focus"),
    ("drawing_requires_purchase", "raffle-purchase-banned"),
    ("co_host_not_recognized", "cohost-unrecognized-banned"),
    ("sponsor_gives_money", "sponsorship-cash-banned"),
])
def test_fact_alone_still_brings_in_its_banned_rule(fact: str, rule_id: str) -> None:
    """The form offers the 'facts' group as tick boxes (GET /events/vocabulary). An officer who ticks only
    'A prohibited decoration is planned (... fog machine ...)' or 'Alcohol is the main focus of the event'
    gets a packet with no decorations or alcohol items and no block: the banned rule is triggered only
    by the base attribute (decorations, alcohol, ...), which the fact itself implies. The rule the event
    breaks must appear (blocked, or at least check with the office), never be silently dropped."""
    packet = _packet(event_date="2027-03-05", venue="venue_tes_large", headcount=30, attributes=[fact])
    ids = [o.rule_id for o in packet.obligations]
    assert rule_id in ids, ids
    assert _item(packet, rule_id).status in ("blocked", "check_with_office")


# --- Hard blocks for impossible dates ---------------------------------------------------------------


def test_usg_funding_for_an_event_five_days_away_is_a_hard_block() -> None:
    """USG's deadline is at least 6 academic weeks before the event (usg-page-deadline-event-date), and a
    missed deadline is an automatic denial (PROJECT_CONTEXT 7). Whatever an academic week turns out to be,
    6 of them are at least 42 calendar days, so an event 5 days away has certainly missed it. The packet
    shows only yellow 'check with the office' items, no hard block and no 'other funding' fallback."""
    packet = _packet(event_date="2026-11-20", venue="venue_off_campus", headcount=30, attributes=["usg_funding"])
    usg_blocks = [b for b in packet.hard_blocks if "USG" in b or "Undergraduate Student Government" in b or "funding" in b.lower()]
    assert usg_blocks, packet.hard_blocks
    assert any(f.kind == "other_funding" for f in packet.fallbacks), packet.fallbacks
