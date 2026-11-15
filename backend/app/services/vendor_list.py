"""Match a vendor name against Greenlight's copy of USG's vendor list (rule usg-vendor-list, two snapshots).

Pure Python. The list is unconfirmed and USG says it is not complete, so every result is a yellow note for a person
to check; this module only says whether the name was found and what the list's note says. Being on the list never
makes an expense eligible (the list includes talent agencies, buses and balloon vendors): the eligibility check is
separate.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.rules import RuleSet

HEADER_END = "==== END OF SNAPSHOT HEADER ===="
SUFFIXES = {"inc", "llc", "co", "corp", "corporation", "ltd", "company", "the", "lp", "pc", "dba"}
CHECK_STATUS = re.compile(r"inactive|not found|registration(?: status)?\s*:\s*(none|ip|in progress|invited)", re.IGNORECASE)


@dataclass(frozen=True)
class ListedVendor:
    name: str
    note: str
    tab: str

    @property
    def needs_status_check(self) -> bool:
        return bool(CHECK_STATUS.search(self.note))


def normalize_name(text: str) -> str:
    """Lowercase letters and digits only, company suffixes dropped ("Casa Sanchez Restaurant, Inc" ->
    "casa sanchez restaurant")."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    folded = folded.replace("&", " and ")
    words = re.findall(r"[a-z0-9]+", folded)
    return " ".join(word for word in words if word not in SUFFIXES)


def _aliases(name: str) -> set[str]:
    """The name as written, and each part in brackets or on its own line, as separate names."""
    parts = {name}
    parts.update(re.findall(r"[\[(]([^\])]+)[\])]", name))
    parts.add(re.sub(r"[\[(][^\])]*[\])]", " ", name))
    parts.update(name.splitlines())
    return {alias for alias in (normalize_name(part) for part in parts) if len(alias) >= 3}


def _body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.partition(HEADER_END)[2]


def _rows(path: Path, tab: str) -> list[ListedVendor]:
    vendors: list[ListedVendor] = []
    reader = csv.reader(io.StringIO(_body(path)))
    name_col, note_cols = None, []
    for row in reader:
        cells = [cell.strip() for cell in row]
        lowered = [cell.lower() for cell in cells]
        if "vendor name" in lowered and name_col is None:
            name_col = lowered.index("vendor name")
            note_cols = [i for i, cell in enumerate(lowered) if cell in ("note", "notes")]
            continue
        if name_col is None or len(cells) <= name_col or not cells[name_col]:
            continue
        others = [cell for i, cell in enumerate(cells) if i != name_col and cell]
        if not others:
            continue  # a group heading such as "Audio Visual / Technical"
        note = " ".join(cells[i] for i in note_cols if i < len(cells) and cells[i])
        vendors.append(ListedVendor(name=cells[name_col], note=note, tab=tab))
    return vendors


@lru_cache(maxsize=4)
def _load(sources_dir: str, files: tuple[str, ...]) -> tuple[ListedVendor, ...]:
    vendors: list[ListedVendor] = []
    for name in files:
        path = Path(sources_dir) / name
        if path.is_file():
            vendors.extend(_rows(path, "Food Vendors" if "other" not in name else "Other Vendors"))
    return tuple(vendors)


def listed_vendors(ruleset: RuleSet, sources_dir: Path) -> tuple[ListedVendor, ...]:
    files = tuple(ruleset.get("usg-vendor-list").params.get("snapshots", ())) if "usg-vendor-list" in ruleset else ()
    return _load(str(sources_dir), files)


def find_vendor(name: str, vendors: tuple[ListedVendor, ...]) -> ListedVendor | None:
    """The listed vendor whose name (or a bracketed alias) equals this name once normalised, or None."""
    wanted = normalize_name(name)
    if len(wanted) < 3:
        return None
    for vendor in vendors:
        if wanted in _aliases(vendor.name):
            return vendor
    return None
