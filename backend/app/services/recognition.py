"""The recognition check, end to end: read the upload, let the AI reader read, let code decide."""

from __future__ import annotations

from typing import Any

from app.rules import RuleSet, citation_for
from app.schemas.common import Verdict
from app.services.recognition_check import (
    ConstitutionReport,
    ReportNote,
    check_constitution,
    template_year,
    unreadable_report,
)
from app.services.recognition_document import (
    MAX_TEXT_CHARS,
    MIN_READABLE_CHARS,
    ReadDocument,
    UnreadableDocument,
    read_pasted_text,
    read_upload,
    readable_characters,
)
from app.services.recognition_intake import read_answers, transcribe

TEMPLATE_RULE = "recognition-constitution-template"
KIND_LABELS = {"pasted_text": "pasted text", "text_file": "a text file", "docx": "a Word document", "pdf": "a PDF",
               "image": "an image"}


def check_upload(
    ruleset: RuleSet,
    club: dict[str, bool | None],
    *,
    filename: str | None = None,
    data: bytes | None = None,
    text: str | None = None,
    client: Any | None = None,
) -> tuple[ConstitutionReport, list[Any]]:
    """Check an uploaded file or pasted text. Returns the report and the AI results (for the audit log).
    A file that cannot be read gives a report that says so; it never gives a pass."""
    try:
        document = read_upload(filename or "upload", data) if data is not None else read_pasted_text(text or "")
    except UnreadableDocument as exc:
        return unreadable_report(str(exc)), []

    ai_results: list[Any] = []
    transcribed = False
    body = document.text
    if document.needs_transcription is not None:
        scan, media_type = document.needs_transcription
        typed, message, results = transcribe(scan, media_type, client)
        ai_results.extend(results)
        if typed is None or readable_characters(typed) < MIN_READABLE_CHARS:
            return _with_document(unreadable_report(message or "Greenlight could not read any text in this file."), document), ai_results
        body, transcribed = typed[:MAX_TEXT_CHARS], True

    reader = read_answers(body, ruleset, client)
    ai_results.extend(reader.results)
    report = check_constitution(
        body, ruleset, club, answers=reader.answers, transcribed=transcribed,
        form_layout=document.kind == "pdf" and bool(document.fillable),
    )
    notes = list(report.notes) + _format_notes(ruleset, document)
    if document.damaged_pages:
        pages = ", ".join(str(number) for number in document.damaged_pages)
        notes.insert(0, ReportNote(
            kind="damaged_pages", verdict=Verdict.YELLOW,
            message=f"Part of this PDF is damaged: Greenlight could not read page{'s' if len(document.damaged_pages) > 1 else ''} "
                    f"{pages}. Clauses on those pages may be listed as missing only because they could not be read. "
                    "Download or export the file again and re-check it.",
        ))
    overall = report.overall
    if overall is Verdict.GREEN and any(note.verdict is Verdict.YELLOW for note in notes):
        overall = Verdict.YELLOW
    report = report.model_copy(update={
        "notes": notes,
        "overall": overall,
        "message": report.message if overall is report.overall else
        "No clause is missing or changed, but some items need a human look before you submit.",
        "reader": {"used": reader.answers is not None, "message": reader.message},
    })
    return _with_document(report, document), ai_results


def _with_document(report: ConstitutionReport, document: ReadDocument) -> ConstitutionReport:
    return report.model_copy(update={"document": {
        "name": document.name, "kind": document.kind, "kind_label": KIND_LABELS[document.kind],
        "pages": document.pages, "fillable": document.fillable,
    }})


def _format_notes(ruleset: RuleSet, document: ReadDocument) -> list[ReportNote]:
    """Campus Activities accepts only the fillable PDF template; say so when the upload is something else."""
    if TEMPLATE_RULE not in ruleset:
        return []
    rule = ruleset.get(TEMPLATE_RULE)
    citation = citation_for(ruleset, TEMPLATE_RULE)
    year = template_year(ruleset) or "current"
    if document.kind == "pdf" and document.fillable:
        return []
    if document.kind == "pdf":
        return [ReportNote(
            kind="not_fillable", verdict=Verdict.YELLOW, citation=citation,
            message=f"This PDF has no form fields, so it looks printed to PDF or flattened. {rule.message}",
        )]
    return [ReportNote(
        kind="not_the_form", verdict=None, citation=citation,
        message=f"Greenlight checked the wording of {KIND_LABELS[document.kind]}. When it is ready, enter it in the "
                f"{year} fillable PDF template: {rule.message}",
    )]
