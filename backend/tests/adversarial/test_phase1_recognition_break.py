"""Phase 1, iteration 2 (break): the constitution check and the readiness tracker.

Every test here failed when it was written and states the correct behaviour. Inputs start from the
clean eval constitution co-01 and change one thing.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.config import REPO_ROOT
from app.rules import get_ruleset
from app.services.recognition import check_upload
from app.services.recognition_check import ReaderAnswer, check_constitution, reader_questions
from app.services.recognition_readiness import OfficerStatus, ReadinessInput, readiness

EVAL = REPO_ROOT / "data" / "eval" / "constitutions"
CASES = {case["id"]: case for case in json.loads((EVAL / "cases.json").read_text(encoding="utf-8"))["cases"]}
CLEAN = (EVAL / "texts" / "co-01.txt").read_text(encoding="utf-8")
CLUB = CASES["co-01"]["club"]
BACKEND = Path(__file__).resolve().parents[2]

PURPOSE = ("The purpose of this organization is to bring USC students together to create, exhibit and share "
           "community art projects.")
DUES_FIXED = "Part 4. Dues may not be a requirement for any level of membership."


@pytest.fixture(scope="module")
def ruleset() -> Any:
    return get_ruleset()


def _result(report: Any, rule_id: str) -> Any:
    return next(r for r in report.clauses if r.rule_id == rule_id)


def _all_note_text(report: Any) -> str:
    return " ".join([n.message for n in report.notes] + [line for n in report.notes for line in n.detail])


def _confident_no(ruleset: Any) -> dict[tuple[str, str], ReaderAnswer]:
    """A reader that found nothing wrong anywhere (what an injected or mistaken model would return)."""
    return {(q.clause_rule_id, q.banned_rule_id): ReaderAnswer("no", True, None) for q in reader_questions(ruleset)}


# ------------------------------------------------------------------------------------------------
# Wrong greens: a blank filled with something meaningless


@pytest.mark.parametrize("filler", ["TBC", "Insert purpose here", "To be decided later", "TBD by the board", "XX",
                                    "Lorem ipsum dolor sit amet"])
def test_meaningless_fill_in_is_not_shown_present(ruleset: Any, filler: str) -> None:
    """A placeholder or filler text in a blank is an unfilled blank, not a present clause."""
    text = CLEAN.replace(PURPOSE, f"The purpose of this organization is {filler}.")
    assert _result(check_constitution(text, ruleset, CLUB), "clause-i-b-1").state != "present"


def test_blank_filled_with_the_templates_own_words_is_not_present(ruleset: Any) -> None:
    """Repeating the template's lead-in words inside the blank does not answer it."""
    original = re.search(r"Part 4\. Voting members must attend.*", CLEAN).group(0)  # type: ignore[union-attr]
    text = CLEAN.replace(original, "Part 4. Voting members must attend at least of all meetings of all meetings. "
                                   "General members must attend at least of all meetings of all meetings.")
    assert _result(check_constitution(text, ruleset, CLUB), "clause-ii-c-4").state != "present"


def test_dues_clause_with_placeholders_is_not_green_even_when_the_reader_finds_no_problem(ruleset: Any) -> None:
    """'none_is_acceptable' lets "none" or "$0" through; it must not let "TBD" or "[insert amount]" through."""
    original = re.search(r"Part 5\. Dues: Members.*", CLEAN).group(0)  # type: ignore[union-attr]
    text = CLEAN.replace(original, "Part 5. Dues: Members may be asked to pay dues in the amount of [insert amount] "
                                   "per semester. Member dues will be used for: TBD.")
    result = _result(check_constitution(text, ruleset, CLUB, answers=_confident_no(ruleset)), "clause-ii-c-5")
    assert result.state == "missing"


# ------------------------------------------------------------------------------------------------
# Wrong greens: a number below the minimum read as meeting it


@pytest.mark.parametrize("count", ["less than one", "fewer than 1", "one-half", "at most 1"])
def test_advisor_meetings_below_once_a_semester_are_not_present(ruleset: Any, count: str) -> None:
    """The advisor rule is 'at least once a semester'. These wordings allow fewer, so the clause is not green."""
    text = re.sub(r"Officers should meet with the advisor .*? times per semester",
                  f"Officers should meet with the advisor {count} times per semester", CLEAN)
    result = _result(check_constitution(text, ruleset, CLUB), "clause-vii-b-2")
    assert result.state in ("contradicts", "needs_look")


# ------------------------------------------------------------------------------------------------
# Wrong greens: membership wording that breaks the open-membership and dues rules, outside the membership blanks


def test_membership_barriers_written_into_the_purpose_blank_are_flagged(ruleset: Any) -> None:
    """Interview, GPA, major and paid-dues requirements break the open-membership rules wherever they are written."""
    text = CLEAN.replace(PURPOSE, "The purpose of this organization is to bring USC students together to create art. "
                                  "Membership is limited to School of Fine Arts majors with a 3.5 GPA who pass an "
                                  "interview and pay $50 in dues.")
    result = _result(check_constitution(text, ruleset, CLUB), "clause-i-b-1")
    assert result.state in ("contradicts", "needs_look")


def test_line_that_negates_a_fixed_clause_keeps_the_clause_from_green(ruleset: Any) -> None:
    """The fixed dues clause followed by a line that cancels it is a changed clause, not a present one."""
    text = CLEAN.replace(DUES_FIXED, DUES_FIXED + "\nThis Part does not apply to voting members, who must pay dues.", 1)
    assert _result(check_constitution(text, ruleset, CLUB), "clause-ii-a-4").state != "present"


# ------------------------------------------------------------------------------------------------
# Text that disappears without being reported


def test_line_with_dot_leaders_is_not_silently_dropped(ruleset: Any) -> None:
    """Only the table of contents may be skipped. A clause line that ends in dots must still be read or reported."""
    added = "Except that voting members must pay $50 in dues each semester........"
    report = check_constitution(CLEAN.replace(DUES_FIXED, DUES_FIXED + "\n" + added, 1), ruleset, CLUB)
    reported = "voting members must pay $50" in _all_note_text(report)
    assert reported or _result(report, "clause-ii-a-4").state != "present"


def test_text_after_an_appendix_heading_is_reported(ruleset: Any) -> None:
    """The 2026-27 template's appendix is empty; anything the club writes there must be shown, not ignored."""
    text = CLEAN + "\nAPPENDIX\nVoting members must pay $50 dues and pass an interview.\n"
    report = check_constitution(text, ruleset, CLUB)
    assert "pass an interview" in _all_note_text(report)


# ------------------------------------------------------------------------------------------------
# Not-applicable logic


def test_document_that_names_a_parent_organization_does_not_hide_the_national_bylaws_clause(ruleset: Any) -> None:
    """The officer answered 'no parent organization', but Article VI says the club is a chapter of a national
    organization. The required link to the national bylaws (VIII-C-2) must not be hidden as 'not required'."""
    old = "Section B. PARENT ORGANIZATION AFFILIATION\nPart 1. Not applicable.\nPart 2. Not applicable."
    new = ("Section B. PARENT ORGANIZATION AFFILIATION\n"
           "Part 1. Lantern Arts Collective is the USC chapter of the National Lantern Society.\n"
           "Part 2. Where National Lantern Society guidelines, regulations, or policies differ from those of USC, "
           "USC's policies, regulations, and guidelines take precedence.")
    assert old in CLEAN
    report = check_constitution(CLEAN.replace(old, new), ruleset, CLUB)
    assert _result(report, "clause-viii-c-2").state in ("missing", "needs_look")


# ------------------------------------------------------------------------------------------------
# Wrong-year template


def test_current_year_written_in_full_is_not_flagged_as_another_year(ruleset: Any) -> None:
    report = check_constitution(CLEAN.replace("2026-27 AY", "2026-2027 Academic Year"), ruleset, CLUB)
    assert "other_year" not in {n.kind for n in report.notes}


def test_other_year_note_names_the_year_the_document_says(ruleset: Any) -> None:
    report = check_constitution(CLEAN.replace("2026-27 AY", "2025-2026 Academic Year"), ruleset, CLUB)
    note = next(n for n in report.notes if n.kind == "other_year")
    assert "2025-20 " not in note.message and ("2025-26" in note.message or "2025-2026" in note.message)


# ------------------------------------------------------------------------------------------------
# Files


def test_windows_1252_text_file_is_read_as_text_not_as_utf16_garbage(ruleset: Any) -> None:
    """Word's 'Save as plain text' on Windows writes cp1252. It must be read correctly or refused clearly;
    it must not be decoded as UTF-16 and reported as '92 of 92 clauses need fixing'."""
    data = CLEAN.encode("cp1252", errors="replace")
    if len(data) % 2:
        data += b" "
    report, _ = check_upload(ruleset, CLUB, filename="constitution.txt", data=data)
    assert (not report.readable) or report.summary["present"] >= 80


def test_pdf_with_damaged_pages_says_so(ruleset: Any) -> None:
    """A PDF whose middle is damaged loses page text. The report must say part of the file could not be read,
    instead of listing the lost clauses as if the officer had left them out."""
    data = bytearray((REPO_ROOT / "rules" / "sources" / "raw" / "constitution-template.pdf").read_bytes())
    start = len(data) // 3
    data[start:start + 2000] = b"A" * 2000
    report, _ = check_upload(ruleset, {}, filename="constitution.pdf", data=bytes(data))
    if report.readable:
        words = _all_note_text(report).lower() + " " + report.message.lower()
        assert "damaged" in words or "could not be read" in words or "could not read" in words


def test_long_part_is_checked_in_reasonable_time() -> None:
    """90,000 characters (well under the 400,000 limit) in one Part must not stall the server. The prefix
    search in compare() is quadratic: about 3 s for 4,000 lines, minutes for 30,000."""
    script = textwrap.dedent("""
        import os, tempfile
        os.environ["AI_MODE"] = "recorded"
        os.environ["AI_RECORDINGS_DIR"] = tempfile.mkdtemp()
        os.environ["ANTHROPIC_API_KEY"] = ""
        from app.rules import get_ruleset
        from app.services.recognition_check import check_constitution
        text = "ARTICLE I. NAME\\nSection B: PURPOSE\\nPart 2. All activities\\n" + "ab\\n" * 30000
        check_constitution(text, get_ruleset(), {})
    """)
    try:
        subprocess.run([sys.executable, "-c", script], cwd=BACKEND, check=True, timeout=20, capture_output=True)
    except subprocess.TimeoutExpired:
        pytest.fail("checking 90,000 characters in one Part took more than 20 seconds")


# ------------------------------------------------------------------------------------------------
# Readiness tracker


def _all_done_but_advisor() -> ReadinessInput:
    officers = [OfficerStatus(position=p, named=True, hazing_prevention=True, officer_learning_path=True,
                              commitment_to_community=True)
                for p in ("president", "vice president", "secretary", "treasurer", "programming chair")]
    return ReadinessInput(officers=officers, additional_members=5, advisor_named=True, constitution_ready=True,
                          accountability_document=True, positions_accepted=True)


@pytest.mark.parametrize("as_of", [date(2026, 11, 23), date(2026, 12, 1)])
def test_advisor_items_still_open_until_december_1_are_not_reported_as_too_late(ruleset: Any, as_of: date) -> None:
    """Between Nov 23 and Dec 1 the advisor's three items are still due (Dec 1). The headline must say so,
    not 'the application closed ... late applications are not accepted. 3 items were still open.'"""
    report = readiness(ruleset, _all_done_but_advisor(), as_of)
    assert "December 1" in report.message


def test_officer_position_written_with_a_hyphen_is_not_silently_ignored(client: Any) -> None:
    """'Vice-President' with every box ticked must count for the vice president, or be refused clearly;
    it must not be dropped so the vice president shows four open items."""
    body = {"officers": [{"position": "Vice-President", "named": True, "hazing_prevention": True,
                          "officer_learning_path": True, "commitment_to_community": True}]}
    response = client.post("/recognition/readiness", params={"as_of": "2026-11-15"}, json=body)
    if response.status_code == 200:
        items = {i["id"]: i["state"] for g in response.json()["groups"] for i in g["items"]}
        assert items["vice president:named"] == "done"
    else:
        assert response.status_code == 422
