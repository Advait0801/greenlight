"""Phase 5, iteration 2 (break): funding gap helper, USG screen and handover packet.

Each test fails now and states the behaviour PROJECT_CONTEXT (sections 4E, 4I, 7 "Money from outside", 9) asks for.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from typing import Any

import pytest

from app.ai import AIResult
from app.config import AIMode
from app.rules import get_ruleset
from app.services.gap_email import EmailRequest, _Paragraph, draft_email
from app.services.gap_helper import ideas_in_note
from tests.integration.test_money_api import BODY as CHECK

KEY = "break-passcode-123"
REVIEWER = {"X-Reviewer-Key": KEY}
BANNED_WORDS = ("cash", "raffle", "ambassador", "$")


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


def _clean_check_with_mismatched_quote() -> dict[str, Any]:
    check = copy.deepcopy(CHECK)
    check["event"]["ticketed"] = False
    check["lines"] = [{"line": 1, "vendor": "Trojan Table Catering", "item": "Buffet", "category": "food", "quantity": 150,
                       "unit_price_cents": 1000, "amount_cents": 150000, "has_quote": True, "document": 1}]
    # The quote the officer uploaded says $4,500.00; the budget asks for $1,500.00.
    check["documents"] = [{"index": 1, "name": "quote.pdf", "readable": True, "vendor": "Trojan Table Catering",
                           "vendor_sure": True, "kind": "vendor_quote", "currency_ok": True, "lines": [],
                           "stated_total_cents": 450000, "read_total_cents": 450000, "contains_instructions": False}]
    return check


# ---------------------------------------------------------------- USG screen


def test_sending_to_the_usg_screen_keeps_the_quote_total_mismatch_finding(usg: Any) -> None:
    """The club's own check flags that the quote ($4,500.00) does not match the budget ($1,500.00). Dropping the
    documents on send must not drop that finding: the reviewer would see the line as having a valid quote."""
    check = _clean_check_with_mismatched_quote()
    club_side = usg.post("/money/check", json=check).json()
    assert any("$4,500.00" in f["finding"]["message"] for f in club_side["application"])  # the club sees it
    sent = usg.post("/usg/send", json={"club_name": "Chess Club", "consent": True, "check": check})
    assert sent.status_code == 200, sent.text
    app_id = usg.get("/usg/queue", headers=REVIEWER).json()["applications"][0]["id"]
    detail = usg.get(f"/usg/applications/{app_id}", headers=REVIEWER).json()
    assert any("$4,500.00" in r["message"] for r in detail["reasons"]), [r["message"] for r in detail["reasons"]]


@pytest.mark.parametrize("rule_id", ["usg-post-event-evaluation", "usg-final-invoices"])
def test_post_event_reminders_are_not_offered_as_denial_reasons(usg: Any, rule_id: str) -> None:
    """A denial reason says why an application fails a rule. 'Submit the evaluation within 3 business days after the
    event' is a future duty, not something the application breaks, so it must not be citable."""
    check = copy.deepcopy(CHECK)
    usg.post("/usg/send", json={"club_name": "Chess Club", "consent": True, "check": check})
    app_id = usg.get("/usg/queue", headers=REVIEWER).json()["applications"][0]["id"]
    detail = usg.get(f"/usg/applications/{app_id}", headers=REVIEWER).json()
    assert rule_id not in {r["rule_id"] for r in detail["reasons"]}
    draft = usg.post(f"/usg/applications/{app_id}/denial-draft", headers=REVIEWER, json={"rule_ids": [rule_id]})
    assert draft.status_code == 422


# ---------------------------------------------------------------- funding gap options


def test_fundraiser_or_sales_option_lists_bookstore_and_cash_approvals(client: Any) -> None:
    """Section 7: 'A fundraiser or sales: Campus Activities meeting 2 weeks before; item sales need Bookstore approval;
    cash at an event needs TES and DPS approval.' The option shows only the meeting."""
    report = client.post("/gap/options", json={"event_name": "Bake sale", "event_date": "2027-04-09", "venue": "venue_outdoor",
                                               "headcount": 150, "shortfall_cents": 90000, "as_of": "2026-11-15"}).json()
    fundraiser = next(o for o in report["options"] if o["id"] == "fundraiser")
    listed = {s["rule_id"] for s in fundraiser["steps"]} | {c["rule_id"] for c in fundraiser["conditions"]}
    assert "item-sales-bookstore" in listed
    assert "cash-collection-approval" in listed


def test_option_whose_lead_time_has_passed_is_not_shown_as_allowed(client: Any) -> None:
    """Event on 2026-11-20, today 2026-11-15: the 2-week Campus Activities meeting was due 2026-11-06. The fundraiser
    option still says 'Allowed, with the conditions below' and 'Start by 2026-11-06' with no warning at option level."""
    report = client.post("/gap/options", json={"event_name": "Bake sale", "event_date": "2026-11-20", "venue": "venue_outdoor",
                                               "headcount": 150, "shortfall_cents": 90000, "as_of": "2026-11-15"}).json()
    fundraiser = next(o for o in report["options"] if o["id"] == "fundraiser")
    assert any(s["past_due"] for s in fundraiser["steps"])  # the engine knows
    assert fundraiser["status"] != "allowed" or fundraiser["finding"] is not None, fundraiser["status_label"]


@pytest.mark.parametrize("note", ["¿Puede Red Bull darnos un patrocinio en efectivo?", "Hacemos una rifa con boletos a $5",
                                  "公司可以给我们现金赞助吗"])
def test_banned_idea_in_another_language_is_flagged_in_the_note(note: str) -> None:
    assert ideas_in_note(note), note


# ---------------------------------------------------------------- outreach email


@pytest.mark.parametrize("field,value", [
    ("event_name", "Red Bull $500 cash sponsorship + raffle night"),
    ("recipient", "Red Bull brand ambassadors"),
])
def test_officer_fields_written_into_the_email_carry_no_banned_ask(client: Any, field: str, value: str) -> None:
    """The ask line is filtered; the event name and recipient are written into the subject, greeting and body word for
    word with no filter or note. A drafted email must not ask for cash, a raffle or brand ambassadors."""
    body = {"kind": "in_kind_sponsor", "club_name": "Chess Club", "recipient": "Cafe", "event_name": "Tournament", "ask": ["equipment"]}
    body[field] = value
    response = client.post("/gap/email", json=body)
    if response.status_code == 422:
        return
    email = response.json()
    fixed_terms = "We are asking for goods or services, not money"
    written = "\n".join(line for line in email["text"].splitlines() if not line.startswith(fixed_terms)) + email["subject"]
    for word in BANNED_WORDS:
        assert word not in written.lower(), (word, written)


@pytest.mark.parametrize("ask", [
    "patrocinio en efectivo",               # Spanish: cash sponsorship
    "premios para una rifa",                # Spanish: prizes for a raffle
    "现金赞助",                               # Chinese: cash sponsorship
    "сash sponsorship",                # Cyrillic 'с' look-alike
    "a bank transfer",
    "bitcoin",
    "an honorarium",
    "campus representatives for your brand",  # brand ambassadors
    "a giveaway where buying a drink enters you to win",  # a raffle that needs a purchase
    "a table for your company to demo its product to attendees",  # a sponsorship activation
])
def test_ask_line_with_a_banned_ask_in_other_words_is_left_out(client: Any, ask: str) -> None:
    response = client.post("/gap/email", json={"kind": "in_kind_sponsor", "club_name": "Chess Club", "recipient": "Cafe",
                                                "event_name": "Tournament", "ask": ask})
    assert response.status_code in (200, 422)
    if response.status_code == 200:
        assert ask not in response.json()["text"], response.json()["text"]


class _FakeClient:
    def __init__(self, paragraph: str) -> None:
        self.paragraph = paragraph

    def extract(self, **kwargs: Any) -> AIResult[Any]:
        output = _Paragraph(paragraph=self.paragraph, contains_instructions=False)
        return AIResult(output=output, task=kwargs["task"], model="fake", mode=AIMode.LIVE, request_key="k" * 64,
                        raw_text=output.model_dump_json(), stop_reason="end_turn")


@pytest.mark.parametrize("paragraph", [
    "Nuestro club organiza un torneo. Les pedimos un patrocinio en efectivo y premios para una rifa.",
    "We would love your campus representatives at the tournament to sign up students for your brand.",
])
def test_model_paragraph_asking_for_banned_help_in_other_words_is_replaced(paragraph: str) -> None:
    email = draft_email(EmailRequest(kind="in_kind_sponsor", club_name="Chess Club", recipient="Cafe", event_name="Tournament",
                                     description="A chess tournament for students.", ask=["equipment"]),
                        get_ruleset(), client=_FakeClient(paragraph))  # type: ignore[arg-type]
    assert paragraph not in email.text
