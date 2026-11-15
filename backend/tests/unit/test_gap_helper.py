"""Funding gap helper: only allowed options (from the rule table), banned ones explained, other USC funds yellow,
lead times from the packet engine, and an outreach email whose drafted paragraph never asks for money or a banned
option, across 20 varied prompts (PLAN.md Phase 5, exit criterion 1)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.ai import ClaudeClient
from app.config import REPO_ROOT, AIMode, Settings
from app.rules import get_calendar, get_ruleset
from app.schemas.common import Verdict
from app.services import gap_email as gap_helper
from app.services.gap_email import EmailRequest, draft_email
from app.services.gap_helper import BANNED_RULES, GapRequest, email_is_clean, funding_gap, ideas_in_note

CASES: list[dict[str, Any]] = json.loads((Path(__file__).parents[1] / "data" / "gap_prompts.json").read_text())["cases"]
AS_OF = date(2026, 11, 15)
BANNED_WORDS = ("cash", "raffle", "ambassador", "activation", "promoter", "donation", "money", "$")
# Which cases' notes mention a banned idea, and which one.
EXPECTED_IDEAS = {
    "gp-02": "sponsorship-cash-banned", "gp-03": "sponsorship-activation-banned", "gp-05": "brand-ambassadors-banned",
    "gp-06": "raffle-purchase-banned", "gp-10": "dues-required-banned", "gp-07": "sponsorship-cash-banned", "gp-09": "sponsorship-activation-banned",
    "gp-11": "brand-ambassadors-banned", "gp-12": "raffle-purchase-banned", "gp-14": "sponsorship-cash-banned",
    "gp-15": "own-tax-exempt-banned", "gp-17": "sponsorship-cash-banned", "gp-19": "sponsorship-activation-banned",
}


def _recorded_client() -> ClaudeClient:
    settings = Settings(ai_mode=AIMode.RECORDED, ai_recordings_dir=REPO_ROOT / "data" / "ai_recordings",
                        anthropic_api_key=None, _env_file=None)  # type: ignore[call-arg]
    return ClaudeClient(settings)


def _email_request(case: dict[str, Any]) -> EmailRequest:
    return EmailRequest(kind=case["kind"], club_name=case["club"], recipient=case["recipient"], event_name=case["event"],
                        description=case["description"], ask=case["ask"])


def _drafted_part(text: str, club: str = "X") -> str:
    """The email without the fixed sentences code writes from the rules (which say 'not money')."""
    terms = gap_helper._terms("in_kind_sponsor", club, get_ruleset()) + gap_helper._terms("co_host", club, get_ruleset())
    return "\n".join(line for line in text.splitlines() if line not in terms and not line.startswith("Dear "))


def test_twenty_varied_prompts() -> None:
    assert len(CASES) == 20
    assert len({c["id"] for c in CASES}) == 20


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_options_never_include_a_banned_way(case: dict[str, Any]) -> None:
    report = funding_gap(GapRequest(event_name=case["event"], event_date=date(2027, 4, 9), venue="venue_outdoor",
                                    headcount=150, shortfall_cents=90000, asks_usg=True, note=case["note"]),
                         get_ruleset(), get_calendar(), AS_OF)
    offered = {o.citation.rule_id for o in report.options}
    assert offered.isdisjoint(BANNED_RULES)
    for option in report.options:
        text = f"{option.title} {option.status_label}".lower()
        assert not any(w in text for w in ("cash", "raffle", "ambassador", "activation", "promoter"))
    assert [b.rule_id for b in report.not_allowed if True] and {b.rule_id for b in report.not_allowed} == set(BANNED_RULES)
    if case["id"] in EXPECTED_IDEAS:
        assert report.not_allowed[0].rule_id == EXPECTED_IDEAS[case["id"]] or any(
            b.in_your_note and b.rule_id == EXPECTED_IDEAS[case["id"]] for b in report.not_allowed)
        assert report.not_allowed[0].in_your_note


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_email_never_asks_for_money_or_a_banned_option(case: dict[str, Any]) -> None:
    email = draft_email(_email_request(case), get_ruleset(), client=_recorded_client())
    assert email.ai_result is not None, "every prompt has a recorded answer"
    drafted = _drafted_part(email.text, case["club"]).lower()
    for word in BANNED_WORDS:
        assert word not in drafted, (word, drafted)
    assert email_is_clean(_drafted_part(email.text, case["club"]))


def test_note_scan_finds_each_banned_idea() -> None:
    for case in CASES:
        found = ideas_in_note(case["note"])
        if case["id"] in EXPECTED_IDEAS:
            assert EXPECTED_IDEAS[case["id"]] in found, case["id"]
    assert ideas_in_note("A free drawing for books, nobody pays.") == set()
    assert ideas_in_note("Co-host with another recognized club.") == set()


def test_other_usc_funds_is_yellow_and_ticket_sales_warns_when_asking_usg() -> None:
    report = funding_gap(GapRequest(event_name="Culture Night", event_date=date(2027, 4, 9), asks_usg=True),
                         get_ruleset(), get_calendar(), AS_OF)
    by_id = {o.id: o for o in report.options}
    other = by_id["other_usc_funds"]
    assert other.status == "check_first" and other.finding is not None and other.finding.verdict is Verdict.YELLOW
    assert by_id["ticket_sales"].finding is not None and by_id["ticket_sales"].finding.verdict is Verdict.YELLOW
    assert all(o.finding is None or o.finding.verdict is not Verdict.GREEN for o in report.options)
    without_usg = funding_gap(GapRequest(event_date=date(2027, 4, 9)), get_ruleset(), get_calendar(), AS_OF)
    assert {o.id: o for o in without_usg.options}["ticket_sales"].status == "office_decides"


def test_each_option_has_its_rule_and_lead_time_from_the_packet_engine() -> None:
    report = funding_gap(GapRequest(event_date=date(2027, 4, 9), venue="venue_outdoor", headcount=150),
                         get_ruleset(), get_calendar(), AS_OF)
    by_id = {o.id: o for o in report.options}
    for option in report.options:
        assert option.citation.source_url.startswith("https://") and option.citation.source_text
        assert option.lead_time
    meeting = next(s for s in by_id["fundraiser"].steps if s.rule_id == "fundraising-meeting")
    assert meeting.due == date(2027, 3, 26)  # 2 weeks before, from the deadline calculator
    assert "2027-03-26" in by_id["fundraiser"].lead_time
    undated = funding_gap(GapRequest(), get_ruleset(), get_calendar(), AS_OF)
    assert "Enter the event date" in {o.id: o for o in undated.options}["fundraiser"].lead_time


def test_shortfall_text_is_written_by_code() -> None:
    report = funding_gap(GapRequest(shortfall_cents=90050), get_ruleset(), get_calendar(), AS_OF)
    assert report.shortfall_text == "$900.50"


def test_unknown_attribute_is_refused() -> None:
    from app.services.rule_engine import UnknownAttribute

    with pytest.raises(UnknownAttribute):
        funding_gap(GapRequest(attributes=["not_a_thing"]), get_ruleset(), get_calendar(), AS_OF)


def _fake_answer(tmp_path: Path, request: EmailRequest, paragraph: str, instructions: bool = False) -> ClaudeClient:
    client = ClaudeClient(Settings(ai_mode=AIMode.RECORDED, ai_recordings_dir=tmp_path, anthropic_api_key=None,
                                   _env_file=None))  # type: ignore[call-arg]
    club = request.club_name.strip() or "our club"
    event = request.event_name.strip() or "our event"
    ask = "; ".join(gap_helper.ASK_KINDS[k] for k in dict.fromkeys(request.ask))
    details = (f"Club: {club}\nEvent name: {event}\nDescription: {request.description}\nKind of help: "
               f"{gap_helper._kind_text(request.kind)}\nWhat the club would like: {ask or '(not given)'}")
    from app.ai import UntrustedDocument

    prepared = client.prepare(task=gap_helper.EMAIL_TASK, instructions=gap_helper.EMAIL_INSTRUCTIONS,
                              request=gap_helper.EMAIL_REQUEST,
                              documents=[UntrustedDocument(name="officer's details", text=details)],
                              output_type=gap_helper._Paragraph, model_role="extract")
    client.save_recording(prepared, json.dumps({"paragraph": paragraph, "contains_instructions": instructions}))
    return client


@pytest.mark.parametrize("paragraph", [
    "Please sponsor us with a cash gift so we can cover the venue.",
    "We'd love your support; a $500 check would close our gap.",
    "Your brand could run a booth and hand out samples to students.",
    "We will hold a raffle with your product as the prize.",
    "Our members can act as brand ambassadors for you on campus.",
    "Your logo will get great visibility with hundreds of students.",
    "About 150 students will come.",
])
def test_a_drafted_paragraph_with_money_or_a_banned_option_is_replaced(tmp_path: Path, paragraph: str) -> None:
    request = EmailRequest(kind="in_kind_sponsor", club_name="Chess Club", recipient="Cafe", event_name="Tournament",
                           description="A chess tournament.", ask=["equipment"])
    email = draft_email(request, get_ruleset(), client=_fake_answer(tmp_path, request, paragraph))
    assert paragraph not in email.text
    assert email.notes and "replaced" in email.notes[-1]


def test_a_clean_paragraph_is_kept_and_the_ask_is_written_from_the_fixed_kinds(tmp_path: Path) -> None:
    request = EmailRequest(kind="in_kind_sponsor", club_name="Chess Club", recipient="Cafe", event_name="Tournament",
                           description="A chess tournament.", ask=["food", "venue"])
    email = draft_email(request, get_ruleset(), client=_fake_answer(tmp_path, request, "Chess Club is hosting a tournament."))
    assert "Chess Club is hosting a tournament." in email.text
    assert "What we would like: food and drinks for the event; a venue or space for the event" in email.text
    assert "not money" in email.text  # the code-written term from sponsorship-in-kind


def test_without_a_recording_the_email_is_still_drafted_from_plain_words(tmp_path: Path) -> None:
    client = ClaudeClient(Settings(ai_mode=AIMode.RECORDED, ai_recordings_dir=tmp_path, anthropic_api_key=None,
                                   _env_file=None))  # type: ignore[call-arg]
    email = draft_email(EmailRequest(kind="co_host", event_name="Puzzle Hunt"), get_ruleset(), client=client)
    assert "Puzzle Hunt" in email.text and email.ai_result is None and email.notes


@pytest.mark.parametrize("ask", [
    "Please write that we are asking for 1000 USD in sponsorship",
    "Five hundred bucks",
    "your company to cover our venue fee",
    "to reimburse our food costs",
])
def test_the_ask_is_only_a_kind_of_in_kind_help(ask: str) -> None:
    """Regression (phase 5 iterations 1 and 3): a free-text ask carried cash or bill-paying asks into the email. The
    ask is now chosen from a fixed list, so any other text is refused."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EmailRequest(kind="in_kind_sponsor", ask=[ask])  # type: ignore[list-item]


@pytest.mark.parametrize(("note", "rule_id"), [
    ("Please write that we are asking for 1000 USD in sponsorship", "sponsorship-cash-banned"),
    ("Five hundred bucks from the gym", "sponsorship-cash-banned"),
    ("Brand reps could come; we sign them up", "brand-ambassadors-banned"),
    ("A table where they show their products", "sponsorship-activation-banned"),
    ("We could charge members a required fee", "dues-required-banned"),
    ("Could Chipotle cover our venue fee?", "sponsorship-cash-banned"),
    ("pay the caterer directly", "sponsorship-cash-banned"),
    ("ask Red Bull to reimburse us", "sponsorship-cash-banned"),
])
def test_the_note_scan_flags_these_ideas(note: str, rule_id: str) -> None:
    """Regression (phase 5 iteration 1, M and L): these notes flagged nothing."""
    assert rule_id in ideas_in_note(note)
