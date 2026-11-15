"""The AI reader for constitutions. It reads; it never checks.

Two jobs, both returning typed data that code then checks:
  1. type out a file that has no text layer (a scan or a photo), and
  2. answer fixed yes/no questions about what the officer wrote in the template's blanks.

The questions come from the rule table (recognition_check.reader_questions), never from the upload.
The uploaded text travels as an UntrustedDocument, so nothing in it is followed as an instruction.
If the reader is unavailable, the caller shows the affected items as "needs a human look".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.ai import AIError, AIResult, ClaudeClient, Confidence, RecordingNotFound, UntrustedDocument
from app.rules import RuleSet
from app.services.recognition_check import ReaderAnswer, reader_questions

# A fixed name: the officer's file name is never sent to the model.
DOCUMENT_NAME = "constitution"

ANSWERS_TASK = "constitution-answers"
ANSWERS_INSTRUCTIONS = """\
The document is a student organization's constitution, written on a university template. The officers
typed their own wording into the template's blanks. You will get numbered yes/no questions, each about
what the officers wrote in one named part of the document.
For each question:
- answer "yes" only if the document's own words in that part say so;
- answer "no" if they do not. A part that says nothing about the question is a "no", with high confidence;
- answer "unclear" only if the part is missing or unreadable, or its wording could be read either way;
- give your confidence in that answer;
- in `evidence`, copy the exact words from that part of the document that your answer rests on, without
  changing them, or null if there are none.
Answer every question once, using its number. Do not judge whether the constitution is acceptable.
"""

TRANSCRIBE_TASK = "constitution-transcribe"
TRANSCRIBE_INSTRUCTIONS = """\
The document is a scan or photo of a student organization's constitution. Type out its text exactly as
written, in reading order, one heading or numbered part per line. Keep every heading ("ARTICLE II.",
"Section A:", "Part 1.") as it appears. Put handwritten or typed-in answers where they appear in the
sentence. Where a blank is left empty, write "____". Do not correct, complete, translate or summarise
anything, and do not add wording you expect a constitution to have. If you cannot read a passage, write
"[unreadable]" in its place. Set `readable` to "no" if the file has no legible constitution text.
"""


class AnswerOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: int
    answer: Literal["yes", "no", "unclear"]
    confidence: Confidence
    evidence: str | None


class ConstitutionAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[AnswerOut]


class Transcription(BaseModel):
    model_config = ConfigDict(extra="forbid")

    readable: Literal["yes", "partly", "no"]
    text: str


@dataclass
class ReaderOutcome:
    """What the reader returned. `answers` is None when it did not run or its answer was unusable."""

    answers: dict[tuple[str, str], ReaderAnswer] | None
    message: str
    results: list[AIResult[Any]] = field(default_factory=list)


def _why_unavailable(exc: AIError) -> str:
    if isinstance(exc, RecordingNotFound):
        return "Greenlight's AI reader is switched off in this copy (it replays saved answers only)."
    return f"Greenlight's AI reader could not be used: {exc}"


def read_answers(text: str, ruleset: RuleSet, client: ClaudeClient | None = None) -> ReaderOutcome:
    """Ask the reader the fixed questions about the fill-ins. Never raises: a failure means no answers."""
    questions = reader_questions(ruleset)
    if not questions:
        return ReaderOutcome(answers={}, message="No questions to ask.")
    request = "Answer these questions about the document:\n" + "\n".join(f"{q.number}. {q.text}" for q in questions)
    try:
        result = (client or ClaudeClient()).extract(
            task=ANSWERS_TASK,
            instructions=ANSWERS_INSTRUCTIONS,
            request=request,
            documents=[UntrustedDocument(name=DOCUMENT_NAME, text=text)],
            output_type=ConstitutionAnswers,
            max_tokens=4000,
        )
    except (AIError, ValueError) as exc:
        reason = _why_unavailable(exc) if isinstance(exc, AIError) else "The document is too long for the AI reader."
        return ReaderOutcome(answers=None, message=f"{reason} Answers typed into the membership blanks were not read "
                                                   "against the membership rules; they are marked for a human look.")
    by_number: dict[int, list[AnswerOut]] = {}
    for answer in result.output.answers:
        by_number.setdefault(answer.question, []).append(answer)
    answers: dict[tuple[str, str], ReaderAnswer] = {}
    for question in questions:
        given = by_number.get(question.number, [])
        if len(given) == 1:
            answers[(question.clause_rule_id, question.banned_rule_id)] = ReaderAnswer(
                answer=given[0].answer, confident=given[0].confidence == "high", evidence=given[0].evidence
            )
        # A question answered twice or not at all stays unanswered, which the check shows as yellow.
    return ReaderOutcome(answers=answers, message="The AI reader read the answers typed into the blanks; code made every "
                                                  "decision.", results=[result])


def transcribe(data: bytes, media_type: str, client: ClaudeClient | None = None) -> tuple[str | None, str, list[AIResult[Any]]]:
    """Type out a file that has no text layer. Returns (text or None, message, AI results)."""
    try:
        result = (client or ClaudeClient()).extract(
            task=TRANSCRIBE_TASK,
            instructions=TRANSCRIBE_INSTRUCTIONS,
            request="Type out the text of this document.",
            documents=[UntrustedDocument(name=DOCUMENT_NAME, data=data, media_type=media_type)],
            output_type=Transcription,
            max_tokens=16000,
        )
    except (AIError, ValueError) as exc:
        reason = _why_unavailable(exc) if isinstance(exc, AIError) else str(exc)
        return None, (
            "This file has no text Greenlight can read directly (it looks like a scan or a photo). "
            f"{reason} Paste the constitution's text instead, or upload the fillable PDF."
        ), []
    if result.output.readable == "no" or not result.output.text.strip():
        return None, ("Greenlight could not read any constitution text in this file. Upload a clearer copy, the fillable "
                      "PDF, or paste the text."), [result]
    return result.output.text, "", [result]
