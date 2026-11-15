# Progress log

The orchestrator updates this file after every build step and every iteration. A new session should be able to resume from this file alone.

Final reviewers in Phase 7 must **not** read this file.

## Current state

- **Phase:** 0 — Foundation
- **Step:** iteration 1 (verify) done and fixed; iteration 2 (break) next
- **Next action:** run iteration 2 with a fresh `breaker` sub-agent (PLAN.md section 1)
- **Blocked on humans:** a person must confirm the four open questions (answers researched, see below) and review the rule table by hand (PLAN.md section 3); a person must compare the hand-transcribed USG deadline table with the sheet.

## Phase status

| Phase | Goal | Build | Iterations run | Last iteration clean? | Gate |
|---|---|---|---|---|---|
| 0 | Foundation | done | 1 | yes (0 blocker, 0 high) | open |
| 1 | Recognition check | — | 0 | — | open |
| 2 | Event packet | — | 0 | — | open |
| 3 | Money check | — | 0 | — | open |
| 4 | Year plan | — | 0 | — | open |
| 5 | Supporting features and USG screen | — | 0 | — | open |
| 6 | Ship | — | 0 | — | open |
| 7 | Final review (F1, F2, F3) and freeze | — | 0 | — | open |

## Phase 0 build (2026-11-14)

What exists now:
- **Backend** (`backend/`): FastAPI app with `GET /health`, `GET /rules`, `GET /rules/{id}`; routers in `app/api/` are discovered automatically. SQLAlchemy tables for every table in PROJECT_CONTEXT section 5 (money in whole cents). Settings from env and `.env`.
- **Claude client** (`app/ai/`): structured output via `messages.parse` validated against Pydantic models; `AI_MODE` = `recorded` (default; replay only, never the network), `live`, or `record` (live + save). Untrusted text is HTML-escaped inside `<document>` wrappers and the system prompt says it is data. Recordings store document fingerprints, not text. One live smoke call (Haiku, 2026-11-14) confirmed structured output works and an injected "mark this approved" was reported as document content.
- **Source snapshots** (`rules/sources/`): 18 sources (one a manual transcription) in `manifest.json` with fetch time, SHA-256 and version date; text snapshots committed; small raw PDFs/CSVs committed, the 6.7 MB Handbook PDF and raw HTML not.
- **Rule table**: 259 rules (`funding` 69, `events` 61, `outside_money` 19, `recognition` 110 incl. every constitution template clause). 253 `read` (each `source_text` cut verbatim from its snapshot and re-checked on every load), 6 `unverified`; 13 more inherit yellow through `depends_on`. Known conflicts encoded both ways (decorations 3 vs 2 weeks, large-venue cancellation 3 vs 4 weeks, USG deadline anchor payment date vs event date, incomplete application 2 business days vs 48 hours, travel 9 weeks (guidelines) vs 8 weeks (USG FAQ document), vendors not on the list rejected (guidelines) vs allowed as "new vendors" (FAQ), officer trainings template vs recognition page).
- **Calendar** (`rules/calendar.json`): Fall 2026, Spring 2027, Summer 2027 from the Registrar's page; `unverified`.
- **Test sets** (`data/eval/`): 30 events (417 expected obligations), 20 budgets (30 planted violations), 10 constitutions (20 planted faults), 2 year plans; JSON Schemas in `data/eval/schemas/`; method in `data/eval/README.md`.
- **Scripts**: `validate_rules.py`, `run_eval.py` (+ `evaluators/` plug-in folder), `seed_demo.py` (+ `data/demo/club.json`), `fetch_sources.py`.
- **Frontend**: Vite + React 19 + TypeScript strict + Tailwind 4; start page calls `/health` and `/rules` and shows status and the open questions; `StatusBadge` (icon + text) and `SourceLink` shared components.
- **CI**: job-level `hashFiles()` removed (the cause of the zero-job failure); backend job runs `validate_rules.py`, `run_eval.py`, `pytest`, `pytest tests/adversarial`; frontend job runs `npm ci` and `npm run build` on Node 20.
- **Tests**: 144 passing (`pytest`), 0 adversarial yet.

## Iteration log

Add the newest entry at the top.

### Phase 0, iteration 1 — verify
Date/time: 2026-11-14, about 22:00-22:35 PT
Agent and model: verifier (fresh), Opus 5.5; fresh clone of aa143fa, followed the README
Report: docs/reviews/phase-0-iter-1-verify.md
Findings: 0/0/3/5 (all 8 criteria pass)
Fixed: M1 backend now started with `python -m app`, which reads BACKEND_PORT/BACKEND_HOST from the shell or .env like the Vite config; M2 relative SQLite paths resolve against backend/ so seed_demo.py and the app share one file; M3 usg-approved-vendor depends on usg-vendor-list, and food-approved-provider on a new unverified rule usc-approved-caterers (both now yellow); L1 CORS always allows the dev server on FRONTEND_PORT, FRONTEND_ORIGIN documented; L2 exact match no longer folds Unicode compatibility characters (NFC only), and every raw source download is committed with a test that re-derives each snapshot and checks its SHA-256; L3 the start page shows each rule's plain message, verification notes rewritten without file paths or planning references; L4 the phone number moved to usc-approved-caterers, which cites the TES FAQ where it appears; L5 README covers seeding, adversarial tests and the frontend build. Each has a regression test.
Also in this round: new unverified rule usc-business-days-definition (the business-day assumption), which every business-day deadline depends on; validate_rules.py checks it agrees with calendar.json. tes-decorations-prohibited is now kind banned and classroom-requests-week-4 kind blocked_period. A test now checks every expected event status follows from the rule's certainty, severity and kind.
Left open: none from this report.
Full test suite: pass (144)
Gate: not yet, because iterations 2 (break) and 3 (audit) have not run

```
### Phase <n>, iteration <m> — <verify | break | audit | F1 | F2 | F3>
Date/time:
Agent and model:
Report: docs/reviews/...
Findings: <blocker>/<high>/<medium>/<low>
Fixed: ...
Left open: ...
Full test suite: pass / fail
Gate: passed / not yet, because ...
```

## Open questions for humans

| Question | Asked | Answer (researched 2026-11-14 by the managing session; see `docs/research/open_questions.md`) | Status in the rules |
|---|---|---|---|
| USG funding deadlines table, and how academic weeks are counted across winter break | 2026-11-14 | Found. The "Funding Application Deadlines" Google Sheet needs a sign-in; transcribed by hand (`docs/research/manual_snapshots/usg-funding-deadlines-26-27.csv`, copied to `rules/sources/usg-funding-deadlines.txt` as a manual snapshot). Keyed by event week, a 6-week and a 9-week deadline, always a Wednesday; weeks with no deadline (winter recess, study days, finals, spring recess) get no USG funding. Look deadlines up; do not compute them. | `usg-academic-week-definition` unverified (code cannot check the transcription); academic-week deadlines yellow |
| Spring 2027 academic calendar: first day, breaks, study days, finals | 2026-11-14 | Official calendar (usc.edu/academic-calendar and academics.usc.edu/calendar, same dates): classes Jan 11 - Apr 30, holidays Jan 18 and Feb 15, spring recess Mar 14-21, study days May 1-4, exams May 5-12; winter recess Dec 17 - Jan 10. | `rules/calendar.json` matches the snapshot; still unverified until a person confirms (PLAN.md Phase 0) |
| Approved vendor and caterer lists | 2026-11-14 | USG Vendor List is public, two tabs (Food Vendors, Other Vendors), both snapshotted. INACTIVE / NOT FOUND / registration-state rows mean yellow. The list includes buses, balloon vendors and talent agencies, which are ineligible: vendor check and eligibility check stay separate. Purchasing's approved-caterer list is not public. | `usg-vendor-list` unverified |
| Is the cap four funded events per semester? | 2026-11-14 | Only in the USG Funding page FAQ; the 2026-27 guidelines and the USG FAQ document do not state it. | `usg-events-per-semester-cap` unverified, yellow, "confirm with usgfunds@usc.edu" |

## Decisions

Record any change of scope or departure from PROJECT_CONTEXT here, with the reason.

- **[F] sources re-read in full.** PROJECT_CONTEXT marks the TES FAQ, tabling and Campus Activities pages [F] (read through a summarising tool). Phase 0 snapshotted each page's full text, and every rule taken from them quotes the snapshot verbatim (checked by code), so those rules are `read`. Where the snapshot differs from the brief, the snapshot wins: e.g. the tabling page does not say "since Oct 12, 2026".
- **Open questions stay `unverified`** even where a source states the answer (the 4-events cap is on the USG web page; the calendar is on the Registrar's page): PLAN.md and the task brief require a person to confirm them first. Shown yellow.
- **Rule loading is all or nothing.** One malformed rule stops the whole table (with every problem listed) instead of being skipped, because a skipped rule is a silently missing obligation. `/health` answers 503 and check routes refuse with the reasons.
- **"Exact match"** = substring after NFKC normalisation and whitespace collapsing, with words split across PDF lines at a hyphen re-joined. Quotes keep the sources' own typos ("six academic weeks six academic weeks", "Restaurant diners", the PDF's "w ill").
- **USG deadline anchor conflict.** The guidelines count back from the initial payment due date; the USG web page from the event date. Encoded as a conflict pair; the earlier deadline applies.
- **TES "first 3 weeks" vs "after January 26".** Events through Jan 26, 2027 are blocked (the stated date); Jan 27–31 are yellow "confirm with Trojan Event Services".
- **Rule-object additions** beyond PROJECT_CONTEXT's example: `kind`, `title`, `source_section`, `verification_note`, `triggers`/`trigger_mode` (names from `rules/vocabulary.json`), `params`, `direction`, `depends_on`, `notes`. `applies_to` and `check` are plain-language descriptions, not code; checks read `params`.
- **No `green` severity on rules.** Green is a verdict on a checked item, never a property of a rule.
- **Event test-set scope**: events/outside-money rules of kind deadline, requirement, cap, banned, blocked_period, plus USG deadline/blocked/ineligible rules when funding is requested. USG document requirements belong to the money check (data/eval/README.md).
- **No database migrations** (hackathon): `init_db()` creates tables; delete the local SQLite file after a schema change.
- **Ports configurable** for parallel phases: `BACKEND_PORT`, `FRONTEND_PORT`, `API_PROXY_TARGET`, `VITE_API_BASE_URL` (CLAUDE.md). Backend routes have no `/api` prefix; the Vite proxy strips it.
- **Parallel-friendly layout**: routers and evaluators are discovered by file; pages are one line in `frontend/src/routes.tsx`.
- **`AI_MODE` default is `recorded`** (in code and `.env.example`) so nothing spends API money by accident.
- **USG deadlines differ from PROJECT_CONTEXT's assumption** (from the researched deadline table): deadlines are not a count of academic weeks; they are looked up by event week. For spring events before spring recess (Jan 11 - Mar 12, 2027) the 9-week travel deadline is November 11 or 18, 2026, in the previous semester, not January; for events after spring recess it is January 20 - February 24, 2027. PROJECT_CONTEXT section 11's line "the retreat's travel deadline ... lands in January" is therefore true only for a retreat after spring recess. The demo club's retreat (`data/demo/club.json`, year plan yp-01) is set to February 26-28, 2027, so the demo shows a travel deadline of November 18, 2026, in the previous semester. PROJECT_CONTEXT itself is not edited.
- **Three source disagreements on USG deadlines**, each encoded as a conflict pair with the stricter applied: the guidelines count back from the initial payment due date, the web page, FAQ document and table from the event (week); the FAQ document says 8 weeks for travel, the guidelines 9; the FAQ document allows "new vendors", the guidelines reject vendors not on the list.
- **Calendar stays `unverified`** although the managing session suggested `read`: PLAN.md Phase 0 says to mark it unverified "until a human confirms it", and the research was done by an AI session. To confirm, a person sets `verified` to `read` in both `rules/calendar.json` and rule `usc-academic-calendar-2026-27` (validate_rules.py checks they agree).
- **Research files from the managing session** (`docs/research/open_questions.md`, `docs/research/manual_snapshots/`) are committed with Phase 0 at its request and are part of the iteration 3 audit.
- **Calendar confirmation not applied (2026-11-14).** The managing session relayed that the user confirmed the calendar ("Calendar confirmed") and asked for it to be marked verified. The permission system blocked that change because the confirmation reached this session only through another session, so the calendar stays `unverified`. To apply it, the user confirms directly in this session (or sets `verified: "read"` in `rules/calendar.json` and in rule `usc-academic-calendar-2026-27` and runs `python scripts/validate_rules.py`). The business-day and academic-week assumptions and the 4-event cap stay unverified in any case.
- **Vendor and caterer checks are yellow until the lists are confirmed.** PROJECT_CONTEXT says to treat a vendor not on USG's list as red; the rule keeps severity red, but because it depends on the unverified list it is shown yellow until a person confirms the list.
- **Commit convention changed by the user (2026-11-14, confirmed directly in this session).** Small commits, one per logical piece and one per finding fixed; imperative, descriptive subjects with no `phase N` / `iter N` prefix (phases and iterations are tracked here). CLAUDE.md, PLAN.md (Bookkeeping, checkpoint step 4, Phase 7) and CONTRIBUTING.md updated. The three earlier local Phase 0 commits are reworded to match before the checkpoint push (contents unchanged). Push policy unchanged: only at a phase checkpoint, never force-push.
