# Progress log

The orchestrator updates this file after every build step and every iteration. A new session should be able to resume from this file alone.

Final reviewers in Phase 7 must **not** read this file.

## Current state

- **Phase:** 0 — Foundation
- **Step:** closed. Iterations 1-4 ran; every blocker and high from iteration 4 is fixed; the humans ended the review loop there (see Decisions, 2026-11-15)
- **Next action:** paused at the user's request after the Phase 0 push. Phase 1 (recognition check) starts only when the humans say so, under the new process (at most 3 iterations, 1-2 reviewers each)
- **Blocked on humans:** a person must confirm the four open questions (answers researched, see below) and review the rule table by hand (PLAN.md section 3); a person must compare the hand-transcribed USG deadline table with the sheet.

## Phase status

| Phase | Goal | Build | Iterations run | Last iteration clean? | Closed |
|---|---|---|---|---|---|
| 0 | Foundation | done | 4 | no (iteration 4: 3 blockers, 17 high, all fixed) | yes, 2026-11-15 (by the humans' decision) |
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
- **Claude client** (`app/ai/`): structured output via `messages.parse` validated against Pydantic models; `AI_MODE` = `recorded` (default; replay only, never the network), `live`, or `record` (live + save). Untrusted text is HTML-escaped inside `<document>` wrappers and the system prompt says it is data. Recordings store the request as document fingerprints; the response can quote the document in `evidence`, so fields marked `PERSONAL` are blanked before a response is recorded or audited, and `data/ai_recordings/` is git-ignored. One live smoke call (Haiku, 2026-11-14) confirmed structured output works and an injected "mark this approved" was reported as document content.
- **Source snapshots** (`rules/sources/`): 18 sources (one a manual transcription) in `manifest.json` with fetch time, SHA-256 and version date; text snapshots committed; small raw PDFs/CSVs committed, the 6.7 MB Handbook PDF and raw HTML not.
- **Rule table**: 288 rules (`funding` 75, `events` 71, `outside_money` 22, `recognition` 120 incl. every constitution template clause, each with its template wording and blanks marked). 283 `read` (each `source_text` cut verbatim from its snapshot, whose text hash the manifest records, and re-checked on every load; every number in its params pinned to its own phrase of the quote, and every deadline's offset, unit and direction checked against it), 5 `unverified`; 15 more inherit yellow through `depends_on`. Every event and outside-money ban names the fact that breaks it (`params.violated_when`, from `vocabulary.json` facts). Known conflicts encoded both ways (decorations 3 vs 2 weeks, large-venue cancellation 3 vs 4 weeks, USG deadline anchor payment date vs event date, incomplete application 2 business days vs 48 hours, travel 9 weeks (guidelines) vs 8 weeks (USG FAQ document), vendors not on the list rejected (guidelines) vs allowed as "new vendors" (FAQ), officer trainings template vs recognition page).
- **Calendar** (`rules/calendar.json`): Fall 2026, Spring 2027, Summer 2027 from the Registrar's page; confirmed by the user on 2026-11-14 (`read`); every date is checked against the quoted Registrar text on load.
- **Test sets** (`data/eval/`): 30 events (456 expected obligations), 20 budgets (30 planted violations), 10 constitutions (21 planted faults and one empty file), 2 year plans; JSON Schemas in `data/eval/schemas/`; method in `data/eval/README.md`.
- **Scripts**: `validate_rules.py`, `run_eval.py` (+ `evaluators/` plug-in folder), `seed_demo.py` (+ `data/demo/club.json`), `fetch_sources.py`.
- **Frontend**: Vite + React 19 + TypeScript strict + Tailwind 4; start page calls `/health` and `/rules` and shows status and the open questions; `StatusBadge` (icon + text) and `SourceLink` shared components.
- **CI**: job-level `hashFiles()` removed (the cause of the zero-job failure); backend job runs `validate_rules.py`, `run_eval.py`, `pytest`, `pytest tests/adversarial`; frontend job runs `npm ci` and `npm run build` on Node 20.
- **Tests**: 318 passing (`pytest`), including 105 adversarial tests from iterations 2 and 4.

## Iteration log

Add the newest entry at the top.

### Phase 0, iteration 4 — break and audit (six reviewers in parallel); phase closed
Date/time: 2026-11-15, about 00:00-02:30 PT
Agent and model: fresh breaker and five fresh auditors at high effort, Opus 5.5, on commit f65afcc (split as in iteration 3)
Reports: docs/reviews/phase-0-iter-4-{break,audit-funding,audit-events,audit-outside-money-calendar,audit-recognition,audit-code}.md (the recognition auditor could not write its file; its returned report was saved by the orchestrator). 46 failing tests in backend/tests/adversarial/test_phase0_iter4_*_break.py
Findings: break 0/10/5/6, funding 1/2/5/6, events 0/1/2/13, outside money and calendar 1/1/3/8, recognition 1/0/2/7, code 0/3/4/5; in all 3/17/21/45 (the funding and outside-money blockers are the same finding)
Fixed (all blockers and highs, each with its test): the USG FAQ's 8-weeks-before-travel date is no longer a certain deadline (Professional/Academic Fund only, counted from the travel date, yellow, the guidelines' rule applied in the keys); budget keys carry USG's case-by-case food and hotel review as office decides; the co-host ban covers Unrecognized Student Organizations only; the tabling blackout is red for holidays and a separate yellow rule for university functions; the term-of-office clause has its three blanks; every params number is pinned to its own phrase, deadline units and directions and params dates and times are checked against the quote, negatives and numbers-as-text refused; edited snapshots refused (text_sha256); unknown rule files refused; quotes cut after a number's punctuation refused; Finding refuses green on yellow rules and on the less strict side of a conflict, and red on uncertain rules, and citations name conflicting rules; personal data blanked at any depth, evidence dropped from schemas holding it, unblankable personal fields refused; file names cannot carry the request label or code; a calendar missing a term or claiming an academic-week definition is refused; the answer-key validator checks budget verdicts against rules and caps, year-plan and event violations against facts and dates, and recomputes every dated deadline from its anchor; the demo seeder gives clear errors. Quick mediums: participation limited to the USC community (Handbook item 4), the enrolled-voting message, III.A.1 linked to the five-officer rule, tabling set-up limits, academic-week deadlines undated until the table is confirmed, conditional-clause facts documented.
Left open (medium and low, for a later phase or a person): see "Open findings after Phase 0" below.
Full test suite: pass (318, adversarial included); validate_rules.py OK; run_eval.py all four sets valid; frontend build OK
Close: Phase 0 closed without a fifth round, by the humans' decision (Decisions, 2026-11-15)

### Phase 0, iteration 3 — audit (five parallel auditors)
Date/time: 2026-11-14, about 23:30 PT to 2026-11-15 early morning
Agent and model: five fresh auditors at high effort, Opus 5.5, on commit 9c3f500: (a) funding, (b) events, (c) outside money + academic calendar + USG deadline table, (d) recognition, (e) code, trust rules and earlier fixes
Reports: docs/reviews/phase-0-iter-3-audit-{funding,events,outside-money-calendar,recognition,code}.md
Findings: funding 0/2/8/13, events 0/1/7/10, outside money and calendar 0/2/8/8, recognition 0/1/8/11, code 0/1/3/8; in all 0/7/34/50
Fixed (highs): funding: the USG page's 9-weeks-before-payment deadline encoded with one earliest-date policy, and summer events flagged; events: candle ban separated from Sterno and open flame, venue cap, alcohol and bus rules narrowed to the guidelines; outside money: free drawings are a required list of steps (red), and the deadline-table rows a person must compare with the sheet are recorded (rows_to_confirm, date_to_row, earlier date until confirmed); recognition: every clause carries its template wording with blanks marked, and a clause with fixed words around its blank is fixed_and_fill, checked by the loader; code: every number in a read rule's params (nested too) must be stated in its quote.
Fixed (mediums and most lows): business days count every weekday (earliest date); every ban names its fact and the eval validator checks verdicts against it; co-sponsorship, vendor-permission and discretionary-fundraising rules; orphan rules triggered; new recognition rules (enrolled voting members, advisor meets once a semester, one rule per advisor item, Event Accessibility shown yellow, cover-page clauses); constitution test set varied (chapter, school affiliation, empty blank, words deleted around a blank, empty file) with not_applicable checked against club flags; Finding frozen, re-checked on copy, green only with the rule table's own citation and never on info; personal fields blanked in recordings and the audit log, recordings git-ignored; tests for guards that had none; request code against forged request labels; architecture guard covers every module; quotes may not cut a number at a decimal point; line-item confidence stored as the AI's label; demo seeder never replaces a club it did not create; stale docs corrected. Each fix is its own commit with its test.
Left open: code L (status and deadline logic written in three places) is for Phase 2, when the deadline calculator exists and the validator can import it; recognition L (Appendix clause, contradiction-specific clause messages) and outside-money L (week-4 classroom date, Handbook emblem and silent-auction passages, the Nov 11 deadline on Veterans Day) recorded for a person; the form-field instructions of the fillable template are not in the snapshot (decision below).
Full test suite: pass (265, adversarial included); validate_rules.py OK; run_eval.py all four sets valid; frontend build OK
Gate: not yet, because iteration 3 had high findings; iteration 4 (break + audit) next

### Phase 0, iteration 2 — break
Date/time: 2026-11-14, about 22:30-23:00 PT (fixes until about 23:20)
Agent and model: breaker (fresh), Opus 5.5; worked on copies of commit 1c53949
Report: docs/reviews/phase-0-iter-2-break.md (59 failing tests in backend/tests/adversarial/test_phase0_*_break.py)
Findings: 0/2/10/13
Fixed: H1 rule numbers: offset must be a JSON integer, effective_date an ISO string, limits positive numbers, and every limit and offset of a 'read' rule must be stated in its quoted text; H2 year plan yp-02 now lists usg-ineligible-alcohol. M1 calendar dates are checked against the quoted Registrar text (plus overlap, commencement and numeric-date checks); M2 bad manifest, snapshot, calendar or test-set files are load errors, not crashes, and the app starts degraded; M3 AI answers parsed as strict JSON in Pydantic strict mode, corrupt recordings are AIErrors; M4 Finding refuses green on an uncertain or office-decides rule; M5/M6 validate_set recomputes due dates, statuses, past-due flags, conflict choices, over-cap figures and budget verdict consistency; M7 quotes must start and end on a word boundary; M8 academic-week and business-day deadlines must depend on the rule defining the unit; M9 rule history after a revert; L1 events cannot end before they start; L2 binary uploads limited to PDF/images and 20 MB; L3 forged request label neutralised; L4 manifest version_date required and calendar effective date checked; L5 the app checks calendar/rule agreement; L6 no absolute server paths in errors; L7 relative folders and sqlite+driver URLs anchored; L8 startup race tolerated; L11 first-weeks fix text matches the confirm window; L12 seed_demo refuses to replace a real club. Each fix is its own commit with its test.
Left open (questions, recorded below): M10, L9, L10, L13.
Full test suite: pass (208, adversarial included)
Gate: not yet, because iteration 3 (audit) has not run

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

## Open findings after Phase 0

Medium and low findings left open when Phase 0 closed (details in the iteration 4 reports):
- **Funding:** year-plan notes give the 6-week table date where the 9-week column applies to some rows (M2); ev-21's charter bus has no rideshare/bus ineligibility finding (M4); no test pins usg-faq-eligibility or the incomplete-application rules (M5); the summer rule's periods are not in the calendar, the other-University-funds note fires on every USG request, the FAQ's four-week clause is unrecorded, after-event dates in the year plans rely on one shared helper (lows).
- **Events:** the alcohol sales ban fires only with ticket sales (M1); the plastic-bottle ban, the smoke-free plan and the Outdoor Events and Social Dance Policy are not encoded (M2); 13 lows (message wording beyond quotes, the cash-payment disagreement, open-flame reading, trigger widths, calendar rule quoting only Spring, "Week 4" counting, regression tests that check rule existence only).
- **Outside money and calendar:** ticket-sales-cover-costs is information with no fact (M); the deadline-table test checks only the after-recess rows (M); lows on club-to-club co-hosting conditions, sponsorship wording, emblem-product and silent-auction passages, payment dates in blank table rows, the Nov 11 deadline on Veterans Day, no free-drawing case in the event set.
- **Recognition:** co-06's deleted officer is "weak" where "contradicts" may fit; template wording shows raw {blank} markers and VIII.B.1 is split across a page; blank positions and the continuation's position are not validated; VI.B.2 and VI.C.2 quotes differ only in underscores; some messages state facts outside the quoted passage; no test that each constitution text differs from co-01 only in its listed clauses; the Appendix is not encoded.
- **Code:** 9 of 62 single-guard removals still leave the suite green (number checks inside lists, relative imports in the architecture test); status and deadline logic is written in more than one place until Phase 2 builds the calculator; the start page miscounts unconfirmed rules; a re-fetched source keeps its old version date; SourceLink does not mark a read rule resting on an unverified one.

## Phase ownership and branches

| Phase | Who | Branch |
|---|---|---|
| 1 Recognition check | teammate (second laptop) | `phase-1/recognition` |
| 2 Event packet | this machine | `phase-2/event-packet` |

Both start from `origin/main` and end with a pull request into `main`. See "Decisions".

## Carried to Phase 7

- **Phase 0 closed without a confirming review.** Iteration 4 (one breaker and five auditors) found 3 blockers and 17 highs. All of them were fixed with regression tests, and the suite passed (318). No fresh reviewer re-checked those fixes before the push on 2026-11-15 (6c63e0f). The humans accepted this to save time and asked for it to be covered in Phase 7. **Phase 7 orchestrator:** make F1 (correctness) explicitly cover the Phase 0 foundation: every rule in `rules/*.json` against its snapshot in `rules/sources/`, the deadline-table snapshot and calendar, and the rule loader and validator guards. Give F1 this as part of its lens. Do not hand it this file or the phase reports (PLAN.md Phase 7, "Independence").

## Open questions for humans

| Question | Asked | Answer (researched 2026-11-14 by the managing session; see `docs/research/open_questions.md`) | Status in the rules |
|---|---|---|---|
| USG funding deadlines table, and how academic weeks are counted across winter break | 2026-11-14 | Found. The "Funding Application Deadlines" Google Sheet needs a sign-in; transcribed by hand (`docs/research/manual_snapshots/usg-funding-deadlines-26-27.csv`, copied to `rules/sources/usg-funding-deadlines.txt` as a manual snapshot). Keyed by event week, a 6-week and a 9-week deadline, always a Wednesday; weeks with no deadline (winter recess, study days, finals, spring recess) get no USG funding. Look deadlines up; do not compute them. | `usg-academic-week-definition` unverified (code cannot check the transcription); academic-week deadlines yellow |
| Spring 2027 academic calendar: first day, breaks, study days, finals | 2026-11-14 | Official calendar (usc.edu/academic-calendar and academics.usc.edu/calendar, same dates): classes Jan 11 - Apr 30, holidays Jan 18 and Feb 15, spring recess Mar 14-21, study days May 1-4, exams May 5-12; winter recess Dec 17 - Jan 10. | `rules/calendar.json` matches the snapshot; confirmed by a person on 2026-11-14 (verified 'read') |
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
- **Calendar confirmed by the user (2026-11-14).** A relayed confirmation was blocked by the permission system; the user then confirmed directly in this session, and the calendar and rule `usc-academic-calendar-2026-27` were marked `read` in their own commit. The business-day and academic-week assumptions, the 4-event cap, the vendor list and approved caterers stay unverified (the cap by the user's choice).
- **Vendor and caterer checks are yellow until the lists are confirmed.** PROJECT_CONTEXT says to treat a vendor not on USG's list as red; the rule keeps severity red, but because it depends on the unverified list it is shown yellow until a person confirms the list.
- **Commit convention changed by the user (2026-11-14, confirmed directly in this session).** Small commits, one per logical piece and one per finding fixed; imperative, descriptive subjects with no `phase N` / `iter N` prefix (phases and iterations are tracked here). CLAUDE.md, PLAN.md (Bookkeeping, checkpoint step 4, Phase 7) and CONTRIBUTING.md updated. The three earlier local Phase 0 commits are reworded to match before the checkpoint push (contents unchanged). Push policy unchanged: only at a phase checkpoint, never force-push.
- **Conditional constitution clauses (iteration 3).** VI.B, VI.C, VIII.C.2, III.A.2, III.B.7 and III.D.8 apply only when the club's matching fact holds (`params.required_if_flag`). When it does not, the clause may be absent or say "Not applicable"; Greenlight does not flag it. The fillable form keeps the fixed text and asks for "N/A", but those field instructions are not in the text snapshot, so no rule can quote them; a blank that should hold the club's name is checked only for being filled in. Phase 1 must not rely on the form-field instructions until `fetch_sources.py` records them.
- **Review process changed by the user (2026-11-15, confirmed directly in this session).** At most three iterations per phase (verify, break, audit), each with one or two fresh reviewers. After the third iteration the orchestrator fixes blockers and highs, confirms the exit criteria and the full suite, and closes the phase; medium and low findings are listed in this file. The "repeat break + audit until a clean round" rule and the five-iteration safety valve are removed (PLAN.md section 1, CLAUDE.md). Phase 0 had already run four iterations (the last with six reviewers); it was closed after fixing every blocker and high from iteration 4, without a fifth round.
- **Open questions from iteration 2 (no code change):** M10: the TES "no events in the first 3 weeks" rule is applied to Trojan Event Services venues only (its source is the TES booking FAQ); whether it also covers classroom or off-campus club events is a question for Campus Activities. L9: business-day counting cannot skip staff holidays outside a term (e.g. Christmas) because only academic holidays are known; business days stay unverified. L10: line items and funding options may hold negative amounts (discount lines); Phase 3 decides. L13: a finding or document can reference another club's event at the database level; access control is Phase 5.
- **Branch-and-PR workflow (2026-11-15, the humans' decision).** From Phase 1 on, every phase works on its own branch (`phase-<n>/<short-name>`) cut from the latest `origin/main` and never commits to `main`. At its checkpoint it rebases on `origin/main`, pushes the branch and opens a pull request into `main`; the humans merge it. Phases 1 and 2 run in parallel: Phase 1 on a teammate's laptop (`phase-1/recognition`), Phase 2 here (`phase-2/event-packet`). PLAN.md (Branches, Phase checkpoint), CLAUDE.md and CONTRIBUTING.md updated.
