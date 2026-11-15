# Progress log

The orchestrator updates this file after every build step and every iteration. A new session should be able to resume from this file alone.

Final reviewers in Phase 7 must **not** read this file.

## Current state

- **Phase:** 0 — Foundation
- **Step:** build done; iteration 1 (verify) next
- **Next action:** run iteration 1 with a fresh `verifier` sub-agent (PLAN.md section 1)
- **Blocked on humans:** the four open questions (PROJECT_CONTEXT section 8) still need a person to confirm them; a person must review the rule table by hand (PLAN.md section 3). An API key is now in `.env` (added by a human on 2026-11-14); nothing in Phase 0 needs it.

## Phase status

| Phase | Goal | Build | Iterations run | Last iteration clean? | Gate |
|---|---|---|---|---|---|
| 0 | Foundation | done | 0 | — | open |
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
- **Source snapshots** (`rules/sources/`): 17 sources in `manifest.json` with fetch time, SHA-256 and version date; text snapshots committed; small raw PDFs/CSVs committed, the 6.7 MB Handbook PDF and raw HTML not.
- **Rule table**: 256 rules (`funding` 68, `events` 59, `outside_money` 19, `recognition` 110 incl. every constitution template clause). 252 `read` (each `source_text` cut verbatim from its snapshot and re-checked on every load), 4 `unverified`; 10 more inherit yellow through `depends_on`. Known conflicts encoded both ways (decorations 3 vs 2 weeks, large-venue cancellation 3 vs 4 weeks, USG deadline anchor payment date vs event date, incomplete application 2 business days vs 48 hours, officer trainings template vs recognition page).
- **Calendar** (`rules/calendar.json`): Fall 2026, Spring 2027, Summer 2027 from the Registrar's page; `unverified`.
- **Test sets** (`data/eval/`): 30 events (415 expected obligations), 20 budgets (30 planted violations), 10 constitutions (20 planted faults), 2 year plans; JSON Schemas in `data/eval/schemas/`; method in `data/eval/README.md`.
- **Scripts**: `validate_rules.py`, `run_eval.py` (+ `evaluators/` plug-in folder), `seed_demo.py` (+ `data/demo/club.json`), `fetch_sources.py`.
- **Frontend**: Vite + React 19 + TypeScript strict + Tailwind 4; start page calls `/health` and `/rules` and shows status and the open questions; `StatusBadge` (icon + text) and `SourceLink` shared components.
- **CI**: job-level `hashFiles()` removed (the cause of the zero-job failure); backend job runs `validate_rules.py`, `run_eval.py`, `pytest`, `pytest tests/adversarial`; frontend job runs `npm ci` and `npm run build` on Node 20.
- **Tests**: 120 passing (`pytest`), 0 adversarial yet.

## Iteration log

Add the newest entry at the top.

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

| Question | Asked | Answer |
|---|---|---|
| USG funding deadlines table, and how academic weeks are counted across winter break | 2026-11-14 | Partly: another session transcribed the sign-in-only table by hand (`rules/sources/usg-funding-deadlines.txt`). A person must compare it with the sheet before it is trusted; until then academic-week deadlines stay yellow. |
| Spring 2027 academic calendar: first day, breaks, study days, finals | 2026-11-14 | Read from the Registrar's public page into `rules/calendar.json`; PLAN.md requires a person to confirm it. |
| Approved vendor and caterer lists | 2026-11-14 | USG Vendor List snapshotted (both tabs). Purchasing's approved-caterer list is not public (phone only). |
| Is the cap four funded events per semester? | 2026-11-14 | The USG web page FAQ says so; the guidelines do not. Encoded `unverified` (yellow) until USG confirms. |

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
- **Year plan yp-01**: the retreat's travel deadline is not flagged as "previous semester"; counted back nine weeks it is about January 20–22, 2027 (the transcribed table says January 20), inside the spring semester.
