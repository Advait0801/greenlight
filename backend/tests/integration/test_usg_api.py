"""USG screen: a club's data appears only if the club sent it; a denial reason reaches the club only after a person
approved it; reasons are the application's own findings; the chart is aggregate."""

from __future__ import annotations

import copy
from collections.abc import Iterator
from typing import Any

import pytest

from tests.conftest import clear_caches
from tests.integration.test_money_api import BODY as CHECK

KEY = "test-reviewer-passcode"
REVIEWER = {"X-Reviewer-Key": KEY}


@pytest.fixture
def usg(monkeypatch: pytest.MonkeyPatch, client: Any) -> Iterator[Any]:
    monkeypatch.setenv("USG_REVIEWER_KEY", KEY)
    from app.config import get_settings

    get_settings.cache_clear()
    from sqlalchemy import delete

    from app.db import _session_factory
    from app.models import SentApplication

    with _session_factory()() as session:
        session.execute(delete(SentApplication))
        session.commit()
    yield client
    monkeypatch.delenv("USG_REVIEWER_KEY")
    get_settings.cache_clear()


def _send(client: Any, club: str = "Filipino American Student Association", **changes: Any) -> dict[str, Any]:
    check = copy.deepcopy(CHECK)
    check["event"].update(changes)
    response = client.post("/usg/send", json={"club_name": club, "consent": True, "check": check})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_queue_is_closed_without_a_configured_passcode(client) -> None:  # type: ignore[no-untyped-def]
    clear_caches()
    assert client.get("/usg/queue", headers=REVIEWER).status_code == 503


def test_reviewer_routes_need_the_passcode(usg) -> None:  # type: ignore[no-untyped-def]
    for path in ("/usg/queue", "/usg/stats", "/usg/applications/1"):
        assert usg.get(path).status_code == 401
        assert usg.get(path, headers={"X-Reviewer-Key": "wrong-passcode-123"}).status_code == 401
    assert usg.post("/usg/applications/1/denial-draft", json={"rule_ids": ["usg-food-cap"]}).status_code == 401


def test_nothing_is_visible_until_a_club_sends_it_with_consent(usg) -> None:  # type: ignore[no-untyped-def]
    usg.post("/money/check", json=CHECK)  # a check alone never reaches the USG screen
    assert usg.get("/usg/queue", headers=REVIEWER).json()["applications"] == []
    refused = usg.post("/usg/send", json={"club_name": "X", "consent": False, "check": CHECK})
    assert refused.status_code == 422
    assert usg.post("/usg/send", json={"club_name": "X", "check": CHECK}).status_code == 422
    assert usg.get("/usg/queue", headers=REVIEWER).json()["applications"] == []
    sent = _send(usg)
    queue = usg.get("/usg/queue", headers=REVIEWER).json()["applications"]
    assert [a["reference"] for a in queue] == [sent["reference"]]
    assert queue[0]["verdict"] == "red"


def test_the_server_rechecks_and_keeps_no_documents(usg) -> None:  # type: ignore[no-untyped-def]
    sent = _send(usg)
    app_id = usg.get("/usg/queue", headers=REVIEWER).json()["applications"][0]["id"]
    detail = usg.get(f"/usg/applications/{app_id}", headers=REVIEWER).json()
    assert detail["reference"] == sent["reference"]
    assert {r["rule_id"] for r in detail["reasons"]} >= {"usg-food-cap", "usg-ineligible-performers"}
    assert all(r["citation"]["source_url"].startswith("https://") for r in detail["reasons"])


def test_a_club_reads_only_its_own_application_with_its_token(usg) -> None:  # type: ignore[no-untyped-def]
    mine = _send(usg, club="Club A")
    theirs = _send(usg, club="Club B")
    ok = usg.post(f"/usg/sent/{mine['reference']}", json={"club_token": mine["club_token"]})
    assert ok.status_code == 200 and ok.json()["reviewer_message"] is None
    assert usg.post(f"/usg/sent/{theirs['reference']}", json={"club_token": mine["club_token"]}).status_code == 404
    assert usg.post("/usg/sent/G-NOPE", json={"club_token": mine["club_token"]}).status_code == 404
    assert usg.post(f"/usg/sent/{theirs['reference']}/withdraw", json={"club_token": mine["club_token"]}).status_code == 404


def test_withdrawn_applications_leave_the_queue_and_the_chart(usg) -> None:  # type: ignore[no-untyped-def]
    sent = _send(usg)
    app_id = usg.get("/usg/queue", headers=REVIEWER).json()["applications"][0]["id"]
    assert usg.get("/usg/stats", headers=REVIEWER).json()["applications"] == 1
    usg.post(f"/usg/sent/{sent['reference']}/withdraw", json={"club_token": sent["club_token"]})
    assert usg.get("/usg/queue", headers=REVIEWER).json()["applications"] == []
    assert usg.get(f"/usg/applications/{app_id}", headers=REVIEWER).status_code == 404
    assert usg.get("/usg/stats", headers=REVIEWER).json()["applications"] == 0


def test_denial_reason_reaches_the_club_only_after_a_person_approves_it(usg) -> None:  # type: ignore[no-untyped-def]
    sent = _send(usg)
    app_id = usg.get("/usg/queue", headers=REVIEWER).json()["applications"][0]["id"]
    assert usg.post(f"/usg/applications/{app_id}/denial-approve", headers=REVIEWER,
                    json={"text": "No.", "reviewer_name": "R"}).status_code == 409
    bad = usg.post(f"/usg/applications/{app_id}/denial-draft", headers=REVIEWER, json={"rule_ids": ["usg-hotel-cap"]})
    assert bad.status_code == 422
    draft = usg.post(f"/usg/applications/{app_id}/denial-draft", headers=REVIEWER, json={"rule_ids": ["usg-food-cap"]})
    assert draft.status_code == 200 and draft.json()["approved"] is False
    text = draft.json()["text"]
    assert "usg-food-cap" not in text and "$35" in text and "https://" in text
    status_before = usg.post(f"/usg/sent/{sent['reference']}", json={"club_token": sent["club_token"]}).json()
    assert status_before["reviewer_message"] is None
    edited = text.replace("[Reviewer name]", "Jordan Lee")
    approved = usg.post(f"/usg/applications/{app_id}/denial-approve", headers=REVIEWER,
                        json={"text": edited, "reviewer_name": "Jordan Lee"})
    assert approved.status_code == 200
    status_after = usg.post(f"/usg/sent/{sent['reference']}", json={"club_token": sent["club_token"]}).json()
    assert status_after["reviewer_message"] == edited


def test_failure_chart_counts_red_rules_once_per_application_and_names_no_club(usg) -> None:  # type: ignore[no-untyped-def]
    _send(usg, club="Club A")
    _send(usg, club="Club B")
    stats = usg.get("/usg/stats", headers=REVIEWER).json()
    assert stats["applications"] == 2
    rows = {r["rule_id"]: r["applications"] for r in stats["rows"]}
    assert rows["usg-food-cap"] == 2 and rows["usg-ineligible-performers"] == 2
    assert "Club A" not in str(stats)


def test_no_new_draft_once_a_reason_is_approved(usg) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 5 iteration 3, M): re-drafting after approval changed the recorded reasons behind the text
    the club already reads."""
    _send(usg)
    app_id = usg.get("/usg/queue", headers=REVIEWER).json()["applications"][0]["id"]
    text = usg.post(f"/usg/applications/{app_id}/denial-draft", headers=REVIEWER, json={"rule_ids": ["usg-food-cap"]}).json()["text"]
    usg.post(f"/usg/applications/{app_id}/denial-approve", headers=REVIEWER, json={"text": text, "reviewer_name": "R"})
    again = usg.post(f"/usg/applications/{app_id}/denial-draft", headers=REVIEWER, json={"rule_ids": ["usg-ineligible-performers"]})
    assert again.status_code == 409
    assert usg.get(f"/usg/applications/{app_id}", headers=REVIEWER).json()["denial_rule_ids"] == ["usg-food-cap"]


def test_denial_approve_needs_the_passcode(usg) -> None:  # type: ignore[no-untyped-def]
    assert usg.post("/usg/applications/1/denial-approve", json={"text": "x", "reviewer_name": "R"}).status_code == 401


def test_the_reviewer_header_is_allowed_cross_origin(usg) -> None:  # type: ignore[no-untyped-def]
    """Regression (phase 5 iteration 3, M): the CORS preflight refused X-Reviewer-Key."""
    response = usg.options("/usg/queue", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
                                                  "Access-Control-Request-Headers": "X-Reviewer-Key"})
    assert response.status_code == 200
