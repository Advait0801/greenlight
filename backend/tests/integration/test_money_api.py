"""Money check routes: code-only check, uploads read as data, no draft while red, approval recorded, nothing sent."""

from __future__ import annotations

from typing import Any

BODY: dict[str, Any] = {
    "event": {"name": "Culture Night", "description": "Cultural celebration", "event_date": "2027-04-09", "expected_attendance": 150,
              "venue": "venue_outdoor", "ticketed": True, "open_to_all_students": True},
    "club": {"usg_received_this_year_cents": 0, "usg_funded_events_this_semester": 0},
    "attachments": ["esr", "hospitality_food_form", "food_health_permit_and_insurance", "food_justification"],
    "lines": [
        {"line": 1, "vendor": "Trojan Table Catering", "item": "Buffet", "category": "food", "quantity": 150,
         "unit_price_cents": 3800, "amount_cents": 570000, "has_quote": True},
        {"line": 2, "vendor": "Nova Sound DJ", "item": "DJ", "category": "performer_fee", "quantity": 1,
         "unit_price_cents": 80000, "amount_cents": 80000, "has_quote": True},
    ],
    "fund": "usg-fund-social-recreation-startup",
    "as_of": None,
}


def test_check_returns_red_lines_with_rule_text_and_fixes(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/money/check", json=BODY)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["verdict"] == "red" and not report["draft_allowed"]
    food = report["lines"][0]["findings"]
    cap = next(f["finding"] for f in food if f["finding"]["rule_id"] == "usg-food-cap")
    assert cap["citation"]["source_url"].startswith("https://") and cap["fix"]
    assert report["totals"]["total_cents"] == 650000 and report["notice"]


def test_check_refuses_unknown_names_and_bad_numbers(client) -> None:  # type: ignore[no-untyped-def]
    bad = {**BODY, "lines": [{**BODY["lines"][0], "category": "rockets"}]}
    assert client.post("/money/check", json=bad).status_code == 422
    negative = {**BODY, "lines": [{**BODY["lines"][0], "amount_cents": -5}]}
    assert client.post("/money/check", json=negative).status_code == 422
    assert client.post("/money/check", json={**BODY, "lines": []}).status_code == 422


def test_draft_is_refused_while_red_and_the_server_rechecks(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/money/draft", json={"check": BODY, "purpose": "Share cultures."})
    assert response.status_code == 409
    assert response.json()["detail"]["blocked_by"]


def test_draft_when_clean_falls_back_without_a_recording(client) -> None:  # type: ignore[no-untyped-def]
    clean = {**BODY, "event": {**BODY["event"], "ticketed": False},
             "lines": [{**BODY["lines"][0], "unit_price_cents": 3500, "amount_cents": 525000}]}
    response = client.post("/money/draft", json={"check": clean, "purpose": "Share cultures."})
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft["approved"] is False and "$5,250.00" in draft["text"] and "does not submit" in draft["text"]


def test_approval_is_recorded_and_nothing_is_sent(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/money/draft/approve", json={"text": "Final text", "event_name": "x"})
    assert response.status_code == 200 and response.json()["approved"] is True
    assert "not submitted" in response.json()["message"]
    assert client.post("/money/draft/approve", json={"text": "   "}).status_code == 422


def test_read_rejects_empty_unknown_and_unreadable_files(client) -> None:  # type: ignore[no-untyped-def]
    assert client.post("/money/read", data={"text": ""}).status_code == 422
    response = client.post("/money/read", files={"files": ("x.bin", b"\x00\x01\x02\xff", "application/octet-stream")})
    assert response.status_code == 200
    body = response.json()
    assert body["documents"] == [] and "PDF" in body["problems"][0]["message"]
    response = client.post("/money/read", data={"text": "Quote: pizza $10"})
    assert response.json()["problems"] and response.json()["documents"] == []  # no recording: a clear message, not a pass


def test_vocabulary_lists_categories_attachments_and_funds(client) -> None:  # type: ignore[no-untyped-def]
    body = client.get("/money/vocabulary").json()
    assert len(body["funds"]) == 4 and any(c["name"] == "food" for c in body["categories"]) and body["attachments"]


def test_fund_reading_without_a_recording_says_choose_yourself(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/money/fund", json={"name": "Night", "description": "Party"})
    assert response.status_code == 422 and "Choose the fund" in response.json()["detail"]["message"]
