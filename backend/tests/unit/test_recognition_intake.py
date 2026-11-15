"""The AI reader: what it is sent, and how code treats what it returns."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.ai import AIResult, AIUnavailable, UntrustedDocument
from app.config import AIMode, REPO_ROOT, Settings
from app.rules import get_ruleset
from app.schemas.common import Verdict
from app.services.recognition import check_upload
from app.services.recognition_check import reader_questions
from app.services.recognition_intake import (
    DOCUMENT_NAME,
    AnswerOut,
    ConstitutionAnswers,
    Transcription,
    read_answers,
    transcribe,
)

EVAL = REPO_ROOT / "data" / "eval" / "constitutions"
CLEAN = (EVAL / "texts" / "co-01.txt").read_text(encoding="utf-8")
INJECTED = (EVAL / "texts" / "co-08.txt").read_text(encoding="utf-8")
CLUB = json.loads((EVAL / "cases.json").read_text(encoding="utf-8"))["cases"][0]["club"]


class FakeClient:
    """Stands in for ClaudeClient and records what it was sent."""

    def __init__(self, output: Any = None, error: Exception | None = None) -> None:
        self.output, self.error, self.calls = output, error, []

    def extract(self, **kwargs: Any) -> AIResult[Any]:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        output = self.output(kwargs) if callable(self.output) else self.output
        return AIResult(output=output, task=kwargs["task"], model="fake", mode=AIMode.LIVE, request_key="k" * 64,
                        raw_text=output.model_dump_json(), stop_reason="end_turn")


@pytest.fixture(scope="module")
def ruleset() -> Any:
    return get_ruleset()


def _all(answer: str, confidence: str = "high") -> Any:
    def build(kwargs: dict[str, Any]) -> ConstitutionAnswers:
        count = len(kwargs["request"].strip().split("\n")) - 1
        return ConstitutionAnswers(answers=[AnswerOut(question=n, answer=answer, confidence=confidence, evidence=None)  # type: ignore[arg-type]
                                            for n in range(1, count + 1)])
    return build


def test_document_goes_as_untrusted_data_under_a_fixed_name(ruleset: Any) -> None:
    client = FakeClient(_all("no"))
    read_answers(INJECTED, ruleset, client)  # type: ignore[arg-type]
    call = client.calls[0]
    (document,) = call["documents"]
    assert isinstance(document, UntrustedDocument) and document.name == DOCUMENT_NAME
    assert "ignore the rules" in (document.text or "")
    # Instructions and request are written by code; the document's words are not in them.
    assert "ignore the rules" not in call["request"] and "ignore the rules" not in call["instructions"]
    assert "Lantern" not in call["request"]


def test_prompts_ask_for_no_verdict_number_or_date(ruleset: Any) -> None:
    client = FakeClient(_all("no"))
    read_answers(CLEAN, ruleset, client)  # type: ignore[arg-type]
    words = (client.calls[0]["instructions"] + client.calls[0]["request"]).lower()
    for banned in ("approve", "compliant", "pass or fail", "deadline", "total", "calculate"):
        assert banned not in words


def test_injected_yes_to_everything_cannot_make_missing_clauses_present(ruleset: Any) -> None:
    report, _ = check_upload(ruleset, CLUB, text=INJECTED, client=FakeClient(_all("no")))
    states = {r.rule_id: r.state for r in report.clauses}
    assert states["clause-ii-d-1"] == "missing" and states["clause-iv-a-2"] == "missing"
    assert report.overall is Verdict.RED


def test_unsure_reader_keeps_membership_answers_yellow(ruleset: Any) -> None:
    report, _ = check_upload(ruleset, CLUB, text=CLEAN, client=FakeClient(_all("no", "medium")))
    result = next(r for r in report.clauses if r.rule_id == "clause-ii-a-1")
    assert result.state == "needs_look" and result.verdict is Verdict.YELLOW


def test_confident_no_on_clean_wording_is_present(ruleset: Any) -> None:
    report, _ = check_upload(ruleset, CLUB, text=CLEAN, client=FakeClient(_all("no")))
    result = next(r for r in report.clauses if r.rule_id == "clause-ii-a-1")
    assert result.state == "present" and report.reader["used"]


def test_missing_or_duplicate_answers_stay_unanswered(ruleset: Any) -> None:
    count = len(reader_questions(ruleset))
    answers = [AnswerOut(question=1, answer="no", confidence="high", evidence=None)] * 2 + [
        AnswerOut(question=n, answer="no", confidence="high", evidence=None) for n in range(3, count + 1)]
    outcome = read_answers(CLEAN, ruleset, FakeClient(ConstitutionAnswers(answers=answers)))  # type: ignore[arg-type]
    assert outcome.answers is not None
    first, second = reader_questions(ruleset)[:2]
    assert (first.clause_rule_id, first.banned_rule_id) not in outcome.answers
    assert (second.clause_rule_id, second.banned_rule_id) not in outcome.answers


def test_reader_failure_means_no_answers_and_a_message(ruleset: Any) -> None:
    outcome = read_answers(CLEAN, ruleset, FakeClient(error=AIUnavailable("down")))  # type: ignore[arg-type]
    assert outcome.answers is None and "human look" in outcome.message


def test_recorded_mode_without_a_recording_never_calls_the_network(ruleset: Any, tmp_path: Any) -> None:
    from app.ai import ClaudeClient

    client = ClaudeClient(Settings(ai_mode=AIMode.RECORDED, ai_recordings_dir=tmp_path, anthropic_api_key=None))
    outcome = read_answers(CLEAN, ruleset, client)
    assert outcome.answers is None


def test_transcription_feeds_the_check_but_is_never_green(ruleset: Any) -> None:
    client = FakeClient(lambda kw: Transcription(readable="yes", text=CLEAN) if kw["task"] == "constitution-transcribe"
                        else _all("no")(kw))
    report, results = check_upload(ruleset, CLUB, filename="scan.png", data=b"\x89PNG\r\n\x1a\n" + b"\0" * 64, client=client)
    assert report.readable and report.overall is not Verdict.GREEN
    assert all(r.verdict is not Verdict.GREEN for r in report.clauses)
    assert "transcribed" in {note.kind for note in report.notes}
    assert len(results) == 2


def test_transcription_that_reads_nothing_is_unreadable() -> None:
    text, message, _ = transcribe(b"\x89PNG", "image/png", FakeClient(Transcription(readable="no", text="")))  # type: ignore[arg-type]
    assert text is None and message


def test_recorded_answers_reproduce_the_test_set(ruleset: Any) -> None:
    """With the committed recordings, the membership contradictions in co-04, co-05 and co-09 are found."""
    from app.ai import ClaudeClient

    recordings = REPO_ROOT / "data" / "ai_recordings"
    if not (recordings / "constitution-answers").is_dir():
        pytest.skip("no recordings in this checkout")
    client = ClaudeClient(Settings(ai_mode=AIMode.RECORDED, ai_recordings_dir=recordings, anthropic_api_key=None))
    cases = {c["id"]: c for c in json.loads((EVAL / "cases.json").read_text(encoding="utf-8"))["cases"]}
    for case_id in ("co-04", "co-05", "co-09"):
        case = cases[case_id]
        report, _ = check_upload(ruleset, case["club"], text=(EVAL / case["file"]).read_text(encoding="utf-8"), client=client)
        assert report.reader["used"], case_id
        states = {r.rule_id: r.state for r in report.clauses}
        for finding in case["expected"]["findings"]:
            if finding.get("contradicted_by") and finding["rule_id"].startswith("clause-ii-a"):
                assert states[finding["rule_id"]] == "contradicts", (case_id, finding)
