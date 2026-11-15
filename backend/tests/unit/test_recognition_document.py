"""Reading uploads: the real template PDF, filled copies, Word files, scans and broken files."""

from __future__ import annotations

import io
from typing import Any

import docx
import pytest
from pypdf import PdfReader, PdfWriter

from app.config import REPO_ROOT
from app.rules import get_ruleset
from app.schemas.common import Verdict
from app.services.recognition import check_upload
from app.services.recognition_document import UnreadableDocument, read_pasted_text, read_upload

TEMPLATE_PDF = REPO_ROOT / "rules" / "sources" / "raw" / "constitution-template.pdf"
CLEAN = (REPO_ROOT / "data" / "eval" / "constitutions" / "texts" / "co-01.txt").read_text(encoding="utf-8")


def _template() -> PdfReader:
    reader = PdfReader(io.BytesIO(TEMPLATE_PDF.read_bytes()))
    if reader.is_encrypted:
        reader.decrypt("")
    return reader


def _filled(values: dict[str, str]) -> bytes:
    writer = PdfWriter(clone_from=_template())
    for page in writer.pages:
        writer.update_page_form_field_values(page, values, auto_regenerate=False)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.fixture(scope="module")
def ruleset() -> Any:
    return get_ruleset()


def test_real_template_pdf_parses_despite_encryption_flag() -> None:
    document = read_upload("2026-27-RSO-Constitution-Template-1.pdf", TEMPLATE_PDF.read_bytes())
    assert document.kind == "pdf" and document.pages == 16 and document.fillable is True
    assert "ARTICLE VIII" in document.text and document.needs_transcription is None


def test_blank_template_is_red_never_green(ruleset: Any) -> None:
    report, _ = check_upload(ruleset, {}, filename="t.pdf", data=TEMPLATE_PDF.read_bytes())
    assert report.readable and report.overall is Verdict.RED
    assert report.summary["missing"] >= 40


def test_typed_form_fields_are_read(ruleset: Any) -> None:
    names = list(_template().get_fields())
    data = _filled({name: f"Answer for {name}" for name in names})
    document = read_upload("filled.pdf", data)
    assert "Answer for RSO Purpose" in document.text
    report, _ = check_upload(ruleset, {}, filename="filled.pdf", data=data)
    states = {r.rule_id: r.state for r in report.clauses}
    assert states["clause-i-b-1"] == "present"
    assert states["clause-preamble-name"] == "present"
    assert report.summary["missing"] <= 3


def test_flattened_pdf_gets_a_template_note(ruleset: Any) -> None:
    writer = PdfWriter(clone_from=_template())
    writer.remove_annotations(subtypes="/Widget")
    if "/AcroForm" in writer._root_object:
        del writer._root_object["/AcroForm"]
    out = io.BytesIO()
    writer.write(out)
    report, _ = check_upload(ruleset, {}, filename="flat.pdf", data=out.getvalue())
    assert "not_fillable" in {note.kind for note in report.notes}


def test_password_protected_pdf_gives_a_clear_message() -> None:
    writer = PdfWriter(clone_from=_template())
    writer.encrypt(user_password="secret", owner_password="owner")
    out = io.BytesIO()
    writer.write(out)
    with pytest.raises(UnreadableDocument, match="password"):
        read_upload("locked.pdf", out.getvalue())


@pytest.mark.parametrize("data", [TEMPLATE_PDF.read_bytes()[:5000], b"%PDF-1.7\nnot really a pdf"])
def test_damaged_pdf_gives_a_clear_message(data: bytes, ruleset: Any) -> None:
    report, _ = check_upload(ruleset, {}, filename="broken.pdf", data=data)
    assert not report.readable and report.overall is None and report.message


def test_pdf_without_text_goes_to_the_reader_and_is_unreadable_when_it_is_off(ruleset: Any) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    writer.write(out)
    document = read_upload("scan.pdf", out.getvalue())
    assert document.needs_transcription is not None
    report, _ = check_upload(ruleset, {}, filename="scan.pdf", data=out.getvalue())
    assert not report.readable and report.overall is None and "scan" in report.message


def test_image_is_sent_for_transcription_not_passed(ruleset: Any) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    assert read_upload("photo.png", png).needs_transcription == (png, "image/png")
    report, _ = check_upload(ruleset, {}, filename="photo.png", data=png)
    assert not report.readable and report.overall is None


def test_docx_is_read(ruleset: Any) -> None:
    document = docx.Document()
    for line in CLEAN.split("\n"):
        document.add_paragraph(line)
    out = io.BytesIO()
    document.save(out)
    report, _ = check_upload(ruleset, {}, filename="c.docx", data=out.getvalue())
    assert report.readable and report.document["kind"] == "docx"
    assert report.summary["present"] >= 80


@pytest.mark.parametrize(
    ("name", "data", "match"),
    [
        ("empty.txt", b"", "empty"),
        ("spaces.txt", b"   \n\n  ", "empty"),
        ("short.txt", b"Constitution.", "no readable text"),
        ("old.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100, ".doc"),
        ("fake.docx", b"just text pretending", "not a DOCX"),
        ("zip.docx", b"PK\x03\x04garbage", "Word"),
        ("binary.bin", bytes(range(256)) * 4, "cannot be read"),
    ],
)
def test_unreadable_uploads_are_refused_with_a_message(name: str, data: bytes, match: str) -> None:
    with pytest.raises(UnreadableDocument, match=match):
        read_upload(name, data)


def test_empty_paste_is_refused() -> None:
    with pytest.raises(UnreadableDocument):
        read_pasted_text("   ")


def test_utf16_and_bom_text_files_are_read() -> None:
    assert "ARTICLE I" in read_upload("c.txt", CLEAN.encode("utf-16")).text
    assert "ARTICLE I" in read_upload("c.txt", b"\xef\xbb\xbf" + CLEAN.encode("utf-8")).text


def test_non_english_text_is_not_a_pass(ruleset: Any) -> None:
    spanish = "CONSTITUCIÓN\nARTÍCULO I. NOMBRE Y PROPÓSITO\nSección A: NOMBRE\nParte 1. El nombre oficial es Colectivo Linterna." * 3
    report, _ = check_upload(ruleset, {}, text=spanish)
    assert report.overall is Verdict.RED
    assert "not_the_template" in {note.kind for note in report.notes}


def test_file_name_is_cleaned() -> None:
    document = read_upload("../../etc/<script>.txt", CLEAN.encode())
    assert "/" not in document.name and "<" not in document.name
