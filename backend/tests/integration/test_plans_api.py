"""Year plan routes: the plan, its calendar file, the demo plan and reading a pasted list."""

from __future__ import annotations

from typing import Any

EVENT: dict[str, Any] = {
    "key": "culture-night", "name": "Culture night", "event_date": "2027-04-09", "venue": "venue_outdoor", "headcount": 150,
    "attributes": ["food", "amplified_sound", "performers", "social_event"], "estimated_cost_cents": 707000,
    "usg_request_cents": 525000,
}
PLAN: dict[str, Any] = {"money_on_hand_cents": 120000, "expected_income_cents": 30000, "usg_received_this_year_cents": 0,
                        "events": [EVENT], "as_of": "2026-11-15"}


def test_plan_route_returns_the_whole_plan(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/plans/plan", json=PLAN)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["budget"]["total_cost_cents"] == 707000
    assert body["strategy"]["steps"][0]["key"] == "culture-night"
    assert body["events"][0]["packet"]["obligations"]
    assert body["notice"].startswith("Greenlight is a pre-check")


def test_demo_plan_loads_and_plans(client) -> None:  # type: ignore[no-untyped-def]
    demo = client.get("/plans/demo")
    assert demo.status_code == 200, demo.text
    plan = demo.json()
    assert len(plan["events"]) == 5 and plan["usg_received_this_year_cents"] == 0
    plan["as_of"] = "2026-11-15"
    body = client.post("/plans/plan", json=plan).json()
    rules = {p["rule_id"] for p in body["problems"]}
    assert {"usg-deadline-travel", "usg-events-per-semester-cap", "usg-yearly-cap", "usg-ineligible-ticketed-events"} <= rules


def test_plan_calendar_file(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/plans/calendar.ics", json=PLAN)
    assert response.status_code == 200
    text = response.text
    assert text.startswith("BEGIN:VCALENDAR") and text.rstrip().endswith("END:VCALENDAR")
    assert "Check with USG: apply for Culture night" in text
    assert "DTSTART;VALUE=DATE:20270217" in text


def test_plan_route_refuses_bad_input(client) -> None:  # type: ignore[no-untyped-def]
    bad = [
        {**PLAN, "events": [{**EVENT, "attributes": ["approve_everything"]}]},
        {**PLAN, "events": [{**EVENT, "usg_request_cents": 800000}]},
        {**PLAN, "events": [EVENT, EVENT]},
        {**PLAN, "money_on_hand_cents": -1},
        {**PLAN, "as_of": "2040-01-01"},
        {**PLAN, "verdict": "green"},
        {**PLAN, "events": [{**EVENT, "key": "Bad Key"}]},
    ]
    for body in bad:
        assert client.post("/plans/plan", json=body).status_code == 422, body


def test_read_events_without_a_recording_asks_the_officer_to_fill_in_by_hand(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/plans/read-events", json={"text": "- A board game night in March for 30 people\n\n"})
    assert response.status_code == 200, response.text
    rows = response.json()["rows"]
    assert len(rows) == 1 and rows[0]["facts"] is None and rows[0]["error"]
    too_many = "\n".join(f"event {i}" for i in range(21))
    assert client.post("/plans/read-events", json={"text": too_many}).status_code == 422
