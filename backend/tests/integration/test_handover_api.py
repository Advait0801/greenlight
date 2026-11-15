"""Handover packet: built by code from the saved plan and the club's own sent applications, editable, approved by a
person; another club's application cannot be read in with the wrong token."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.schemas.plans import PlanEvent, YearPlanRequest
from app.services.handover import seed_next_year
from tests.integration.test_money_api import BODY as CHECK


def _demo(client: Any) -> dict[str, Any]:
    response = client.get("/plans/demo")
    assert response.status_code == 200
    plan = response.json()
    plan["as_of"] = "2026-11-15"
    return plan


def test_packets_for_each_role_with_figures_from_code(client) -> None:  # type: ignore[no-untyped-def]
    plan = _demo(client)
    response = client.post("/handover", json={"plan": plan})
    assert response.status_code == 200, response.text
    body = response.json()
    assert [p["role"] for p in body["packets"]] == ["President", "Treasurer", "Events lead"]
    treasurer = body["packets"][1]["text"]
    report = client.post("/plans/plan", json=plan).json()
    assert f"${report['budget']['total_cost_cents'] // 100:,}." in treasurer
    assert any("reference and token" in n for n in body["notes"])
    first = plan["events"][0]
    seeded = body["next_year_plan"]["events"][0]
    assert seeded["key"] == first["key"] and seeded["event_date"] != first["event_date"]
    assert body["next_year_plan"]["money_on_hand_cents"] == 0


def test_sent_applications_need_the_clubs_own_token(client) -> None:  # type: ignore[no-untyped-def]
    mine = client.post("/usg/send", json={"club_name": "Mine", "consent": True, "check": CHECK}).json()
    theirs = client.post("/usg/send", json={"club_name": "Theirs", "consent": True, "check": CHECK}).json()
    plan = _demo(client)
    ok = client.post("/handover", json={"plan": plan, "applications": [{"reference": mine["reference"], "club_token": mine["club_token"]}]})
    assert ok.status_code == 200
    assert "Trojan Table Catering" in ok.json()["packets"][1]["text"]
    stolen = client.post("/handover", json={"plan": plan, "applications": [{"reference": theirs["reference"], "club_token": mine["club_token"]}]})
    assert stolen.status_code == 404


def test_an_edited_packet_is_approved_by_a_person(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/handover/approve", json={"role": "President", "text": "Edited packet."})
    assert response.status_code == 200 and response.json()["approved"] is True
    assert client.post("/handover/approve", json={"role": "President", "text": "  "}).status_code == 422


def test_next_years_plan_keeps_the_weekday_and_clears_the_money() -> None:
    plan = YearPlanRequest(club_name="C", money_on_hand_cents=500, usg_received_this_year_cents=100, events=[
        PlanEvent(key="a", name="A", event_date=date(2027, 4, 9), end_date=date(2027, 4, 10)),
        PlanEvent(key="b", name="B", event_date=date(2100, 12, 1))])
    seeded = seed_next_year(plan)
    assert seeded.events[0].event_date == date(2028, 4, 7) and seeded.events[0].event_date.weekday() == date(2027, 4, 9).weekday()
    assert seeded.events[0].end_date == date(2028, 4, 8)
    assert seeded.events[1].event_date is None
    assert seeded.money_on_hand_cents == 0 and seeded.usg_received_this_year_cents is None
