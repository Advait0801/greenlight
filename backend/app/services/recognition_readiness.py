"""Readiness tracker for the rest of the recognition application. Pure code, no AI.

The officer ticks what is done; code counts what is left and how many days remain. Every item, number
and date comes from rules/recognition.json. Greenlight cannot see EngageSC, so a tick is the officer's
own word, and the report says so.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from app.rules import RuleSet, citation_for, finding_for
from app.schemas.common import PRECHECK_NOTICE, Citation, Verdict

CAMPUS_TIME = ZoneInfo("America/Los_Angeles")
ItemState = Literal["done", "to_do", "check", "info"]
STATE_LABELS: dict[ItemState, str] = {
    "done": "Done (marked by you)", "to_do": "Still to do", "check": "Needs a human look", "info": "Good to know",
}


class OfficerStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: str = Field(max_length=60)
    named: bool = False
    hazing_prevention: bool = False
    officer_learning_path: bool = False
    commitment_to_community: bool = False


class ReadinessInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    officers: list[OfficerStatus] = Field(default_factory=list, max_length=20)
    additional_members: int = Field(default=0, ge=0, le=100_000)
    advisor_named: bool = False
    advisor_accepted: bool = False
    advisor_training: bool = False
    advisor_commitment: bool = False
    constitution_ready: bool = False
    accountability_document: bool = False
    positions_accepted: bool = False


class ReadinessItem(BaseModel):
    id: str
    label: str
    state: ItemState
    state_label: str
    verdict: Verdict | None
    message: str
    fix: str | None
    due: date | None
    days_left: int | None
    citation: Citation
    also_cited: list[Citation] = []


class ReadinessGroup(BaseModel):
    title: str
    items: list[ReadinessItem]


class KeyDate(BaseModel):
    label: str
    day: date
    days_left: int
    passed: bool
    message: str
    citation: Citation


class ReadinessReport(BaseModel):
    notice: str = PRECHECK_NOTICE
    as_of: date
    overall: Verdict
    message: str
    summary: dict[str, int]
    positions: list[str]
    groups: list[ReadinessGroup]
    key_dates: list[KeyDate]


def today_on_campus() -> date:
    return datetime.now(CAMPUS_TIME).date()


def _title(text: str) -> str:
    return " ".join(word.capitalize() for word in text.split())


def readiness(ruleset: RuleSet, given: ReadinessInput, as_of: date | None = None) -> ReadinessReport:
    as_of = as_of or today_on_campus()
    window = ruleset.get("recognition-application-window").params
    closes = datetime.fromisoformat(window["closes_at"]).astimezone(CAMPUS_TIME).date()
    opens = date.fromisoformat(window["opens_on"])
    advisor_due = date.fromisoformat(ruleset.get("recognition-advisor-deadline").params["due_on"])
    closed = as_of > closes

    def item(item_id: str, rule_id: str, label: str, done: bool | None, *, due: date | None = None,
             fix: str | None = None, message: str | None = None, also: list[str] | None = None,
             info: bool = False) -> ReadinessItem:
        """done=None is an item Greenlight cannot tick off: it is shown as information or for a human look."""
        rule = ruleset.get(rule_id)
        shown = ruleset.display_severity(rule_id)
        text = message or rule.message
        state: ItemState
        verdict: Verdict | None
        if shown == "info" or info:
            state, verdict = "info", None
        elif done is None or shown != "red":
            # A rule the table shows yellow is never ticked green; it stays a question for the office.
            state, verdict = "check", Verdict.YELLOW
            if done:
                text = f"You marked this done. {text}"
        elif done:
            state, verdict = "done", Verdict.GREEN
        else:
            state, verdict = "to_do", Verdict.RED
            if due is not None and as_of > due:
                text = f"{text} The date for this has passed ({due.strftime('%B %-d, %Y')})."
        if verdict is not None:
            try:
                verdict = finding_for(ruleset, rule_id, verdict, text).verdict
            except ValueError:
                state, verdict = "check", Verdict.YELLOW
        return ReadinessItem(
            id=item_id, label=label, state=state, state_label=STATE_LABELS[state], verdict=verdict, message=text,
            fix=None if state == "done" else fix, due=due, days_left=(due - as_of).days if due else None,
            citation=citation_for(ruleset, rule_id), also_cited=[citation_for(ruleset, other) for other in also or []],
        )

    positions: list[str] = list(ruleset.get("recognition-five-officers").params["required_positions"])
    by_position: dict[str, OfficerStatus] = {}
    for officer in given.officers:
        key = " ".join(re.sub(r"[^a-z]+", " ", officer.position.lower()).split())
        key = {"vp": "vice president", "programming": "programming chair", "program chair": "programming chair"}.get(key, key)
        if key not in by_position:  # a repeated position never overrides the first entry
            by_position[key] = officer
    trainings: list[str] = list(ruleset.get("recognition-officer-trainings").params["trainings"])
    groups: list[ReadinessGroup] = []
    named = 0
    for position in positions:
        officer = by_position.get(position, OfficerStatus(position=position))
        name = _title(position)
        named += officer.named
        ticks = (officer.hazing_prevention, officer.officer_learning_path)
        items = [item(f"{position}:named", "recognition-five-officers", f"{name} named on the application", officer.named,
                      due=closes, fix=f"Name a currently enrolled student as {position}.")]
        for training, tick, key in zip(trainings, ticks, ("hazing", "learning-path"), strict=True):
            items.append(item(f"{position}:{key}", "recognition-officer-trainings", f"{training} certificate", tick,
                              due=closes, fix=f"The {position} still needs {training}."))
        items.append(item(f"{position}:commitment", "recognition-commitment-to-community", "Signed Commitment to Community form",
                          officer.commitment_to_community, due=closes,
                          fix=f"The {position} still needs to sign the Commitment to Community form."))
        groups.append(ReadinessGroup(title=name, items=items))

    members = ruleset.get("recognition-five-more-members").params["min_additional_members"]
    students = ruleset.get("recognition-ten-students").params["min_students"]
    short = max(members - given.additional_members, students - (named + given.additional_members), 0)
    groups.append(ReadinessGroup(title="Members", items=[item(
        "members", "recognition-five-more-members", f"At least {members} more student members ({students} students in all)",
        short == 0, due=closes, also=["recognition-ten-students"],
        fix=f"Add {short} more student member{'s' if short != 1 else ''}." if short else None,
        message=f"You have {named} of {len(positions)} officers named and {given.additional_members} other student "
                f"member{'s' if given.additional_members != 1 else ''}. {ruleset.get('recognition-five-more-members').message}",
    )]))

    groups.append(ReadinessGroup(title="Advisor", items=[
        item("advisor:named", "recognition-advisor", "A full-time faculty or staff advisor", given.advisor_named, due=closes,
             fix=ruleset.get("recognition-advisor").fix_template),
        item("advisor:accepted", "advisor-accepts-position", "Advisor accepted the position on EngageSC", given.advisor_accepted,
             due=advisor_due, fix=ruleset.get("advisor-accepts-position").fix_template, also=["recognition-advisor-deadline"]),
        item("advisor:training", "advisor-training-certificate", "RSO Advisor Training certificate", given.advisor_training,
             due=advisor_due, fix=ruleset.get("advisor-training-certificate").fix_template, also=["recognition-advisor-deadline"]),
        item("advisor:commitment", "advisor-commitment-to-community", "Advisor's Commitment to Community form",
             given.advisor_commitment, due=advisor_due, fix=ruleset.get("advisor-commitment-to-community").fix_template,
             also=["recognition-advisor-deadline"]),
        item("advisor:clery", "advisor-clery-training", "Advisor's Clery Act course", None,
             fix=ruleset.get("advisor-clery-training").fix_template),
    ]))

    groups.append(ReadinessGroup(title="Application documents", items=[
        item("constitution", "recognition-constitution-template", "Constitution on this year's fillable template",
             given.constitution_ready, due=closes, fix=ruleset.get("recognition-constitution-template").fix_template),
        item("accountability", "recognition-accountability-document", "Accountability Document", given.accountability_document,
             due=closes, fix=ruleset.get("recognition-accountability-document").fix_template),
        item("accepted", "recognition-accept-positions", "Everyone accepted their position in EngageSC", given.positions_accepted,
             due=closes, fix="Remind officers, members and the advisor to accept their position in EngageSC."),
        item("accessibility", "recognition-event-accessibility-training", "Event Accessibility module", None,
             fix=ruleset.get("recognition-event-accessibility-training").fix_template),
        item("incomplete", "recognition-incomplete-not-considered", "An incomplete application is not considered", None, info=True),
        item("submitter", "recognition-submitting-officer", "Who submits", None),
        item("appeal", "recognition-appeal", "If the application is denied", None, info=True),
    ]))

    def key_date(label: str, day: date, rule_id: str) -> KeyDate:
        left = (day - as_of).days
        when = "today" if left == 0 else f"in {left} day{'s' if left != 1 else ''}" if left > 0 else \
            f"{-left} day{'s' if left != -1 else ''} ago"
        return KeyDate(label=label, day=day, days_left=left, passed=left < 0, message=f"{day.strftime('%B %-d, %Y')} ({when})",
                       citation=citation_for(ruleset, rule_id))

    key_dates = [
        key_date("Application opened", opens, "recognition-application-window"),
        key_date("Application closes at 11:59 pm; late applications are not accepted", closes, "recognition-application-window"),
        key_date("Advisor's requirements due", advisor_due, "recognition-advisor-deadline"),
    ]

    every = [entry for group in groups for entry in group.items]
    summary = {state: sum(1 for entry in every if entry.state == state) for state in STATE_LABELS}
    to_do, check = summary["to_do"], summary["check"]
    overall = Verdict.RED if to_do else Verdict.YELLOW if check else Verdict.GREEN
    advisor_open = sum(1 for entry in every if entry.state == "to_do" and entry.due == advisor_due)
    student_open = to_do - advisor_open
    if closed and student_open:
        message = (f"The application closed on {closes.strftime('%B %-d, %Y')} and late applications are not accepted. "
                   f"{student_open} item{'s were' if student_open != 1 else ' was'} still open.")
    elif closed and advisor_open and as_of <= advisor_due:
        left = (advisor_due - as_of).days
        message = (f"{advisor_open} advisor item{'s are' if advisor_open != 1 else ' is'} still to do. They are due "
                   f"{advisor_due.strftime('%B %-d, %Y')}" + (f", in {left} day{'s' if left != 1 else ''}." if left else ", today."))
    elif closed and advisor_open:
        message = (f"The advisor's requirements were due {advisor_due.strftime('%B %-d, %Y')}. "
                   f"{advisor_open} advisor item{'s were' if advisor_open != 1 else ' was'} still open.")
    elif to_do:
        left = (closes - as_of).days
        message = (f"{to_do} item{'s' if to_do != 1 else ''} still to do. The application closes "
                   f"{closes.strftime('%B %-d, %Y')} at 11:59 pm" + (f", in {left} day{'s' if left != 1 else ''}." if left > 0 else
                                                                      ", today." if left == 0 else "."))
    else:
        message = ("Everything you can tick is ticked. Items marked for a human look are questions for Campus Activities. "
                   "Greenlight cannot see EngageSC, so check there before you submit.")
    return ReadinessReport(as_of=as_of, overall=overall, message=message, summary=summary, positions=positions,
                           groups=groups, key_dates=key_dates)
