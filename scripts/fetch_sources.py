"""Save snapshots of the official documents to rules/sources/, with the fetch date.

Usage (from the repository root, backend dependencies installed):

    python scripts/fetch_sources.py              # fetch every source in the manifest
    python scripts/fetch_sources.py tes-faq      # fetch only the named sources

For each source in rules/sources/manifest.json this writes:
  - raw/<id>.<ext>   the file exactly as downloaded
  - <id>.txt         a plain-text snapshot: a short header, then the document text
and records fetched_at, sha256 and size in the manifest.

This is a maintenance script. The app never calls USC websites at run time; it reads the
snapshots. After a re-fetch, run `python scripts/validate_rules.py`: any rule marked
"read" whose text is no longer in its snapshot will fail and must be re-checked by hand.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from _common import SOURCES_DIR, use_backend

use_backend()

from app.rules.snapshots import HEADER_END, snapshot_body_sha256  # noqa: E402

MANIFEST = SOURCES_DIR / "manifest.json"
RAW_DIR = SOURCES_DIR / "raw"
USER_AGENT = "Mozilla/5.0 (compatible; greenlight-snapshot/0.1)"
EXTENSIONS = {"pdf": "pdf", "html": "html", "txt": "txt", "csv": "csv"}


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310 - fixed https URLs from the manifest
        data: bytes = response.read()
    return data


def pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        # The constitution template is flagged as encrypted with an empty user password.
        reader.decrypt("")
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        pages.append(f"[page {number}]\n{page.extract_text() or ''}")
    return "\n\n".join(pages)


def html_to_text(data: bytes) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(data, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template", "iframe"]):
        tag.decompose()
    root = soup.find("main") or soup.body or soup
    for tag in root.find_all(["nav", "header", "footer"]):
        tag.decompose()
    lines = [line.strip() for line in root.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def to_text(data: bytes, fmt: str) -> str:
    if fmt == "pdf":
        return pdf_to_text(data)
    if fmt == "html":
        return html_to_text(data)
    return data.decode("utf-8-sig")


def fetch_one(source: dict[str, Any]) -> None:
    source_id = source["id"]
    data = download(source["fetch_url"])
    fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    digest = hashlib.sha256(data).hexdigest()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{source_id}.{EXTENSIONS[source['format']]}"
    raw_path.write_bytes(data)

    header = "\n".join(
        [
            f"SNAPSHOT OF: {source['title']}",
            f"URL: {source['url']}",
            f"FETCHED FROM: {source['fetch_url']}",
            f"FETCHED AT: {fetched_at}",
            f"RAW SHA-256: {digest}",
            f"FORMAT: {source['format']}",
            HEADER_END,
        ]
    )
    text = to_text(data, source["format"])
    snapshot = f"{header}\n{text}\n"
    (SOURCES_DIR / f"{source_id}.txt").write_text(snapshot, encoding="utf-8")
    source["text_sha256"] = snapshot_body_sha256(snapshot)

    source["snapshot"] = f"{source_id}.txt"
    source["raw"] = f"raw/{raw_path.name}"
    source["fetched_at"] = fetched_at
    source["sha256"] = digest
    source["bytes"] = len(data)
    print(f"ok   {source_id:36} {len(data):>9} bytes  {fetched_at}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="*", help="source ids to fetch (default: all)")
    args = parser.parse_args(argv)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    known = {source["id"] for source in manifest["sources"]}
    unknown = sorted(set(args.ids) - known)
    if unknown:
        print(f"Unknown source id(s): {', '.join(unknown)}. Known: {', '.join(sorted(known))}", file=sys.stderr)
        return 2

    failures = 0
    for source in manifest["sources"]:
        if args.ids and source["id"] not in args.ids:
            continue
        if source.get("fetchable") is False:
            print(f"skip {source['id']:36} {source.get('note', 'marked not fetchable')}")
            continue
        try:
            fetch_one(source)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            failures += 1
            print(f"FAIL {source['id']:36} {exc}", file=sys.stderr)

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if failures:
        print(f"{failures} source(s) failed; their previous snapshots were kept.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
