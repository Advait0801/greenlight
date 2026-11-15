"""Snapshots of the official source documents, and exact-text matching against them.

The snapshots live in rules/sources/. Each `<id>.txt` starts with a short header that ends
with HEADER_END; everything after it is the document text. rules/sources/manifest.json maps
each source URL to its snapshot file.

"Matches its snapshot exactly" means: after collapsing every run of whitespace to a single
space, the rule's `source_text` is a contiguous substring of the snapshot text. Whitespace is
not meaningful in text extracted from PDFs and web pages (line breaks fall wherever the layout
put them); every other character must be identical. Two layout artefacts are also undone:
a word that the PDF broke across two lines at a hyphen ("full-" at the end of a line, "time" on
the next) is joined back ("full-time", hyphen kept), and text is put in Unicode NFC form (the
same characters, composed the same way). No compatibility folding is done: a ligature, a
full-width digit or a curly quote must match exactly.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urldefrag

from app.jsonutil import StrictJSONError, loads_strict

HEADER_END = "==== END OF SNAPSHOT HEADER ===="

# A hyphen (ASCII or U+2010) right after a non-space character, followed by a line break.
_LINE_BREAK_HYPHEN = re.compile(r"(?<=\S)([-‐])[ \t]*\r?\n\s*")


def normalize(text: str) -> str:
    """Normalise text for exact matching: NFC, words broken at a line-end hyphen joined,
    whitespace collapsed. A byte-order mark at the very start is dropped."""
    text = unicodedata.normalize("NFC", text.removeprefix("\ufeff"))
    text = _LINE_BREAK_HYPHEN.sub(r"\1", text)
    return " ".join(text.split())


def canonical_url(url: str) -> str:
    """URL used to match a rule to its source: fragment removed, trailing whitespace ignored."""
    return urldefrag(url.strip())[0]


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    owner: str
    url: str
    snapshot: str | None
    fetched_at: str | None
    sha256: str | None
    fetchable: bool
    note: str | None
    version_date: str | None = None
    # SHA-256 of the snapshot text after the header, so an edited snapshot is refused.
    text_sha256: str | None = None


class ManifestError(ValueError):
    """The source manifest is missing or malformed."""


def load_manifest(sources_dir: Path) -> dict[str, Source]:
    """Return the sources keyed by canonical URL."""
    path = sources_dir / "manifest.json"
    try:
        raw = loads_strict(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"{path}: source manifest not found") from exc
    except UnicodeDecodeError as exc:
        raise ManifestError(f"{path}: not UTF-8 text ({exc.reason})") from exc
    except (json.JSONDecodeError, StrictJSONError) as exc:
        raise ManifestError(f"{path}: not valid JSON ({exc})") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        raise ManifestError(f"{path}: expected an object with a 'sources' list")

    sources: dict[str, Source] = {}
    for index, entry in enumerate(raw["sources"]):
        where = f"{path}: sources[{index}]"
        if not isinstance(entry, dict):
            raise ManifestError(f"{where}: expected an object")
        for key in ("id", "title", "owner", "url", "version_date"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ManifestError(f"{where}: '{key}' is required (a non-empty string)")
        for key in ("snapshot", "fetched_at", "sha256", "note", "text_sha256"):
            if entry.get(key) is not None and not isinstance(entry[key], str):
                raise ManifestError(f"{where}: '{key}' must be a string")
        if not isinstance(entry.get("fetchable", True), bool):
            raise ManifestError(f"{where}: 'fetchable' must be true or false")
        try:
            date.fromisoformat(entry["version_date"])
        except ValueError as exc:
            raise ManifestError(f"{where}: version_date '{entry['version_date']}' is not a real date") from exc
        source = Source(
            id=entry["id"],
            title=entry["title"],
            owner=entry["owner"],
            url=entry["url"],
            snapshot=entry.get("snapshot"),
            fetched_at=entry.get("fetched_at"),
            sha256=entry.get("sha256"),
            fetchable=entry.get("fetchable", True) is not False,
            note=entry.get("note"),
            version_date=entry.get("version_date"),
            text_sha256=entry.get("text_sha256"),
        )
        if source.snapshot and not source.text_sha256:
            raise ManifestError(f"{where}: '{source.id}' has a snapshot but no text_sha256 to check it against")
        key = canonical_url(source.url)
        if key in sources:
            raise ManifestError(f"{where}: url {source.url} is listed twice")
        sources[key] = source
    return sources


def snapshot_body_sha256(text: str) -> str:
    """The hash recorded as text_sha256: the snapshot file's text after its header line."""
    return hashlib.sha256(text.partition(HEADER_END)[2].encode("utf-8")).hexdigest()


@lru_cache(maxsize=64)
def _read_body(path: str, mtime_ns: int, expected_sha256: str | None = None) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError(f"{path}: snapshot is not UTF-8 text ({exc.reason})") from exc
    head, sep, body = text.partition(HEADER_END)
    if not sep:
        raise ManifestError(f"{path}: snapshot header end marker not found")
    if expected_sha256 is not None and snapshot_body_sha256(text) != expected_sha256:
        raise ManifestError(
            f"{Path(path).name}: the snapshot text differs from the text_sha256 recorded in the manifest; "
            "a snapshot is only changed by scripts/fetch_sources.py"
        )
    return normalize(body)


def snapshot_text(sources_dir: Path, source: Source) -> str:
    """Normalised body text of a source's snapshot. Raises ManifestError if there is none."""
    if not source.snapshot:
        raise ManifestError(f"source '{source.id}' has no snapshot (run scripts/fetch_sources.py)")
    path = (sources_dir / source.snapshot).resolve()
    if sources_dir.resolve() not in path.parents:
        raise ManifestError(f"source '{source.id}': snapshot path escapes {sources_dir}")
    if not path.is_file():
        raise ManifestError(f"source '{source.id}': snapshot file {path.name} is missing")
    try:
        return _read_body(str(path), path.stat().st_mtime_ns, source.text_sha256)
    except ManifestError as exc:
        raise ManifestError(f"source '{source.id}': {exc}") from exc


def text_in_snapshot(quote: str, snapshot: str) -> bool:
    """True if `quote` appears in the (already normalised) snapshot text, after normalisation,
    starting and ending on a word boundary: a quote may not cut a word or number in half
    ("exceed a $3" is not a quote of "exceed a $35")."""
    needle = normalize(quote)
    if not needle:
        return False
    start = snapshot.find(needle)
    while start >= 0:
        end = start + len(needle)
        clean_start = start == 0 or not (snapshot[start - 1].isalnum() and needle[0].isalnum())
        clean_end = end == len(snapshot) or not (snapshot[end].isalnum() and needle[-1].isalnum())
        # A number continues through a decimal point or thousands comma: "$35" or "$35." is not a quote
        # of "$35.50", and "$8," is not a quote of "$8,000".
        if needle[-1].isdigit() and snapshot[end : end + 1] in (".", ",") and snapshot[end + 1 : end + 2].isdigit():
            clean_end = False
        if needle[-1] in ".," and len(needle) > 1 and needle[-2].isdigit() and snapshot[end : end + 1].isdigit():
            clean_end = False
        if needle[0] in ".," and start > 0 and snapshot[start - 1].isdigit() and needle[1:2].isdigit():
            clean_start = False
        if needle[0].isdigit() and start >= 2 and snapshot[start - 1] in (".", ",") and snapshot[start - 2].isdigit():
            clean_start = False
        if clean_start and clean_end:
            return True
        start = snapshot.find(needle, start + 1)
    return False
