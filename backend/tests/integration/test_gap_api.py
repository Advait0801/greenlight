"""Funding gap helper routes: options are code only, the email is a draft for a person to edit and approve, and
nothing is sent."""

from __future__ import annotations

from typing import Any

BODY: dict[str, Any] = {"event_name": "Culture Night", "event_date": "2027-04-09", "venue": "venue_outdoor", "headcount": 150,
                        "shortfall_cents": 90000, "asks_usg": True, "note": "Can Red Bull sponsor us with cash and run a raffle?"}
BANNED = {"sponsorship-cash-banned", "raffle-purchase-banned", "brand-ambassadors-banned", "sponsorship-activation-banned"}


def test_options_list_only_allowed_ways_and_explain_the_banned_ones(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/gap/options", json=BODY)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["shortfall_text"] == "$900.00"
    assert {o["citation"]["rule_id"] for o in report["options"]}.isdisjoint(BANNED)
    assert BANNED <= {b["rule_id"] for b in report["not_allowed"]}
    assert {b["rule_id"] for b in report["not_allowed"] if b["in_your_note"]} == {"sponsorship-cash-banned", "raffle-purchase-banned"}
    other = next(o for o in report["options"] if o["id"] == "other_usc_funds")
    assert other["finding"]["verdict"] == "yellow"
    assert report["notice"].startswith("Greenlight is a pre-check")


def test_options_refuse_unknown_attributes(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/gap/options", json={**BODY, "attributes": ["free_money"]})
    assert response.status_code == 422


def test_email_is_a_draft_and_approval_sends_nothing(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/gap/email", json={"kind": "in_kind_sponsor", "club_name": "Chess Club", "recipient": "Cafe",
                                                "event_name": "Tournament", "ask": "Boards"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approved"] is False and "does not send" in body["notice"]
    assert "Tournament" in body["text"]
    edited = body["text"] + "\nP.S. edited by the officer"
    approved = client.post("/gap/email/approve", json={"subject": body["subject"], "text": edited})
    assert approved.status_code == 200 and approved.json()["approved"] is True
    assert "has not sent anything" in approved.json()["message"]
    assert client.post("/gap/email/approve", json={"text": "   "}).status_code == 422
