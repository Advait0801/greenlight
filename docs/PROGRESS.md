# Progress log

The orchestrator updates this file after every build step and every iteration. A new session should be able to resume from this file alone.

Final reviewers in Phase 7 must **not** read this file.

## Current state

- **Phase 3 (money check):** closed 2026-11-15 after three iterations; pushed to `main`. Phase 4 (year plan) can start.
- **Phase 3 (branch `phase-3/money-check`):** built 2026-11-15; review iterations under way (see Iteration log).
- **Phase 0:** closed 2026-11-15 (Foundation).
- **Phase 2:** closed 2026-11-15 after three iterations; merged into `main` (pull request from `phase-2/event-packet`).
- **Phase 1:** closed 2026-11-15 after three iterations; pull request from `phase-1/recognition` into `main` for the humans to merge.
- **Next action:** the humans merge the Phase 1 pull request; Phase 3 (money check) can start once Phase 2 is on `main` (it is).
- **Blocked on humans:** a person must confirm the four open questions (answers researched, see below) and review the rule table by hand (PLAN.md section 3); a person must compare the hand-transcribed USG deadline table with the sheet.

## Phase status

| Phase | Goal | Build | Iterations run | Last iteration clean? | Closed |
|---|---|---|---|---|---|
| 0 | Foundation | done | 4 | no (iteration 4: 3 blockers, 17 high, all fixed) | yes, 2026-11-15 (by the humans' decision) |
| 1 | Recognition check | done | 3 | no (iteration 3: 0 blockers, 2 high, both fixed) | yes, 2026-11-15 (pull request from `phase-1/recognition`) |
| 2 | Event packet | done (branch `phase-2/event-packet`) | 3 | no (iteration 3: 0 blockers, 1 high, fixed) | yes, 2026-11-15 (pull request into main) |
| 3 | Money check | done (branch `phase-3/money-check`) | 3 | no (iteration 3: 0 blockers, 1 high, fixed) | yes, 2026-11-15 (pushed to main) |
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

## Phase 2 build (2026-11-15, branch `phase-2/event-packet`)

What exists now:
- **Deadline calculator** (`backend/app/services/deadlines.py`): days, weeks, months (same day or the month's last day), business days (every weekday, earliest date); hours and academic weeks give no date (rule usg-academic-week-definition says no date until a person confirms USG's table). Earliest event date that meets a passed deadline; which of two disagreeing deadlines is stricter. `app/eval_sets.py` now uses it, so date logic lives in one place (closes the Phase 0 code-audit low).
- **Rule engine** (`backend/app/services/rule_engine.py`, `app/schemas/events.py`): event facts -> packet. Selects rules by trigger (scope as in data/eval/README.md); status from certainty, severity and kind; date checks (first three weeks, study days and finals, alcohol weekdays, USG breaks and summer, tabling days, classroom week 4) from the calendar; conflicts with both citations and the stricter applied; hard blocks (date passed, blocked items, passed deadlines); fallbacks (earliest date, change of format, other funding); questions. Unsure details ("possible") add yellow items and never remove one. Green only for date checks passed on certain rules, through `finding_for`.
- **Reading step** (`backend/app/services/event_intake.py`): the model reports date parts, venue, headcount and details with confidence; code builds the date and checks a stated weekday; unsure values become questions. 30 recorded readings in `data/ai_recordings/event_sentence/` (synthetic test sentences, force-added).
- **API** (`backend/app/api/events.py`): `POST /events/parse`, `POST /events/packet`, `POST /events/packet.ics`, `GET /events/vocabulary`.
- **Frontend**: `/events/packet` page (sentence -> check the details -> packet with hard blocks, questions, sources disagree, timeline, grouped checklist with rule text and source, .ics download).
- **Evaluator** (`scripts/evaluators/events.py`): end to end on recorded readings 30/30 obligation lists match, 0 missed, 0 wrongly flagged; engine on the test set's attributes 30/30 with every due date, past-due flag and conflict; one deliberate status difference (ev-28: with no date, every date check is "check with the office", not "rule to keep").
- **Shared code changed** (backward compatible): `app/eval_sets.py` (`_back`/`_forward` call the calculator), `tests/unit/test_architecture.py` (`event_intake.py` allowed to use the AI client), `frontend/src/routes.tsx` (one entry).
- **Tests**: 386 passing.

## Phase 1 build (2026-11-15)

Branch `phase-1/recognition`. What exists now:
- **Reading uploads** (`backend/app/services/recognition_document.py`): pasted text, TXT (UTF-8/UTF-16), DOCX (python-docx), PDF (pypdf; the real template, flagged encrypted with an empty password, opens; typed form-field answers are placed on the page by position). A PDF with no text layer or an image goes to the AI reader for transcription. Empty, too short, damaged, password-protected, `.doc` and mislabelled files give a clear message and no verdict.
- **Clause check** (`recognition_check.py`, pure code): every `clause` rule in `rules/recognition.json` is located by Article, Section and Part (renumbered parts and one-paragraph pastes handled; page headers, the table of contents and the appendix ignored) and compared letter for letter with the template's fixed words around each blank. States: present, missing (absent, blank empty, a placeholder such as N/A or TBD, or "not applicable" on a required clause), weak (fixed words changed, with the missing and added words named), contradicts, needs a human look, not applicable (only when the officer says the club fact is false; unknown counts as required). Text outside the template is listed for the officer. Notes for another year's template, a fragment, instruction-like text, a non-fillable PDF and transcribed scans. Advisor meetings below the minimum are counted in code. Green only through `finding_for`, so clause III.B.1 (sources disagree on trainings) is yellow.
- **AI reader** (`recognition_intake.py`): fixed yes/no questions built from the rule table ("does this wording require an interview / dues / another membership…") about the membership blanks; the document is an `UntrustedDocument` under a fixed name. A "yes" is a conflict only when confident and its quoted evidence is in the document; anything else is yellow; a confident "no" is overruled to yellow by warning words (GPA, interview, dues…). The reader can never make a clause present. Off or failing reader means yellow. Transcription of scans: nothing from it is ever green. Recordings for the 9 synthetic test constitutions committed in `data/ai_recordings/constitution-answers/` (read by a person first, as `.gitignore` asks).
- **Readiness tracker** (`recognition_readiness.py`): 5 officers × (named + 3 documents), member minimum (5 more, 10 in all), advisor items due Dec 1, documents, key dates and days left from the rules; rules shown yellow (Clery course, Event Accessibility, EngageSC acceptance) are never ticked green. Nothing stored server-side.
- **Routes** (`backend/app/api/recognition.py`): `POST /constitution/check` (file or text, four optional yes/no club facts), `GET`/`POST /recognition/readiness`. AI outputs go to the audit log.
- **Page** (`frontend/src/pages/Recognition*.tsx`, route `/recognition`): upload or paste, club questions with "Not sure", report grouped by article with icon and text badges, template wording and source on every clause, readiness checklist (ticks saved in the browser only).
- **Evaluator** (`scripts/evaluators/constitutions.py`): 21/21 planted faults found, 0 missed, 0 wrongly flagged; one found with a different state (co-09 VIII.A.2 shown "wording changed", key says "contradicts").
- **Tests**: 421 passing (103 new). Shared change: `tests/unit/test_architecture.py` allows `app/services/recognition_intake.py` to import the AI client.
- Known limit: II.C.5 (dues) stays yellow on every constitution because the reader answers "no" only at medium confidence.

## Phase 3 build (2026-11-15, branch `phase-3/money-check`)

What exists now:
- **Engine** (`backend/app/services/money_check.py`, `app/schemas/money.py`): budget lines + event + club figures + attachments -> red, yellow, office-decides or green per line; findings about the application; fund; totals; whether a draft may be written. Pure code, whole cents. Limits come from rule params (food $35 per person over all food lines on expected attendance, hotel $400 per room-night, on-campus venue and personnel $4,000 on the sum, $8,000 a year with what was received, over $4,000 and multi-day office decides, 4 events a semester yellow). Ineligible categories red with a computed fix; ticketed, closed on-campus, private residence and international events red; required documents (ESR, food forms, travel and hotel documents) red when missing; quote, cart screenshot and Amazon wish list per line. Unsure or unknown category, a line that does not add up, a duplicate line, a quote total that differs from the budget, another currency, an unreadable document: yellow with the reason. Unknown ticketing or openness is asked, never assumed. Green only through `finding_for` on certain rules. USG deadlines and blocked dates come from the Phase 2 engine (`build_packet`), not recomputed.
- **Vendor check** (`app/services/vendor_list.py`): the vendor name against both vendor-list snapshots; always yellow while the list is unconfirmed, shown apart from eligibility (a listed DJ is still red).
- **Fund**: the officer's choice, or the model's reading when it is sure and names one fund; anything else yellow with the candidates. Fund-specific rules: Professional fund must be free and open (red), PO vendor for arts production lines and the Philanthropy service rule (yellow, cannot be checked).
- **Reading steps** (AI, `quote_intake.py`, `fund_reading.py`): the model copies amounts as written; code parses them to cents, refuses other currencies, negatives and ambiguous formats, checks numbers are written in a text document, computes a missing amount from quantity x unit price, adds up lines and compares with the stated total. Injected instructions are flagged and ignored.
- **Draft** (`application_draft.py`): refused while any red remains (the route re-runs the check); the model writes four prose paragraphs with no figures, code drops any paragraph containing a number not in the officer's own text; every figure (budget table, totals, attendance, date) is written by code. The officer edits and approves; the approval is logged as a fingerprint. Nothing is submitted.
- **API** (`app/api/money.py`): `GET /money/vocabulary`, `POST /money/read` (multipart; file type from its bytes), `POST /money/fund`, `POST /money/check`, `POST /money/draft`, `POST /money/draft/approve`.
- **Frontend**: `/money/check` page (upload, event, editable budget lines, attachments, fund, report with sources, draft and approval); demo budget button.
- **Evaluator** (`scripts/evaluators/budgets.py`): end to end on recorded readings: seeded violations caught 30/30, wrong greens 0, fund matches or yellow 20/20, totals exact 20/20, draft allowed right 20/20. 40 recordings in `data/ai_recordings/{quote_reading,fund_reading}/` (synthetic test data, force-added).
- **Rule added**: `usg-ineligible-expenses-list` (funding.json; yellow; quotes the guidelines' ineligible list) for lines whose category is unclear.
- **Shared code changed** (additive): `tests/unit/test_architecture.py` (three Phase 3 AI modules allowed), `frontend/src/routes.tsx` (one entry). No change to the rule loader, Finding, AI client, models, rule engine or deadline calculator.
- **Tests**: 507 passing (adversarial included).

## Iteration log

Add the newest entry at the top.

### Phase 3, iteration 3 — audit; phase closed
Date/time: 2026-11-15
Agent and model: auditor (fresh), Opus 5.5, medium effort, on commit 5b1f33f
Report: docs/reviews/phase-3-iter-3-audit.md
Findings: 0/1/5/7 (every funding rule the money check uses matches its snapshot in number, unit and anchor; no prompt asks for arithmetic, a date, a cap comparison or a verdict; every earlier fix holds)
Fixed: H1 the page started the club's USG money received and funded-events count at 0, so the $8,000 cap showed green for an unknown club; both now start empty and the check asks (regression test tests/unit/test_money_page_defaults.py reads the page's initial state, as the frontend has no test runner). Also M: a quote that contains instructions has no sure categories (test in tests/unit/test_money_reading.py).
Left open: see "Open findings after Phase 3".
Full test suite: pass (525, adversarial included); validate_rules.py OK; run_eval budgets 30/0/0 (fund 20/20, totals 20/20, draft 20/20), events 30/456/0/0; frontend build OK
Close: Phase 3 closed after iteration 3 (PLAN.md section 1); no further review round

### Phase 3, iteration 2 — break
Date/time: 2026-11-15
Agent and model: breaker (fresh), Opus 5.5, medium effort, on commit 9440d6e
Report: docs/reviews/phase-3-iter-2-break.md (14 failing test cases in backend/tests/adversarial/test_phase3_iter2_money_break.py)
Findings: 2/1/5/1
Fixed (all covered by the breaker's tests): B1 quotes in other currencies written as words ("pounds sterling", "euros", "Canadian dollars") or with prefixed dollar signs (C$, CA$, HK$) are no longer read as US dollars; B2 "$.50" is fifty cents, not fifty dollars; H1 /money/draft always checks as of today, so a back-dated as_of cannot unblock a draft; M an uploaded document linked to no line is yellow; M a hotel quantity that is not rooms x nights is yellow and not passed; M an on-campus venue or staffing line on an off-campus event is yellow; M a fund reading that found instructions is unsure (yellow); M drafted paragraphs with figures written in words are replaced; L the fallback no longer says "Fund fund".
Left open (questions for a person): do mandatory per-night hotel fees count toward the $400 cap; do catering delivery or service fees count toward the $35 per person.
Full test suite: pass (523, adversarial included); run_eval budgets 30/0/0, events 30/456/0/0
Gate: iteration 3 (audit) next

### Phase 3, iteration 1 — verify
Date/time: 2026-11-15
Agent and model: verifier (fresh), Opus 5.5, medium effort, on commit 434a330
Report: docs/reviews/phase-3-iter-1-verify.md
Findings: 0/2/3/4 (6 of 8 exit criteria pass; the two failures were on budgets outside the test set; test set 30/30 caught, 0 wrong greens, fund 20/20)
Fixed: H1 security staffing now counts toward the $4,000 venue and personnel cap (rule params and triggers; it was shown green); H2 a food fix no longer shows a rounded per-person figure ("more than $35.00"). Each with a regression test in tests/unit/test_money_check.py.
Left open: M a certainly passed USG deadline is yellow (from the Phase 2 engine; the draft is still blocked); M the vendor-list note does not change a line's verdict (by design: kept apart from eligibility, always yellow); M the test set does not measure reading line items from uploads (no PDF or image recordings); L instructions in a quote leave its lines marked sure; L unsure food lines are left out of food per person; L an unknown funded-events count gives a question but no finding; L "plan for at least N people" may invite overstating attendance.
Full test suite: pass (509, adversarial included); run_eval budgets 30/0/0, events 30/456/0/0
Gate: iteration 2 (break) next

### Phase 2, after closing — five open mediums fixed at the humans' request
Date/time: 2026-11-15, about 02:10-02:30 PT
Fixed (each with a regression test; no fresh reviewer has seen these, so Phase 7 F1 covers them): audit M6 the LAFD fire permit follows the tent size the officer enters (over 450 sq ft or unknown: listed with a note; 450 or less with no open flame: not listed); audit M8 / verify M3 office-decides approvals with no lead time of their own show the date every approval must be in place (rule approvals-two-weeks, cited), on the page and in the .ics; audit M1 the rule not applied in a source conflict is marked "not applied" and left out of the timeline, the .ics and the hard blocks; audit M4 / verify L2 "move the event" suggestions skip breaks, holidays, study days, finals and the spring 2027 start block, and name the passed USG deadlines a new date cannot settle; audit M5 the year, month, day and headcount the model reports must be written in the sentence, or the officer is asked.
Full test suite: pass (432, adversarial included); run_eval.py events 30/456/0/0; frontend build OK

### Phase 2, iteration 3 — audit; phase closed
Date/time: 2026-11-15, about 01:35-01:50 PT
Agent and model: auditor (fresh), Opus 5.5, medium effort, on commit cf5b22e
Report: docs/reviews/phase-2-iter-3-audit.md
Findings: 0/1/8/9 (every date-producing rule matches its snapshot in number, unit and anchor; earlier fixes hold)
Fixed: H1 a summer date was green on "no USG funding during breaks"; dates outside the fall and spring semesters are now "check with the office" (regression test in tests/unit/test_rule_engine.py).
Left open: see "Open findings after Phase 2".
Full test suite: pass (413, adversarial included); validate_rules.py OK; run_eval.py events 30/456/0/0; frontend build OK
Close: Phase 2 closed after iteration 3 (PLAN.md section 1); no further review round

### Phase 2, iteration 2 — break
Date/time: 2026-11-15, about 01:10-01:30 PT
Agent and model: breaker (fresh), Opus 5.5, medium effort, on commit 62bc37d
Report: docs/reviews/phase-2-iter-2-break.md (23 failing tests in backend/tests/adversarial/test_phase2_iter2_{engine,intake_api}_break.py)
Findings: 3/2/3/3
Fixed (all, each covered by the breaker's tests): B1 the first-three-weeks rule is no longer green outside spring 2027 (calendar coverage checked; the first three weeks of other terms are "check with Trojan Event Services"); B2/B3 tabling hours and the alcohol weekday rule are checked only in part (time of day unknown), so they are never green; H1 a ban comes in from its breaking fact alone (for example "alcohol is the main focus" without "alcohol"); H2 a USG academic-week deadline that has certainly passed (6 academic weeks are at least 42 days) is past due, a hard block, with the other-funding option; M abbreviated weekdays that contradict the date are asked; M an end more than a year after the start becomes a question, not a 500; M dates outside 2000-2100 are refused (422); L impossible headcounts are asked; L control characters dropped from .ics text; L the parse error no longer shows server paths.
Left open: the breaker's questions (should a due date on a holiday or weekend move earlier; does the first-three-weeks rule cover classrooms and off campus; should the packet mention USG's ineligible line items) are for a person.
Full test suite: pass (412, adversarial included); run_eval.py events 30/456/0/0
Gate: iteration 3 (audit) next

### Phase 2, iteration 1 — verify
Date/time: 2026-11-15, about 00:50-01:05 PT
Agent and model: verifier (fresh), Opus 5.5, medium effort, on commit a5ac5e7
Report: docs/reviews/phase-2-iter-1-verify.md
Findings: 0/0/3/6 (all 6 exit criteria pass; 30/30 obligation lists match end to end)
Fixed: M1 with no venue, every on-campus venue's steps are listed as "check with the office" (they were missing); M2 the evaluator counts a miss as silent unless the packet asks the officer; L1 deadlines after the event are past due once passed; L4 "USG" written out in the fallback texts. Each with a regression test.
Left open: M3 most "office decides" items have no contact-by date (no source gives one); L2 "move the date" can suggest a blocked period (the text says to check the new date); L3 an .ics with no dated items is empty (the page disables the button); L4 DPS and GSG appear without full names in rule titles; L5 three more cautious statuses than the test set (ev-23 unsure performers, ev-28); L6 the repository's local .env sets AI_MODE=live (a developer setting, not committed).
Full test suite: pass (389)
Gate: iteration 2 (break) next

### Phase 1, iteration 3 — audit; phase closed
Date/time: 2026-11-15, about 03:50-04:15 PT
Agent and model: one fresh auditor (general-purpose agent following .claude/agents/auditor.md), Opus 5.5, medium effort
Report: docs/reviews/phase-1-iter-3-audit.md
Findings: 0/2/5/4. Clause list: 92 template clauses, 92 clause rules, wording, blanks and conditions match the snapshot; readiness items, numbers and dates match their rules; iteration 2 regression tests exercise the real code.
Fixed (both highs, each with a regression test that failed before the fix): words added after a fixed cover-page sentence keep it from green; a "no appointed positions" answer is treated as not sure when Article III, Section A names an appointed position, so a missing III.D.8 is not hidden. Also fixed (medium): the constitution route runs the check in a worker thread, so an AI call does not stall the server.
Left open: see "Open findings after Phase 1".
Full test suite: pass (449 + 130 adversarial); validate_rules.py OK; run_eval constitutions 21 caught / 0 missed / 0 wrongly flagged; frontend build OK
Close: Phase 1 closed after the third iteration (PLAN.md section 1)

### Phase 1, iteration 2 — break
Date/time: 2026-11-15, about 03:10-03:45 PT
Agent and model: one fresh breaker (general-purpose agent following .claude/agents/breaker.md), Opus 5.5, medium effort
Report: docs/reviews/phase-1-iter-2-break.md (25 failing cases in backend/tests/adversarial/test_phase1_recognition_break.py)
Findings: 7/4/5/1
Fixed (all blockers and highs, each covered by the breaker's tests, now passing): placeholders and filler (TBC, "insert…", lorem ipsum, XX, "to be decided") and blanks that repeat the template's own words are empty; "none" accepted only where the blank allows it, never TBD or brackets; advisor meeting counts that allow fewer are not read as a number; membership barriers written into any blank need a look; only table-of-contents lines are dropped and appendix text is reported; words after a fixed clause keep it from green; a "no" club answer contradicted by the document no longer hides a missing clause; long Parts are checked in linear time; damaged PDF pages are reported. Also fixed (mediums and the low): Windows-1252 text files, "2026-2027" year labels and the other-year note, advisor items open until Dec 1 in the readiness headline, officer titles matched loosely ("Vice-President").
Left open: M (question for the spec) a confident AI "no" with no warning words turns a membership blank green, so against an injected document the model is the only defence there.
Full test suite: pass (446 + 130 adversarial); run_eval constitutions 21/0/0
Gate: not yet, because iteration 3 (audit) has not run

### Phase 1, iteration 1 — verify
Date/time: 2026-11-15, about 02:30-03:00 PT
Agent and model: one fresh verifier (general-purpose agent following .claude/agents/verifier.md, which this session could not load by name), Opus 5.5, medium effort
Report: docs/reviews/phase-1-iter-1-verify.md
Findings: 0/0/1/6 (all 6 exit criteria pass; keyboard use checked by reading the code)
Fixed: the upload form no longer says the file is not kept (the audit log keeps the AI reader's quotes); the hard-coded closing date on the page is gone (the readiness checklist shows it with its source); focus moves to the "could not check this file" message.
Left open: M keyboard use not driven in a real browser; L extra text on the cover page not listed; L co-09 VIII.A.2 shown "wording changed" not "contradicts"; L a changed cover-page clause shows no "your document says".
Full test suite: pass (421 + 105 adversarial)
Gate: not yet, because iterations 2 (break) and 3 (audit) have not run

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

## Open findings after Phase 2

Medium and low findings left open when Phase 2 closed (details in docs/reviews/phase-2-iter-{1,2,3}-*.md):
- **Conflicts:** the parking pair and USG payment-vs-event pair give no applied rule although the rule messages say which applies (M2); the outdoor deposit ($100 vs $200) and late-travel conflicts are not event obligations, so never reach the packet (M3).
- **Rule scope:** the reading step does not read tent size (the officer enters it); the first-three-weeks rule is applied to Trojan Event Services venues only (M7, an open question since Phase 0 M10); final payment leaves out meeting rooms (L); the officer-facing text says the source gives first-three-weeks dates for spring 2027 only, but it also gives fall dates (L).
- **Office decides:** off campus (no approvals rule) office-decides items still have no contact-by date; passed contact-by dates are not hard blocks (L).
- **Lows:** ev-28's answer key expects "condition" where the engine (more cautiously) says "check with the office"; the stricter-rule choice and date checks still appear in eval_sets.py's validator; no test parses the .ics with an independent iCalendar library (the verifier did, by hand); hard blocks carry no citation; the "certainly passed" check assumes the first vendor payment is never after the event; /events/parse has no rate limit and logs audit rows with no club; an .ics with no dated items is empty; DPS and GSG appear without full names in some rule titles; the repository's local .env sets AI_MODE=live (developer setting).
- **Questions for a person (breaker):** should a due date on a holiday or weekend move earlier; does the first-three-weeks rule cover classrooms and off campus; should the packet mention USG's ineligible line items.

## Open findings after Phase 1

Medium and low findings left open when Phase 1 closed (details in docs/reviews/phase-1-iter-*.md):
- **Medium, question for the spec:** a confident AI "no" with no warning words turns a membership blank green, so for that blank the model is the only defence against a document written to fool it (iterations 2 and 3).
- **Medium:** blanks with no AI question (for example II.A.3, open-membership opportunities) are scanned for membership barriers only when they mention membership; "after an interview with the board" there shows green.
- **Medium:** VIII.C.2 (link to the national organization's bylaws) is fixed template text but the rule table makes it conditional on a parent organization; co-01 replaces it with "Not applicable" and passes. A rule-table question for a person, not changed in this phase.
- **Medium:** keyboard-only use (exit criterion 6) was checked by reading the code, never driven in a browser, and has no test.
- **Medium:** II.C.5 (dues) is yellow on every constitution because the reader answers "no" only at medium confidence.
- **Low:** the five "elected or appointed" blanks in III.A.1 accept any word; a second Part with the same number leaves the clause it contradicts green (only the extra-text note turns yellow); scan transcriptions are stored whole in the audit log with no club; club questions and training labels are repeated in the frontend; co-09 VIII.A.2 shown "wording changed" where the key says "contradicts"; a changed cover-page clause shows no "your document says".

## Phase ownership and branches

## Open findings after Phase 3

Medium and low findings left open when Phase 3 closed (details in docs/reviews/phase-3-iter-{1,2,3}-*.md):
- **Scope of rules:** the $4,000 venue and personnel cap adds up venue, personnel and security lines whatever the venue (the source says on-campus; an off-campus venue or staffing line is flagged yellow as a contradiction, but an off-campus security line is not); the vocabulary's performer category includes "speakers' fees", which the guidelines do not name, so a speaker's fee is a certain red (M).
- **Deadlines:** a USG deadline that has certainly passed is yellow (from the Phase 2 engine) and the headline can read "The office decides"; the draft is still blocked (M, carried from iteration 1).
- **Test set:** the 20 budgets check typed lines; reading line items from PDFs, images or screenshots is not measured and recorded mode has no such readings (M). For the demo, record the culture-night quote and the draft once (AI_MODE=record) in Phase 6.
- **Vendor list:** the vendor note is shown apart from the line's verdict and never changes it (by design while the list is unconfirmed) (M, iteration 1).
- **Lows:** the currency pattern is broad ("won", "pounds of brisket" clear every amount in the document, which is the safe direction); drafted paragraphs are not filtered for claims such as "approved"; an unsure travel line drops the travel deadline from the dates list; `first_registered` is accepted but unused (new-club startup fund note not built); some constants are repeated; money routes log AI output with no club; unsure food lines are left out of food per person; an unknown funded-events count gives a question but no finding; "plan for at least N people" may invite overstating attendance.
- **Questions for a person (breaker):** do mandatory per-night hotel fees count toward the $400 cap; do catering delivery or service fees count toward the $35 per person.

## Phase ownership and branches (historical)

Until 2026-11-15 each phase had its own branch and pull request; from then on phases work directly on `main` (see Decisions).

| Phase | Who | Branch |
|---|---|---|
| 1 Recognition check | teammate (second laptop) | `phase-1/recognition` |
| 2 Event packet | this machine | `phase-2/event-packet` |
| 3 Money check | this machine | `phase-3/money-check` |

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
- **Effort and reviewer count (2026-11-15, the humans' decision).** Phase sessions and all sub-agents run at medium effort, not high. Each iteration uses exactly one fresh reviewer sub-agent, so a phase has three in all. The orchestrator does not review its own work. PLAN.md section 1 and CLAUDE.md updated.
- **Push closed phases straight to main (2026-11-15, the user's decision, confirmed directly in the Phase 3 session).** Only one person works on the repository now, so phases work on `main`: no phase branches and no pull requests. At the checkpoint: full suite, PROGRESS.md, `git pull --rebase origin main`, rerun the suite, `git push origin main`, confirm CI on `main`; never force-push. PLAN.md (Checkpoint row, Branches, Phase checkpoint), CLAUDE.md (Conventions, Working with sub-agents) and CONTRIBUTING.md (Branches and commits) updated. Phase 3 was built on `phase-3/money-check` and lands on `main` by fast-forward.
