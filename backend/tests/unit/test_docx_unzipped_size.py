"""A small .docx must not expand to gigabytes before any check (final review F2).

Both Word readers parsed the whole archive before the character limit, so a 275 KB file used 1.2 GB of memory.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from app.api.money import _docx_text as quote_docx_text
from app.services.quote_intake import IntakeError
from app.services.recognition_document import UnreadableDocument, read_upload


def _bomb() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", b" " * (51 * 1024 * 1024))
    return buffer.getvalue()


def test_constitution_docx_too_large_unzipped_is_refused() -> None:
    data = _bomb()
    assert len(data) < 1024 * 1024
    with pytest.raises(UnreadableDocument, match="too large once unzipped"):
        read_upload("constitution.docx", data)


def test_quote_docx_too_large_unzipped_is_refused() -> None:
    with pytest.raises(IntakeError, match="too large once unzipped"):
        quote_docx_text(_bomb())
