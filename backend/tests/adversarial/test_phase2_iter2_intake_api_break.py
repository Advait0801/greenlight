"""Phase 2, iteration 2 (break): the reading step, the packet routes and the .ics export.

Each test describes the correct behaviour and fails against phase-2/event-packet at 62bc37d. AI calls stay
recorded; the reading step is exercised with hand-built readings passed to facts_from_reading (code only).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.rules import get_ruleset
from app.services.event_intake import _reading_model, facts_from_reading, offered_names
from tests.conftest import clear_caches


@pytest.fixture
def lenient_client() -> Iterator[TestClient]:
    """A client that returns a 500 response instead of raising, so the status code can be asserted."""
    from app.main import create_app

    clear_caches()
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
    clear_caches()


def _reading(start: dict[str, Any], end: dict[str, Any] | None = None, *, headcount: int | None = 150,
             headcount_confidence: str = "high") -> Any:
    model = _reading_model(offered_names(get_ruleset()))
    return model.model_validate({
        "event_name": "Culture night",
        "start": start,
        "end": end,
        "venue": {"value": "venue_outdoor", "confidence": "high", "evidence": "McCarthy Quad"},
        "venue_name": "McCarthy Quad",
        "headcount": {"value": headcount, "confidence": headcount_confidence, "evidence": "people"},
        "details": [],
        "contains_instructions": False,
    })


def _parts(year: int, month: int, day: int, weekday: str | None = None) -> dict[str, Any]:
    return {"year": year, "month": month, "day": day, "weekday": weekday, "confidence": "high", "evidence": "stated"}


# --- Contradictory sentences --------------------------------------------------------------------------


@pytest.mark.parametrize("weekday", ["Thu", "Thurs", "Thursday,", "thursday."])
def test_abbreviated_weekday_that_contradicts_the_date_is_caught(weekday: str) -> None:
    """'Thu, April 9, 2027': April 9, 2027 is a Friday. The weekday check compares only full lowercase
    names, so 'Thu', 'Thurs' or 'Thursday,' pass and the contradictory date is used without a question.
    The date must be dropped and asked for, as it is for 'Thursday'."""
    parsed = facts_from_reading(_reading(_parts(2027, 4, 9, weekday)), get_ruleset())
    assert parsed.facts.event_date is None, parsed.facts.event_date
    assert "event_date" in parsed.facts.needs_officer_input


def test_end_date_more_than_a_year_after_start_becomes_a_question_not_a_crash() -> None:
    """A reading with start March 1, 2027 and end March 1, 2029 makes EventFacts raise a ValidationError
    inside facts_from_reading, which /events/parse does not catch (it catches IntakeError only): a 500.
    The end date should be dropped and asked for, like an end date before the start."""
    parsed = facts_from_reading(_reading(_parts(2027, 3, 1), _parts(2029, 3, 1)), get_ruleset())
    assert parsed.facts.end_date is None
    assert "end_date" in parsed.facts.needs_officer_input


@pytest.mark.parametrize("headcount", [-5, 5_000_000])
def test_out_of_range_headcount_is_asked_not_silently_dropped(headcount: int) -> None:
    """A headcount read with high confidence but outside 0..1,000,000 is set to None, and because the
    confidence was high no question is raised: the number silently disappears."""
    parsed = facts_from_reading(_reading(_parts(2027, 3, 1), headcount=headcount), get_ruleset())
    assert parsed.facts.headcount is None
    assert "headcount" in parsed.facts.needs_officer_input


# --- Malformed API bodies -----------------------------------------------------------------------------


@pytest.mark.parametrize(("path", "event"), [
    ("/events/packet", {"event_date": "0001-01-01", "venue": "venue_outdoor"}),
    ("/events/packet", {"event_date": "0001-01-05", "venue": "venue_outdoor", "attributes": ["social_dance"]}),
    ("/events/packet.ics", {"event_date": "0001-01-01", "venue": "venue_outdoor"}),
    ("/events/packet.ics", {"event_date": "9999-12-31", "venue": "venue_outdoor"}),
])
def test_extreme_event_dates_do_not_crash(lenient_client: TestClient, path: str, event: dict[str, Any]) -> None:
    """Year 1 overflows the deadline calculator (date minus weeks/months) and December 31, 9999 overflows the
    .ics DTEND: both give 500 Internal Server Error. They should be refused with a clear 422."""
    response = lenient_client.post(path, json={"event": event, "as_of": "2026-11-15"})
    assert response.status_code == 422, (response.status_code, response.text[:200])


# --- .ics content ---------------------------------------------------------------------------------------


def test_ics_has_no_raw_control_characters(client: TestClient) -> None:
    """RFC 5545 TEXT values may not contain control characters other than tab. An event name with NUL or
    ESC is written into SUMMARY and X-WR-CALNAME as is, which calendar apps reject or truncate."""
    body = {"event": {"name": "Night\x00\x1b\x07 out", "event_date": "2027-04-09", "venue": "venue_outdoor",
                      "headcount": 150}, "as_of": "2026-11-15"}
    response = client.post("/events/packet.ics", json=body)  # type: ignore[attr-defined]
    assert response.status_code == 200
    bad = [ch for ch in response.text if ord(ch) < 32 and ch not in "\r\n\t"]
    assert not bad, [hex(ord(ch)) for ch in bad]


# --- Error messages -------------------------------------------------------------------------------------


def test_parse_error_does_not_reveal_server_paths(client: TestClient) -> None:
    """When the reading step fails, the 422 message shown to the officer includes the server's absolute
    path to the recordings folder and an internal task key. It should be a plain message."""
    response = client.post("/events/parse", json={"sentence": "A small board meeting next term, no date yet."})  # type: ignore[attr-defined]
    assert response.status_code == 422
    message = str(response.json())
    assert "/Users/" not in message and "ai_recordings" not in message and "recorded response" not in message, message
