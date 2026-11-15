# Rules

The rule table. Code reads these files; no rule number or date is hard-coded in Python.

```
funding.json        USG Funding Department Guidelines and the USG funding web page
events.json         Trojan Event Services (TES) terms, FAQ and tabling page; Student Handbook event policy;
                    the Social Dance Approval Process; a pointer rule for the academic calendar
outside_money.json  sponsorship, co-hosting, donations, fundraising, tickets, dues, drawings and raffles
recognition.json    recognition requirements and every clause of the 2026-27 RSO Constitution Template
calendar.json       academic calendar 2026-27 (Fall 2026, Spring 2027, Summer 2027), used for dates
vocabulary.json     the names rules may use in `triggers` (event attributes, budget categories)
sources/            snapshots of the official documents; manifest.json lists them with fetch dates
```

## The rule object

| Field | Meaning |
|---|---|
| `id` | stable identifier, lowercase words joined by hyphens |
| `domain`, `kind` | file it belongs to; `deadline`, `cap`, `ineligible`, `requirement`, `blocked_period`, `allowed`, `banned`, `fund`, `clause` or `info` |
| `title`, `owner_office` | what it is and who owns it |
| `source`, `source_section`, `source_url` | document, place in it, and link (must be listed in `sources/manifest.json`) |
| `source_text` | the exact passage from the snapshot |
| `effective_date` | the source's version date (must equal `version_date` in the manifest) |
| `verified` | `read`, `fetched` or `unverified` (below) |
| `verification_note` | required unless `read`: what a person must confirm |
| `severity` | `red`, `yellow`, `office_decides` or `info`; there is no `green` |
| `message`, `fix_template` | what the officer sees; `{placeholders}` are filled by code |
| `applies_to`, `check` | plain-language description of when it applies and what is checked |
| `triggers`, `trigger_mode` | names from `vocabulary.json`; the rule applies when any (or, with `all`, every) trigger is present |
| `params` | numbers the checks use. Keys ending `_quote` must be text inside `source_text`; keys ending `_rules` must name existing rules |
| `anchor`, `offset`, `unit`, `direction` | deadline rules only: e.g. `event_date`, `6`, `weeks`, `before` |
| `conflicts_with` | rules from another source that disagree; must be listed both ways. The stricter one is applied and both are shown |
| `depends_on` | rules this one rests on; if any is not verified, this one is shown yellow too |

`required` fields: `source_url`, `source_text`, `effective_date`, `verified`, plus the rest of the schema. **Loading is all or nothing**: if any rule is malformed, nothing loads and every problem is listed (a table with one rule silently dropped would hide an obligation). Check with:

```bash
python scripts/validate_rules.py
```

## Verification marks

| Mark | Meaning | Shown as |
|---|---|---|
| `read` | `source_text` appears verbatim in the snapshot. The loader checks this every time it loads. | the rule's severity |
| `fetched` | the source was only seen through a summarising tool; the wording is not checked | yellow |
| `unverified` | an open question for a person (PROJECT_CONTEXT section 8) | yellow |

"Verbatim" means: after collapsing whitespace (and Unicode NFC composition), `source_text` is a contiguous substring of the snapshot text. A word the PDF split across two lines at a hyphen is joined back. Every other character, including curly quotes, ligatures and the source's own typos, must match.

Unverified today (each with its note): the academic-week definition behind every USG deadline (a hand transcription of USG's sign-in-only deadline table is in `sources/usg-funding-deadlines.txt`, not checkable by code), the 4-funded-events-per-semester limit, the USG vendor list, USC's approved caterers (confirmed only by phone), and the business-day assumption. Ten more rules depend on them and are shown yellow too. The academic calendar was confirmed by the user on 2026-11-14 and is `read`.

## Sources

`sources/manifest.json` lists each document: URL, fetch time, SHA-256 of the raw file and the version date. `scripts/fetch_sources.py` re-downloads them; every raw download is kept in `sources/raw/`, so each text snapshot can be re-derived offline. The USG Funding Application Deadlines table needs a USC sign-in; its snapshot is a hand transcription marked `"manual": true` in the manifest, and `fetch_sources.py` skips it.

The app never calls USC websites at run time.

## Changing a rule

1. Re-fetch the source (`python scripts/fetch_sources.py <source-id>`) if it changed.
2. Edit the rule, copying `source_text` exactly from the snapshot; set `effective_date` to the source's version date.
3. Run `python scripts/validate_rules.py`, `pytest` and `python scripts/run_eval.py`.
4. Ask a second person to compare the rule with the source.

A person reviews every rule against its source before it is used (PLAN.md, "What the humans do").
