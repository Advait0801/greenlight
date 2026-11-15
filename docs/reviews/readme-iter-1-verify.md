# README rewrite, iteration 1 — verify

Scope: `README.md` in the working tree (modified, uncommitted) checked against the repository on 2026-11-15. Report only; nothing fixed.

Summary: Blockers: 0. High: 2. Medium: 7. Low: 8.

## What was checked and matched (evidence)

| Claim | Command / file | Result |
|---|---|---|
| 827 tests | `cd backend && pytest -q` | `827 passed, 13 warnings` (testpaths = tests, so this includes adversarial) |
| 201 adversarial tests | `pytest tests/adversarial -q` | `201 passed` |
| 289 rules; events 71, funding 76, outside money 22, recognition 120 | `python scripts/validate_rules.py` | exact match |
| 284 verified, 5 unverified, 15 dependent rules yellow | same | `read 284, unverified 5`; `15 more rules depend on an unverified rule` |
| 18 sources | `rules/sources/manifest.json` | 18 entries |
| Eval table (30/456, 20/30, 10/21, 2/233; 0 missed, 0 wrongly flagged; total 740) | `python scripts/run_eval.py` | exact match; 456+30+21+233 = 740 |
| Accuracy page equals a fresh run | `run_eval.py --json` vs `data/eval/results.json`; `tests/integration/test_scripts.py:179` | identical; test exists |
| 92 clauses | `rules/recognition.json` | 92 rules of kind `clause` |
| Library versions | `backend/requirements.txt`, `frontend/package.json` | FastAPI 0.163.0, Pydantic 2.14.3, SQLAlchemy 2.1.8, React 19.3.1, TS 5.9.3, Vite 7.3.8, Tailwind 4.3.5, Node engines >=20.19.0: all match |
| Model names | `backend/app/config.py` | `claude-sonnet-5-5`, `claude-haiku-5-5`, env `MODEL_EXTRACT`/`MODEL_CLASSIFY` |
| Relative links | all files/dirs linked exist; `CLAUDE.md` has `### Ports and addresses` (anchor `#ports-and-addresses`) | OK |
| Entry points | `python -m app --help` (has `--site`), `seed_demo.py --help`, `npm run build` (built OK), `scripts/deploy/*.sh`, `.replit`, `$PORT` default 5000 | OK |
| Architecture test / Finding guard / audit / UntrustedDocument / structured output / routers auto-discovered | `tests/unit/test_architecture.py`, `schemas/common.py:73-96`, `ai/audit.py` + callers, `main.py:63`, `ai/client.py:180,275` | match the README wording |
| CI steps | `.github/workflows/ci.yml` | validate_rules, run_eval, pytest, adversarial, frontend build: match |
| `USG_REVIEWER_KEY` at least 12 chars | `api/usg.py:41` `MIN_KEY_CHARS = 12` | OK |
| Mermaid | both blocks inspected by hand: `flowchart LR`, quoted labels, `[(...)]` cylinders, `-- "label" -->` edges, one `subgraph ... end` | valid syntax as far as can be checked without rendering (no renderer installed) |

## Findings

### 1. [high] "Instructions inside a file are never followed" is contradicted by known issues
README line 94: "**Uploaded text is data.** Instructions inside a file are never followed."
Evidence: `docs/reviews/known-issues.md`, F2: "An AI reading that follows planted text can make one line green ... The comment in `backend/app/ai/untrusted.py` claims more than the code guarantees." Phase 3 iter 1 also left open "L instructions in a quote leave its lines marked sure" (`docs/PROGRESS.md:243`).
Correct fact: uploaded text is wrapped as data and the model is told not to follow it; dates, sums and verdicts are code, so an obeyed instruction cannot change a figure, but a reading that follows planted text can mislabel a line (shown to the officer to edit). The README repeats the exact overclaim the final security review flagged.

### 2. [high] "Every deadline dated" / "every form, approval and deadline, dated" overclaims
README line 37 ("every deadline dated"), line 39 ("every form, approval and deadline, dated, sourced"), line 151 ("Every form, approval and deadline, counted back from the event date"), line 326 ("every form and deadline, dated and sourced").
Evidence: `docs/reviews/known-issues.md` F3: "The year plan dates the USG application deadline ...; the event packet and money check for the same event give no date." F1: "One USG web-page deadline is never dated." `docs/PROGRESS.md:78`: "hours and academic weeks give no date (rule usg-academic-week-definition says no date until a person confirms USG's table)".
Correct fact: deadlines are dated where a rule gives a countable period; USG academic-week deadlines in the event packet and money check, and one USG web-page deadline, are shown yellow without a date.

### 3. [medium] Review report count is 36, not 38
README line 129: "**38 review reports** in `docs/reviews/`".
Evidence: `ls docs/reviews | wc -l` = 38, but that includes `README.md` (an index) and `known-issues.md` (a list, not a report). That leaves 36, of which `ui-pass.md` is the orchestrator's own problem list rather than a reviewer's report (35 reviewer reports). This file, once written, adds one more.
Correct fact: 36 reports (35 by reviewer agents) plus the known-issues list.

### 4. [medium] The start page does not show whether the rule table and calendar loaded
README line 267: "Open http://localhost:5173. The start page shows whether the rule table and calendar loaded."
Evidence: `frontend/src/routes.tsx`: `/` is `Dashboard` (hero, demo button, plan summary; uses `/health` only for the pre-check notice text). Rule/calendar status is on `/status` (`Home.tsx`, "System status", `hidden: true`), reached by the footer link "System status: rules and calendar" (`App.tsx:186`).
Correct fact: the System status page (link at the foot of the sidebar/page, `/status`) shows it.

### 5. [medium] The two new README images are not tracked by git
README lines 56 and 61 use `docs/submission/screenshots/readme-screens.png` and `readme-phone.png`.
Evidence: `git status --short` shows both as `??` (untracked); `README.md` is ` M`. They exist locally, so links resolve here, but on GitHub they will be broken unless added in the same commit.
Correct fact: add both files with the README commit.

### 6. [medium] Not every source is a snapshot with a committed raw file
README line 42 ("**18 snapshotted USC documents**") and line 116 ("raw files committed so every snapshot can be re-derived offline").
Evidence: `rules/sources/manifest.json`: `usg-funding-deadlines` has `commit_raw: false`, `raw: null`, `manual: true`; the manifest says a "manual" source "is a hand transcription". `rules/sources/raw/` holds 17 files.
Correct fact: 17 sources fetched and snapshotted with raw files committed; 1 (USG's funding deadline table, behind a USC sign-in) is a hand transcription.

### 7. [medium] "Works without the AI service" is not true for the application draft (and only one denial-reason recording exists)
README line 126 ("replays saved readings, so the demo and every test run with no API key") and line 322 ("its AI readings are recorded, so it works even when the AI service is slow or down"); demo step 4 ends "the application can be drafted".
Evidence: `ls data/ai_recordings` has no `application_draft` folder. `known-issues.md` F3: "Recorded mode has no recording for the application draft; it returns the code-built draft with a note that the paragraphs could not be drafted." `usg_denial_reason/` holds 1 recording, so step 6 in recorded mode drafts a reason only for that one combination of ticked findings.
Correct fact: in recorded mode the application draft falls back to the code-built draft without drafted paragraphs; a denial reason is drafted only for the recorded selection.

### 8. [medium] "A wrong green can't be built" reads wider than what the guard guarantees
README line 125 and the headline row line 41 ("Never a wrong green").
Evidence: the `Finding` validator (`schemas/common.py:73-96`) enforces citation/verification/office-decides only. `known-issues.md` lists two ways a line can still look green: a planted-text reading (finding 1) and "The money check's line badge stays green above the opened vendor note" (vendor not on USG's list). Wording on line 125 is accurate about the `Finding` object; the heading is not.
Correct fact: a `Finding` cannot be green on an unverified, office-decides or forged citation; the test sets show 0 wrong greens; known issues list cases outside that guarantee.

### 9. [medium] Important existing features are missing from Features
README lines 133-173.
Evidence:
- Year plan: paste a list of events, one per line, read by AI into rows to confirm (`api/plans.py:112` `/read-events`; `YearPlan.tsx:383` "Paste a list"). README line 136 says only "Enter ... or load the demo club".
- Recognition: image upload (screenshot/photo) transcribed by AI (`recognition_document.py:220`; `Recognition.tsx:91` accepts `.png,.jpg,image/*`). README line 143 lists PDF, Word, text, paste only. Money check also accepts images (`MoneyCheck.tsx:475`).
- USG screen, club side: a club checks the status of a sent application with its token and can withdraw it (`api/usg.py:118,128`; `UsgScreen.tsx:53,71`); reviewers see a chart of common failure reasons (`/usg/stats`, `UsgScreen.tsx:15`).
- Money check: reading the fund from the event description (`/money/fund`, `fund_reading.py`) is implied only by "the fund it belongs to".
- Handover: per-role editable packets and a starting plan for next year (`services/handover.py:1-2`); README line 170 gives only "What ran, what it cost and what was denied".

### 10. [low] Eval table rows omit the noted differences
README lines 104 and 106.
Evidence: `results.json` notes — events: conflict lists 30/30 are measured "engine on the test set's attributes", not end to end, and "1 status/date differences"; constitutions: "1 found with a different state than the answer key". Both are in `known-issues.md` ("Two answer-key differences, both on the safe side").
Correct fact: say end to end for obligation lists only, and mention the two safe-side differences.

### 11. [low] Tests section implies `pytest` excludes the adversarial tests
README line 286: "the second command runs the adversarial tests".
Evidence: `backend/pytest.ini` `testpaths = tests`; `pytest --collect-only` includes all 201 adversarial tests in the 827.
Correct fact: `pytest` runs everything (827, adversarial included); `pytest tests/adversarial` runs only the 201 adversarial tests.

### 12. [low] `app/rules/` does not hold the rule engine
README line 381: "`app/rules/` # rule loading and the rule engine".
Evidence: `backend/app/rules/` = `loader.py, schema.py, citations.py, calendar.py, snapshots.py`; the engine is `backend/app/services/rule_engine.py`.
Correct fact: rule loading, citations, snapshots and the academic calendar.

### 13. [low] `seed_demo.py` is not needed to "load the demo club" in the app
README lines 269-273.
Evidence: the "Load the demo club" button calls `GET /plans/demo`, which reads `data/demo/club.json` directly (`api/plans.py:33,81`). `seed_demo.py` writes `Club`/`User`/`YearPlan` rows that no API route reads (grep of `app/api`, `app/services`).
Correct fact: the demo works without seeding; the script loads the demo club into the database (used by the deploy start script).

### 14. [low] "each with one fresh reviewer agent" does not hold for Phase 0
README line 370 (and line 129 "Every phase went through ... (verify, break, audit)").
Evidence: `docs/PROGRESS.md:312,322`: Phase 0 ran four iterations, with five and six reviewers in parallel; Phase 7 ran F1-F3 instead of verify/break/audit. Line 370 is scoped to "feature phase", so this is only a nuance.

### 15. [low] Open findings are not all in PROGRESS.md
README line 370: "open medium and low findings are logged in `docs/PROGRESS.md`".
Evidence: the final reviews' open findings are in `docs/reviews/known-issues.md` (its header says so). Line 129 does link it.

### 16. [low] "Every blocker and high ... fixed with a regression test" does not cover the UI pass
README line 370.
Evidence: `ui-pass-review.md` had 4 highs, fixed (`PROGRESS.md:121`); the frontend has no test runner or test files (`package.json` scripts; no `*.test.*` in `frontend/src`). Scoped to feature phases, so only a nuance.

### 17. [low] "Draft the application once nothing breaks a rule, and send it to the USG screen" vs demo step 4
README line 159 vs line 327.
Evidence: step 4 tells the user to send the red budget to the USG screen before fixing it, so sending is not gated on a clean check (only drafting is). Line 159 reads as if both are.

## Counts

| Severity | Count |
|---|---|
| Blocker | 0 |
| High | 2 |
| Medium | 7 |
| Low | 8 |
