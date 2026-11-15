"""Turn an uploaded constitution (pasted text, TXT, DOCX or PDF) into plain text. No AI here.

A file that code cannot read as text (a scanned PDF, a photo) is handed back as `needs_transcription`,
so the caller can ask the AI reader to transcribe it. A file that cannot be read at all gives a
clear message; it is never treated as an empty constitution that passes.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from typing import Any, Literal

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARS = 400_000
# A Word file is a zip: its unzipped size is checked before parsing, so a small upload cannot expand to gigabytes.
MAX_DOCX_UNZIPPED_BYTES = 50 * 1024 * 1024
# Fewer letters and digits than this is not a constitution; the check refuses instead of guessing.
MIN_READABLE_CHARS = 40
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}

SourceKind = Literal["pasted_text", "text_file", "docx", "pdf", "image"]


class UnreadableDocument(Exception):
    """The upload cannot be read. The message is shown to the officer as it is."""


@dataclass(frozen=True)
class ReadDocument:
    name: str
    kind: SourceKind
    text: str
    pages: int | None = None
    # PDF only: True when the file has form fields (the fillable template), False when it has none.
    fillable: bool | None = None
    # Set when code found no usable text: the original bytes and media type, for the AI reader.
    needs_transcription: tuple[bytes, str] | None = None
    # PDF only: page numbers (from 1) whose text could not be read because that part of the file is damaged.
    damaged_pages: tuple[int, ...] = ()


def readable_characters(text: str) -> int:
    return sum(1 for char in text if char.isalnum())


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    return "".join(char for char in text if char in "\n\t" or char.isprintable())


def _decode(data: bytes) -> str:
    # UTF-16 only with its byte-order mark; otherwise UTF-8, then Windows-1252 (Word's "plain text" on Windows).
    encodings = ("utf-16",) if data.startswith((b"\xff\xfe", b"\xfe\xff")) else ("utf-8-sig", "cp1252")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnreadableDocument(
        "This file is not readable text. Upload the constitution as a PDF, a Word document (.docx) or a text file, "
        "or paste the text."
    )


def _docx_text(data: bytes) -> str:
    try:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        if sum(info.file_size for info in zipfile.ZipFile(io.BytesIO(data)).infolist()) > MAX_DOCX_UNZIPPED_BYTES:
            raise UnreadableDocument("This Word document is too large once unzipped. Paste the text instead.")
        document = docx.Document(io.BytesIO(data))
        lines: list[str] = []
        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                lines.append(block.text)
            elif isinstance(block, Table):
                for row in block.rows:
                    lines.append("  ".join(cell.text for cell in row.cells))
        return "\n".join(lines)
    except UnreadableDocument:
        raise
    except Exception as exc:  # python-docx raises many types on a damaged file
        raise UnreadableDocument(
            "This Word document could not be opened. It may be damaged or password-protected. "
            "Save it again as .docx, or paste the text."
        ) from exc


def _field_value(annotation: Any) -> str | None:
    """The text typed into a form field (a widget), or None for buttons and empty fields."""
    node, value, field_type = annotation, None, None
    for _ in range(5):  # a widget may inherit its value and type from a parent field
        if value is None:
            value = node.get("/V")
        if field_type is None:
            field_type = node.get("/FT")
        parent = node.get("/Parent")
        if parent is None:
            break
        node = parent.get_object()
    if field_type != "/Tx" or value is None:
        return None
    text = str(value).strip()
    return text or None


class DamagedPage(Exception):
    """The page's content could not be decoded."""


def _page_lines(page: Any) -> list[str]:
    """The page's text, line by line, with each filled-in form field placed where it sits on the page.
    Raises DamagedPage when the page's content cannot be decoded, so the loss is reported, not hidden."""
    chunks: list[tuple[float, float, str]] = []  # (y, x, text)

    def visit(text: str, _cm: Any, tm: Any, _font: Any, _size: Any) -> None:
        if text and text.strip():
            chunks.append((float(tm[5]), float(tm[4]), text))

    try:
        page.extract_text(visitor_text=visit)
    except Exception as exc:
        raise DamagedPage from exc
    fields: list[tuple[float, float, float, str]] = []  # (bottom, top, x, value)
    for ref in page.get("/Annots") or []:
        try:
            annotation = ref.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            value = _field_value(annotation)
            rect = [float(number) for number in annotation.get("/Rect", [])]
        except Exception:
            continue
        if value and len(rect) == 4:
            fields.append((min(rect[1], rect[3]), max(rect[1], rect[3]), min(rect[0], rect[2]), value))

    lines: list[list[tuple[float, float, str]]] = []
    for y, x, text in sorted(chunks, key=lambda chunk: (-chunk[0], chunk[1])):
        if lines and abs(lines[-1][0][0] - y) <= 3:
            lines[-1].append((y, x, text))
        else:
            lines.append([(y, x, text)])
    for bottom, top, x, value in fields:
        value = " ".join(value.split())
        # A one-line field sits on the text line whose baseline is just above the field's bottom edge.
        near = [line for line in lines if bottom - 4 <= line[0][0] <= top + 2] if top - bottom <= 40 else []
        if near:
            target = min(near, key=lambda line: abs(line[0][0] - (bottom + 4)))
            target.append((target[0][0], x, f" {value} "))
        else:
            # A tall answer box sits under its lead-in; it becomes its own line at the top of the box.
            lines.append([(top - 1, x, value)])
    lines.sort(key=lambda line: -line[0][0])
    return ["".join(text for _, _, text in sorted(line, key=lambda chunk: chunk[1])).rstrip() for line in lines]


def _read_pdf(name: str, data: bytes) -> ReadDocument:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise UnreadableDocument(
                "This PDF is password-protected, so Greenlight cannot open it. Remove the password, or paste the text."
            )
        pages = len(reader.pages)
        fillable = bool(reader.get_fields())
        lines: list[str] = []
        damaged: list[int] = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                lines.extend(_page_lines(page))
            except DamagedPage:
                damaged.append(number)
    except UnreadableDocument:
        raise
    except Exception as exc:  # pypdf raises many types on a damaged file
        raise UnreadableDocument(
            "This PDF could not be opened. It may be damaged or cut off. Download it again, or paste the text."
        ) from exc
    if pages == 0:
        raise UnreadableDocument("This PDF has no pages.")
    text = _clean("\n".join(lines))
    if readable_characters(text) < MIN_READABLE_CHARS:
        # No text layer: a scan or a photo saved as PDF. Only the AI reader can read it.
        return ReadDocument(name=name, kind="pdf", text="", pages=pages, fillable=fillable,
                            needs_transcription=(data, "application/pdf"), damaged_pages=tuple(damaged))
    return ReadDocument(name=name, kind="pdf", text=text, pages=pages, fillable=fillable, damaged_pages=tuple(damaged))


def read_pasted_text(text: str) -> ReadDocument:
    return _finish(ReadDocument(name="pasted text", kind="pasted_text", text=_clean(text)))


def read_upload(filename: str, data: bytes) -> ReadDocument:
    """Read an uploaded file by what it is (its first bytes), not only by its name."""
    name = re.sub(r"[^\w .()\-]", "_", filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])[:120] or "upload"
    if len(data) > MAX_UPLOAD_BYTES:
        raise UnreadableDocument(f"This file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB. Upload a smaller file.")
    if not data.strip():
        raise UnreadableDocument("This file is empty, so there is nothing to check.")
    suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    head = data[:8]
    if head.startswith(b"%PDF"):
        return _finish(_read_pdf(name, data))
    if head.startswith(b"PK"):
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise UnreadableDocument("This Word document could not be opened. It may be damaged. Save it again as .docx.")
        return _finish(ReadDocument(name=name, kind="docx", text=_clean(_docx_text(data))))
    image_type = (
        "image/png" if head.startswith(b"\x89PNG") else "image/jpeg" if head.startswith(b"\xff\xd8") else
        "image/gif" if head.startswith(b"GIF8") else "image/webp" if head[:4] == b"RIFF" and data[8:12] == b"WEBP" else None
    )
    if image_type:
        return ReadDocument(name=name, kind="image", text="", needs_transcription=(data, image_type))
    if head.startswith(b"\xd0\xcf\x11\xe0") or suffix == ".doc":
        raise UnreadableDocument("Old Word files (.doc) cannot be read. Save the file as .docx or PDF, or paste the text.")
    if suffix == ".pdf" or suffix == ".docx" or suffix in IMAGE_TYPES:
        raise UnreadableDocument(
            f"This file is named {suffix} but its contents are not a {suffix[1:].upper()} file. It may be damaged."
        )
    if b"\x00" in data[:4096] and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise UnreadableDocument(
            "This file type cannot be read. Upload the constitution as a PDF, a Word document (.docx) or a text file, "
            "or paste the text."
        )
    return _finish(ReadDocument(name=name, kind="text_file", text=_clean(_decode(data))))


def _finish(document: ReadDocument) -> ReadDocument:
    if document.needs_transcription is not None:
        return document
    if len(document.text) > MAX_TEXT_CHARS:
        raise UnreadableDocument(
            f"This document has more than {MAX_TEXT_CHARS:,} characters, far longer than a constitution. "
            "Upload only the constitution."
        )
    if readable_characters(document.text) < MIN_READABLE_CHARS:
        raise UnreadableDocument(
            "Greenlight found no readable text here, so there is nothing to check. "
            "Upload the filled-in constitution, or paste its text."
        )
    return document
