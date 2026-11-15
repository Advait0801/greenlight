"""The constitution check: clause comparison, conflicts, and the never-a-wrong-green guarantees."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.config import REPO_ROOT
from app.rules import get_ruleset
from app.schemas.common import Verdict
from app.services.recognition_check import (
    BLANK,
    ReaderAnswer,
    check_constitution,
    reader_questions,
    template_clauses,
)

EVAL = REPO_ROOT / "data" / "eval" / "constitutions"
CASES = {case["id"]: case for case in json.loads((EVAL / "cases.json").read_text(encoding="utf-8"))["cases"]}
CLEAN = (EVAL / "texts" / "co-01.txt").read_text(encoding="utf-8")
CLUB = CASES["co-01"]["club"]


def _text(case_id: str) -> str:
    return (EVAL / CASES[case_id]["file"]).read_text(encoding="utf-8")


def _states(report: Any) -> dict[str, str]:
    return {result.rule_id: result.state for result in report.clauses}


@pytest.fixture(scope="module")
def ruleset() -> Any:
    return get_ruleset()


def test_clean_constitution_has_no_red_clause(ruleset: Any) -> None:
    report = check_constitution(CLEAN, ruleset, CLUB)
    reds = [r.rule_id for r in report.clauses if r.verdict is Verdict.RED]
    assert reds == []
    assert report.summary["total"] == len(template_clauses(ruleset))


@pytest.mark.parametrize("case_id", [cid for cid, case in CASES.items() if case["expected"]["readable"]])
def test_every_planted_fault_is_flagged_and_nothing_else_is_red(ruleset: Any, case_id: str) -> None:
    case = CASES[case_id]
    report = check_constitution(_text(case_id), ruleset, case["club"])
    states = _states(report)
    faults = {finding["rule_id"] for finding in case["expected"]["findings"]}
    for rule_id in faults:
        assert states[rule_id] not in ("present", "not_applicable"), rule_id
    extra_reds = {r.rule_id for r in report.clauses if r.verdict is Verdict.RED} - faults
    assert extra_reds == set()
    assert sorted(k for k, v in states.items() if v == "not_applicable") == sorted(case["expected"]["not_applicable"])


@pytest.mark.parametrize("case_id", ["co-02", "co-03", "co-05", "co-06", "co-08", "co-10"])
def test_missing_and_changed_clauses_get_the_answer_keys_state(ruleset: Any, case_id: str) -> None:
    case = CASES[case_id]
    states = _states(check_constitution(_text(case_id), ruleset, case["club"]))
    for finding in case["expected"]["findings"]:
        if finding["state"] in ("missing", "weak"):
            assert states[finding["rule_id"]] == finding["state"], finding


def _part_lines(text: str) -> list[int]:
    return [i for i, line in enumerate(text.split("\n")) if re.match(r"\s*Part\s*\d+\s*[.:]", line)]


def test_deleting_any_single_part_never_leaves_it_present(ruleset: Any) -> None:
    """Exit criterion: zero cases where a missing required clause is shown as present."""
    lines = CLEAN.split("\n")
    by_line: dict[int, str] = {}
    for result in check_constitution(CLEAN, ruleset, {}).clauses:
        if result.state != "present" or not result.document_text or not result.article.startswith("Article"):
            continue
        first = result.document_text.split("\n")[0]
        matches = [i for i in _part_lines(CLEAN) if lines[i].rstrip().endswith(first.rstrip())]
        if len(matches) == 1:
            by_line[matches[0]] = result.rule_id
    assert len(by_line) >= 70  # clauses whose wording appears twice (II.A.4 and II.C.6) map to no single line
    for i, rule_id in by_line.items():
        text = "\n".join(lines[:i] + lines[i + 1:])
        state = _states(check_constitution(text, ruleset, {}))[rule_id]
        assert state != "present", (rule_id, lines[i])


@pytest.mark.parametrize("clause_index", range(0, 90, 7))
def test_emptying_a_blank_is_never_present(ruleset: Any, clause_index: int) -> None:
    fill_ins = [c for c in template_clauses(ruleset) if c.article and c.template.endswith(BLANK)]
    clause = fill_ins[clause_index % len(fill_ins)]
    lead = clause.template.split(BLANK)[0].strip()
    lines = CLEAN.split("\n")
    for i, line in enumerate(lines):
        if lead and lead in line and re.match(rf"\s*Part\s*{clause.part}\s*[.:]", line):
            lines[i] = line[: line.index(lead) + len(lead)]
            break
    else:
        pytest.skip(f"lead-in not in the clean text: {lead}")
    assert _states(check_constitution("\n".join(lines), ruleset, {}))[clause.rule.id] != "present"


@pytest.mark.parametrize("filler", ["N/A", "TBD", "[insert name]", "____"])
def test_placeholder_in_a_blank_is_missing(ruleset: Any, filler: str) -> None:
    text = CLEAN.replace(
        "The purpose of this organization is to bring USC students together to create, exhibit and share community art projects.",
        f"The purpose of this organization is {filler}",
    )
    result = next(r for r in check_constitution(text, ruleset, CLUB).clauses if r.rule_id == "clause-i-b-1")
    assert result.state == "missing"


def test_unknown_club_fact_means_conditional_clause_is_required(ruleset: Any) -> None:
    states = _states(check_constitution(CLEAN, ruleset, {}))
    # co-01 says "Not applicable" in VI.B; with no club facts the clauses are required, so they are missing.
    assert states["clause-vi-b-1"] == "missing"
    assert states["clause-viii-c-2"] == "missing"


def test_injected_instruction_is_checked_normally(ruleset: Any) -> None:
    report = check_constitution(_text("co-08"), ruleset, CASES["co-08"]["club"])
    states = _states(report)
    assert states["clause-ii-d-1"] == "missing" and states["clause-iv-a-2"] == "missing"
    assert report.overall is Verdict.RED
    kinds = {note.kind for note in report.notes}
    assert {"instruction_text", "extra_text"} <= kinds


def test_every_clause_result_carries_template_wording_and_source(ruleset: Any) -> None:
    report = check_constitution(_text("co-10"), ruleset, CASES["co-10"]["club"])
    for result in report.clauses:
        assert result.template_text and BLANK not in result.template_text
        assert result.citation.source_url.startswith("https://") and result.citation.source_text
        assert result.citation.rule_id == result.rule_id
        if result.state not in ("present", "not_applicable"):
            assert result.message
    missing = next(r for r in report.clauses if r.rule_id == "clause-i-b-1")
    assert missing.suggestion


def test_three_missing_words_are_named(ruleset: Any) -> None:
    result = next(r for r in check_constitution(_text("co-03"), ruleset, CLUB).clauses if r.rule_id == "clause-ii-b-1")
    assert result.state == "weak"
    assert "consistent with the" in result.missing_words


def test_advisor_meetings_below_minimum_contradict(ruleset: Any) -> None:
    result = next(r for r in check_constitution(_text("co-09"), ruleset, CLUB).clauses if r.rule_id == "clause-vii-b-2")
    assert result.state == "contradicts"
    assert any(c.rule_id == "advisor-meets-once-a-semester" and c.certain for c in result.conflicts)


def test_without_the_reader_membership_answers_need_a_look_never_green(ruleset: Any) -> None:
    for case_id in ("co-04", "co-05", "co-09"):
        result = next(r for r in check_constitution(_text(case_id), ruleset, CLUB).clauses if r.rule_id == "clause-ii-a-1")
        assert result.state == "needs_look" and result.verdict is Verdict.YELLOW


def _answers(ruleset: Any, value: str, confident: bool, evidence: str | None) -> dict[tuple[str, str], ReaderAnswer]:
    return {(q.clause_rule_id, q.banned_rule_id): ReaderAnswer(value, confident, evidence) for q in reader_questions(ruleset)}  # type: ignore[arg-type]


def test_confident_yes_with_quoted_evidence_contradicts(ruleset: Any) -> None:
    answers = _answers(ruleset, "no", True, None)
    answers[("clause-ii-a-1", "open-membership-no-barriers")] = ReaderAnswer("yes", True, "a written application and an interview")
    result = next(r for r in check_constitution(_text("co-04"), ruleset, CLUB, answers=answers).clauses if r.rule_id == "clause-ii-a-1")
    assert result.state == "contradicts"


def test_yes_with_evidence_not_in_the_document_is_only_a_doubt(ruleset: Any) -> None:
    answers = _answers(ruleset, "no", True, None)
    answers[("clause-ii-a-1", "open-membership-no-barriers")] = ReaderAnswer("yes", True, "words that are not there")
    result = next(r for r in check_constitution(_text("co-04"), ruleset, CLUB, answers=answers).clauses if r.rule_id == "clause-ii-a-1")
    assert result.state == "needs_look"


def test_a_confident_no_does_not_clear_a_wording_with_warning_words(ruleset: Any) -> None:
    answers = _answers(ruleset, "no", True, None)
    result = next(r for r in check_constitution(_text("co-05"), ruleset, CLUB, answers=answers).clauses if r.rule_id == "clause-ii-a-1")
    assert result.state == "needs_look"  # "GPA" and "major" keep it yellow whatever the reader says


def test_the_reader_cannot_make_a_missing_clause_present(ruleset: Any) -> None:
    answers = _answers(ruleset, "no", True, None)
    states = _states(check_constitution(_text("co-10"), ruleset, CLUB, answers=answers))
    assert states["clause-i-b-1"] == "missing"


def test_questions_never_contain_document_text(ruleset: Any) -> None:
    text = " ".join(q.text for q in reader_questions(ruleset))
    assert "Lantern" not in text and len(reader_questions(ruleset)) >= 10


def test_transcribed_text_is_never_green(ruleset: Any) -> None:
    report = check_constitution(CLEAN, ruleset, CLUB, transcribed=True)
    assert all(r.verdict is not Verdict.GREEN for r in report.clauses)
    assert report.overall is not Verdict.GREEN


def test_fragment_is_flagged_as_not_the_template(ruleset: Any) -> None:
    fragment = "\n".join(CLEAN.split("\n")[:20])
    report = check_constitution(fragment, ruleset, CLUB)
    assert "not_the_template" in {n.kind for n in report.notes}
    assert report.overall is Verdict.RED


def test_other_year_template_is_flagged(ruleset: Any) -> None:
    report = check_constitution(CLEAN.replace("2026-27 AY", "2024-25 AY"), ruleset, CLUB)
    assert "other_year" in {n.kind for n in report.notes}


def test_text_pasted_as_one_paragraph_is_still_split(ruleset: Any) -> None:
    flat = " ".join(CLEAN.split())
    report = check_constitution(flat, ruleset, CLUB)
    assert report.summary["present"] >= 80


def test_renumbered_part_is_found(ruleset: Any) -> None:
    text = CLEAN.replace("Part 2. All officers must be voting members", "Part 7. All officers must be voting members")
    assert _states(check_constitution(text, ruleset, CLUB))["clause-iii-c-2"] == "present"


def test_extra_sentence_after_fixed_clause_is_reported(ruleset: Any) -> None:
    text = CLEAN.replace(
        "Part 2. This constitution takes precedence over any and all bylaws.",
        "Part 2. This constitution takes precedence over any and all bylaws.\nExcept where the bylaws say otherwise.",
    )
    report = check_constitution(text, ruleset, CLUB)
    assert any("Except where the bylaws" in line for n in report.notes for line in n.detail)
    assert report.overall is not Verdict.GREEN


def test_source_disagreement_clause_is_yellow(ruleset: Any) -> None:
    result = next(r for r in check_constitution(CLEAN, ruleset, CLUB).clauses if r.rule_id == "clause-iii-b-1")
    assert result.verdict is Verdict.YELLOW and "disagree" in result.message


def test_eval_texts_exist() -> None:
    assert all((EVAL / case["file"]).is_file() for case in CASES.values())
    assert Path(EVAL / "texts").is_dir()
