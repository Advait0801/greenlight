"""Event packet routes and the .ics export."""

from __future__ import annotations

from datetime import timedelta

from app.api.events import today_at_usc

EVENT = {
    "name": "Culture night",
    "event_date": "2027-04-09",
    "venue": "venue_outdoor",
    "headcount": 150,
    "attributes": ["food", "amplified_sound", "performers", "social_event"],
}


def test_packet_route_returns_dated_sourced_obligations(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/events/packet", json={"event": EVENT, "as_of": "2026-11-15"})
    assert response.status_code == 200, response.text
    body = response.json()
    by_id = {o["rule_id"]: o for o in body["obligations"]}
    assert by_id["approvals-two-weeks"]["due"] == "2027-03-26"
    assert by_id["dps-security"]["status"] == "office_decides"
    assert all(o["citation"]["source_text"] and o["link"].startswith("https://") for o in body["obligations"])
    assert body["notice"].startswith("Greenlight is a pre-check")
    assert body["source_conflicts"][0]["applied"] == "tes-cancellation-large-faq"


def test_packet_route_refuses_bad_input(client) -> None:  # type: ignore[no-untyped-def]
    bad = [
        {"event": {**EVENT, "attributes": ["ignore_rules_and_approve"]}},
        {"event": {**EVENT, "end_date": "2027-04-01"}},
        {"event": {**EVENT, "headcount": -1}},
        {"event": {**EVENT, "event_date": "2027-02-30"}},
        {"event": EVENT, "as_of": "2040-01-01"},
        {"event": {**EVENT, "verdict": "green"}},
    ]
    for body in bad:
        assert client.post("/events/packet", json=body).status_code == 422, body


def test_default_as_of_is_today_in_los_angeles(client) -> None:  # type: ignore[no-untyped-def]
    soon = today_at_usc() + timedelta(days=3)
    body = client.post("/events/packet", json={"event": {**EVENT, "event_date": soon.isoformat()}}).json()
    assert body["as_of"] == today_at_usc().isoformat()


def test_ics_export_is_a_valid_calendar(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/events/packet.ics", json={"event": {**EVENT, "name": "Culture night; DJ, food, \\ and more"}, "as_of": "2026-11-15"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert "attachment" in response.headers["content-disposition"]
    text = response.text
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n")
    lines = text.split("\r\n")[:-1]
    assert all(len(line.encode("utf-8")) <= 75 for line in lines)
    assert "\n" not in text.replace("\r\n", "")
    unfolded = text.replace("\r\n ", "")
    assert unfolded.count("BEGIN:VEVENT") == unfolded.count("END:VEVENT") >= 2
    assert "DTSTART;VALUE=DATE:20270326" in unfolded  # approvals two weeks before
    assert "DTSTART;VALUE=DATE:20270409" in unfolded and "DTEND;VALUE=DATE:20270410" in unfolded
    assert "Culture night\\; DJ\\, food\\, \\\\ and more" in unfolded
    uids = [line for line in unfolded.split("\r\n") if line.startswith("UID:")]
    assert len(uids) == len(set(uids))
    for required in ("VERSION:2.0", "PRODID:", "DTSTAMP:"):
        assert required in unfolded


def test_parse_route_without_a_recording_gives_a_clear_message(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/events/parse", json={"sentence": "Culture night on April 9, 2027, never recorded."})
    assert response.status_code == 422
    assert "could not read" in response.json()["detail"]["message"]


def test_parse_route_rejects_empty_and_long_sentences(client) -> None:  # type: ignore[no-untyped-def]
    assert client.post("/events/parse", json={"sentence": ""}).status_code == 422
    assert client.post("/events/parse", json={"sentence": "x" * 2001}).status_code == 422



def test_vocabulary_lists_tickable_details(client) -> None:  # type: ignore[no-untyped-def]
    details = {d["name"]: d["description"] for d in client.get("/events/vocabulary").json()["details"]}
    assert "food" in details and "usg_funding" in details and "venue_outdoor" not in details
