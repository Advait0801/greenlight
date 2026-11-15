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
                                                "event_name": "Tournament", "ask": ["equipment"]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approved"] is False and "does not send" in body["notice"]
    assert "Tournament" in body["text"]
    edited = body["text"] + "\nP.S. edited by the officer"
    approved = client.post("/gap/email/approve", json={"subject": body["subject"], "text": edited})
    assert approved.status_code == 200 and approved.json()["approved"] is True
    assert "has not sent anything" in approved.json()["message"]
    assert client.post("/gap/email/approve", json={"text": "   "}).status_code == 422


def test_an_event_name_that_has_the_sponsor_pay_is_left_out(client) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 5 iteration 3, H): 'paid for by' names went into the subject and greeting."""
    body = client.post("/gap/email", json={"kind": "in_kind_sponsor", "event_name": "Free Pizza Night paid for by Dominos",
                                            "ask": ["food"]}).json()
    assert "paid for by" not in body["text"] and "paid for by" not in body["subject"]
    assert client.post("/gap/email", json={"kind": "in_kind_sponsor", "ask": "cover our venue fee"}).status_code == 422


def test_fundraiser_and_ticket_sales_are_shown_as_the_office_decides(client) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 5 iteration 3, M): options that need an office's approval read 'Allowed'."""
    report = client.post("/gap/options", json={"event_date": "2027-04-09", "as_of": "2026-11-15"}).json()
    by_id = {o["id"]: o for o in report["options"]}
    for option in ("fundraiser", "ticket_sales"):
        assert by_id[option]["status"] == "office_decides" and by_id[option]["finding"]["verdict"] == "office_decides"
