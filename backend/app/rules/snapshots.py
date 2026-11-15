"""Snapshots of the official source documents, and exact-text matching against them.

The snapshots live in rules/sources/. Each `<id>.txt` starts with a short header that ends
with HEADER_END; everything after it is the document text. rules/sources/manifest.json maps
each source URL to its snapshot file.

"Matches its snapshot exactly" means: after Unicode NFKC normalisation and collapsing every
run of whitespace to a single space, the rule's `source_text` is a contiguous substring of
the snapshot text. Whitespace is not meaningful in text extracted from PDFs and web pages
(line breaks fall wherever the layout put them); every other character must be identical.
One layout artefact is also undone: a word that the PDF broke across two lines at a hyphen
("full-" at the end of a line, "time" on the next) is joined back ("full-time"). The hyphen
itself is kept.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urldefrag

HEADER_END = "==== END OF SNAPSHOT HEADER ===="

# Characters that carry no text: soft hyphen, zero-width space/joiners, byte-order mark.
_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍⁠﻿"), None)
# A hyphen (ASCII or U+2010) right after a non-space character, followed by a line break.
_LINE_BREAK_HYPHEN = re.compile(r"(?<=\S)([-‐])[ \t]*\r?\n\s*")


def normalize(text: str) -> str:
    """Normalise text for exact matching: NFKC, invisible characters removed, words broken at a
    line-end hyphen joined, whitespace collapsed."""
    text = unicodedata.normalize("NFKC", text).translate(_INVISIBLE)
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


class ManifestError(ValueError):
    """The source manifest is missing or malformed."""


def load_manifest(sources_dir: Path) -> dict[str, Source]:
    """Return the sources keyed by canonical URL."""
    path = sources_dir / "manifest.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"{path}: source manifest not found") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{path}: not valid JSON ({exc})") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        raise ManifestError(f"{path}: expected an object with a 'sources' list")

    sources: dict[str, Source] = {}
    for index, entry in enumerate(raw["sources"]):
        where = f"{path}: sources[{index}]"
        if not isinstance(entry, dict):
            raise ManifestError(f"{where}: expected an object")
        for key in ("id", "title", "owner", "url"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ManifestError(f"{where}: '{key}' is required")
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
        )
        key = canonical_url(source.url)
        if key in sources:
            raise ManifestError(f"{where}: url {source.url} is listed twice")
        sources[key] = source
    return sources


@lru_cache(maxsize=64)
def _read_body(path: str, mtime_ns: int) -> str:
    text = Path(path).read_text(encoding="utf-8")
    head, sep, body = text.partition(HEADER_END)
    if not sep:
        raise ManifestError(f"{path}: snapshot header end marker not found")
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
    return _read_body(str(path), path.stat().st_mtime_ns)


def text_in_snapshot(quote: str, snapshot: str) -> bool:
    """True if `quote` appears in the (already normalised) snapshot text, after normalisation."""
    needle = normalize(quote)
    return bool(needle) and needle in snapshot
