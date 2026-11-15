# Phase 0, iteration 3 — audit (code, trust rules, security, earlier fixes)
Summary: 0 blockers, 1 high, 3 medium, 8 low.

Auditor (e) of five. Commit audited: `9c3f500` on `main`. Scope: `backend/app/`, `backend/tests/` (including `adversarial/`), `scripts/`, `frontend/src/`, `frontend/vite.config.ts`, `.github/workflows/ci.yml`, `.env.example`, `.gitignore`, `data/eval/` validation, `data/demo/`. The other four auditors check the rule text against the sources, so this report only looks at rules where the code's guards are involved.

What I ran (the Claude API was never called and `.env` was never read):
- `pytest` (from `backend/`, `ANTHROPIC_API_KEY` unset, dead HTTP proxy): **208 passed**. `pytest tests/adversarial`: **59 passed**.
- `npm run build` in `frontend/`: passes (`tsc -b && vite build`, 48 modules).
- From the root of a clean copy (`git archive HEAD`, no `.env`): `validate_rules.py` prints OK, `run_eval.py` reports all four sets valid, and `seed_demo.py` (throwaway DB) seeds 1 club, 2 users, 1 plan and 5 events.
- `python -m app --no-reload` from the copy on `BACKEND_PORT=8791`, `FRONTEND_PORT=5791`, with a throwaway SQLite file. `/health` returns `ok`, 259 rules (`read` 254, `unverified` 5), 15 shown yellow, calendar `read`. The only routes are `/health`, `/rules` and `/rules/{rule_id}`. `..%2F..%2Fetc` gives 404 and `POST /rules` gives 405. CORS gives no header to `http://evil.example` and allows `http://localhost:5791`. `usg-approved-vendor` red→yellow, `usg-deadline-vendor` red→yellow, `usg-events-per-semester-cap` →yellow, `dps-security` →office_decides. Each has a citation with `source_url` and `source_text`. The server was stopped afterwards and port 8791 is free.
- **Mutation check of the earlier fixes.** In the clean copy I removed one fix at a time and ran the full suite. 39 mutations in total; the harness and results are in `/private/tmp/claude-501/-Users-dalvi-Downloads-Projects-greenlight/238ee673-f1fb-4379-a4ec-c85ea7e316a6/scratchpad/mutate.py`. 35 of 39 make at least one test fail. The 4 that pass silently are in M2.
- Secrets: `git log --all -p` contains no API-key, private-key or token patterns. No secret value was printed. `.env`, `*.db` and `settings.local.json` were never committed. `.env` is ignored (`.gitignore:2`), and `.env.example` has an empty `ANTHROPIC_API_KEY=`.

Checks that held up:
- **AI reads, code checks.** There is one prompt, `BASE_SYSTEM_PROMPT` (`backend/app/ai/untrusted.py:27-42`). It forbids totals, per-person amounts, dates, deadlines and pass/fail decisions, and nothing in `app/` calls `ClaudeClient.extract` yet. Model output is validated by strict JSON plus a Pydantic strict model (`client.py:285-303`). `is_confident` requires `high` and a finite value.
- **No submit or send path.** Nothing in the code submits or sends: the only network call is `scripts/fetch_sources.py`, a maintenance script. `FundingOption.draft_approved` defaults to false.
- **Uploaded content is data.** Untrusted text is HTML-escaped inside `<document>` with escaped attributes, and the injection test exists.
- **Rule code stays away from the AI.** The rule code does not import `app.ai`.
- **Plain language and colour.** The interface never shows state by colour alone (`StatusBadge` has an icon and a label), and the USG acronym is spelled out.

## Rule check
Only rules where a code guard is involved. The other auditors cover rule text against sources.

| Rule id | Matches source? | Note |
|---|---|---|
| lafd-division-5-permit | Yes (450 sq ft) | `params.tent_area_sqft_over` is not checked against `source_text` by the loader. 4500 loads as `read` (H1). |
| tes-rso-deposits | Yes ($300 / $300 / $100 / 5 business days) | `deposit_usd.*` and `due_business_days_after_processing` are unchecked. A $1 outdoor deposit loads (H1). |
| alcohol-thursday-saturday | Yes (one hour) | `service_ends_hours_before_end` is unchecked. `-3` loads (H1). |
| classroom-requests-week-4 | Yes (Week 4) | `requests_open_week` is unchecked. `9` loads as certain red (H1). |
| amplified-sound-90-dba | Yes (90 dBA, 45 feet) | `max_dba` is checked; `measured_at_feet` is not (H1). |
| uepa-late-exception, usg-fund-closure, tes-space-request | Yes (48 hours; 50%; 3-6 weeks) | `typical_minimum_hours`, `utilization_threshold` and `range_weeks` are unchecked (H1). |
| recognition-three-items-per-officer | Text matches | `params.officers: 5` and the message's "(15 in all)" are not in this rule's `source_text` (L1). |
| campus-filming | Text matches | The message adds "(213) 740-6951", which is not in the cited TES Terms; it is in `student-handbook.txt:5136-5138`. The iteration 1 phone-number regression test misses this format (L1). |
| usg-approved-vendor, food-approved-provider | Yes | Iteration 1 M3 fix holds: both depend on unverified lists and display yellow. |
| usg-food-cap, usg-hotel-cap, usg-yearly-cap, usg-venue-personnel-cap, usg-over-4000-case-by-case, tabling-limits, recognition-ten-students, recognition-five-more-members, recognition-appeal | Yes | `max_` / `min_` / `threshold_` params are checked against `source_text` at load time. |

## Findings

### [high] Iteration 2's H1 fix covers only params named `max_`, `min_` or `threshold_`; ten other numbers load unchecked, including the two the breaker named
Where: `backend/app/rules/loader.py:151` (`LIMIT_PREFIXES`), `backend/app/rules/loader.py:173-182`. Rules: `rules/events.json:893` (`lafd-division-5-permit`), `:293` (`tes-rso-deposits`), `:793` (`alcohol-thursday-saturday`), `:504` (`classroom-requests-week-4`), and `amplified-sound-90-dba`, `uepa-late-exception`, `usg-fund-closure`, `tes-space-request`, `recognition-three-items-per-officer`.

Problem: the iteration 2 report (H1) said "Every other param (`max_days_per_month`, `max_dba`, `tent_area_sqft_over`, `deposit_usd`, etc.) can carry any value". PROGRESS.md records the fix as "every limit and offset of a 'read' rule must be stated in its quoted text". `_check_numbers` skips every key that does not start with `max_`, `min_` or `threshold_`. These numeric params are still not compared with the source text and not checked for sign: `tent_area_sqft_over`, `deposit_usd.{bovard,trojan_grand_ballroom,venue_outdoor,venue_tes_meeting_room}`, `due_business_days_after_processing`, `service_ends_hours_before_end`, `requests_open_week`, `measured_at_feet`, `typical_minimum_hours`, `utilization_threshold`, `range_weeks[]`, `items_per_officer`, `officers`.

Reproduced on a copy of `rules/` (`/private/tmp/claude-501/-Users-dalvi-Downloads-Projects-greenlight/238ee673-f1fb-4379-a4ec-c85ea7e316a6/scratchpad/probe1.py`). These four changes all load with no error, and each rule stays `read` and certain:
- `tent_area_sqft_over: 4500`, shown red;
- `deposit_usd.venue_outdoor: 1`;
- `service_ends_hours_before_end: -3`;
- `requests_open_week: 9`, shown red.

Today's values match their sources. No test pins any of them (`test_key_numbers_match_the_sources` covers 4 caps and 4 offsets).

Why it matters: "a wrong rule here is wrong everywhere" (PLAN Phase 0). In Phase 2, a mistyped `tent_area_sqft_over` would let a 1,000 sq ft tent go without the Los Angeles Fire Department permit obligation, and a wrong `requests_open_week` would block or allow classroom events on the wrong dates. Each would be shown as certain, with a correct-looking quote beside it. The iteration 2 finding was high, and the fix the log records as done does not cover the cases the breaker listed.

Suggested fix: apply the number-in-text check to every numeric value in `params` (recursing into dicts and lists), not only to prefixed keys. Allow an explicit exemption list for derived values, each with a reason (for example `officers` comes from another rule; `utilization_threshold` 0.5 is "50%"). Also refuse negative values. Add a regression test that mutates `tent_area_sqft_over` and `deposit_usd.venue_outdoor` in `rules_copy` and expects `RuleLoadError`.

### [medium] The green-verdict guard on `Finding` can be bypassed in three ways
Where: `backend/app/schemas/common.py:33-68`.

Problem: the iteration 2 M4 fix validates only at construction, and it trusts the citation's own fields. Reproduced (`/private/tmp/claude-501/-Users-dalvi-Downloads-Projects-greenlight/238ee673-f1fb-4379-a4ec-c85ea7e316a6/scratchpad/probe2.py`). Each of these ends with `verdict == green`:
1. **Assignment.** Build a yellow `Finding` for `usg-events-per-semester-cap`, then `f.verdict = Verdict.GREEN`. The model has no `validate_assignment` and is not frozen.
2. **Copy.** `Finding(... "dps-security", OFFICE_DECIDES ...).model_copy(update={"verdict": Verdict.GREEN})`.
3. **Hand-built citation.** `citation_for(rs, "usg-events-per-semester-cap").model_copy(update={"verified": "read", "uncertain_reasons": [], "display_severity": "red"})` is accepted with a green verdict. `Citation` is a plain model that anyone can build.

Also, green is accepted on an `info` rule (`usg-fund-closure`), although `rules/schema.py` says info is "never a pass or fail".

Why it matters: this type is the single place meant to make "unsure is never green" and "office decides is never a pass" impossible to break. Phase 1-4 code that builds a finding and then "upgrades" it after a check would silently produce a wrong green.

Suggested fix:
- Make `Finding` and `Citation` `frozen=True`; this also stops a `model_copy` from sneaking a green in.
- Re-run the guard against the `RuleSet` in a factory, for example `make_finding(ruleset, rule_id, verdict, ...)` that computes the citation itself. Make it the only constructor the features use.
- Refuse green when the display severity is `info`.
- Add tests for each of the three bypass routes.

### [medium] Four fixes or guards have no test that fails when they are removed
Where:
- `backend/app/rules/loader.py:183-185`: offset must be stated in `source_text` (iteration 2 H1).
- `backend/app/eval_sets.py:91-92`: an academic-week obligation must have a null due date (exit criterion 4 guard).
- `backend/app/config.py:30-34` with `backend/tests/unit/test_config.py:22-28`: ports read from the repository `.env` (iteration 1 M1).
- `backend/app/main.py:39-41`: two workers at start-up (iteration 2 L8).

Problem: I removed each one in a clean copy and ran the full suite. 208 tests still passed every time:
- `offset_in_text`: `if not _number_in_text(rule.offset, ...)` replaced by `if False:`.
- `academic_week_due_null`: the check removed.
- `env_file_port`: `env_file=None`. The test passes `_env_file=env` explicitly, so it tests pydantic-settings, not the app's own `env_file` setting.
- `lifespan_integrity`: `except IntegrityError` replaced by an unrelated exception.

The adversarial offset tests (`test_deadline_offset_of_the_wrong_type_is_refused`) cover only the type, and the boolean case is refused anyway by the number-in-text check. PROGRESS.md says "Each fix is its own commit with its test", and CLAUDE.md says "Every bug fix comes with a test that fails before the fix".

Why it matters: these guards protect the exit criteria (numbers match the source, an unverified unit is never given a certain date) and a documented command. A later refactor could remove any of them with CI staying green.

Suggested fix: add these tests:
- `minors-registration` with `offset: 6` in `rules_copy` should raise `RuleLoadError`;
- an `events` case giving `usg-deadline-vendor` a non-null `due` should be rejected;
- `Settings()` with no `_env_file`, run from a temporary `REPO_ROOT`, or a subprocess `python -m app --help`-style check of the port it reads;
- a test that runs `lifespan` twice against one database file, or calls `sync_rule_versions` from two sessions and then starts the app.

### [medium] Recordings and the audit log keep document text through the model's `evidence` field; recordings are not git-ignored
Where:
- `backend/app/ai/client.py:179-201`: `save_recording` stores `response_text` verbatim; its docstring says "never their content".
- `backend/app/ai/client.py:62-71`: `audit_payload` stores the full output.
- `backend/app/ai/schemas.py:23-24`: `evidence` is "the words in the material the value was read from".
- `backend/app/config.py:52`: recordings go to `data/ai_recordings/`.
- `.gitignore`: no entry for that folder.
- `backend/app/models/__init__.py:4-5`: says traveller details are never stored.

Problem: every extraction schema built on `ExtractedField` returns verbatim quotes from the uploaded file. Those quotes go into the recording file and into `audit_log.payload` unchanged. `test_record_mode_saves_fingerprints_not_content` (`tests/unit/test_ai_client.py`) passes only because its fake answer quotes "about 150 people", which is not in the document. Recordings made in `AI_MODE=record` from a real officer's upload land in a tracked folder. Nothing stops a later schema (a traveller list, for instance) from extracting names or IDs, which would then be stored in both places.

Why it matters:
- PROJECT_CONTEXT section 9 says "Traveller details are not stored" and "A club's data is private to the club". The repository will be public for judging.
- The claim in the client docstring and PROGRESS.md ("Recordings store document fingerprints, not text") is not true for any schema that uses `evidence`.

Suggested fix:
- Add `data/ai_recordings/` to `.gitignore`, except a `demo/` subfolder made only from the synthetic demo and test data.
- Correct the docstring.
- Add a guard in `save_recording` and `audit_payload` that refuses or redacts fields marked personal; for instance, a `Personal` annotation that schemas must use for traveller fields, so only a presence flag is kept.
- Add a test whose recorded `evidence` quotes the document.

### [low] The phone-number regression test misses the "(213) 740-6951" form; `campus-filming` cites a source that lacks its number
Where: `backend/tests/unit/test_rules_loader.py:343-349`; `rules/events.json:1303` (`campus-filming`); `rules/recognition.json:194`.

Problem:
- **The test is narrower than its name.** `test_every_figure_in_a_message_is_in_the_quoted_source` only matches `\d{3}-\d{3}-\d{4}`.
- **`campus-filming`.** Its message adds "((213) 740-6951)". That number is not in its `source_text` or in the TES Terms it cites; it is in `rules/sources/student-handbook.txt:5136-5138`. This is the same pattern as iteration 1 L4.
- **`recognition-three-items-per-officer`.** Its message states "(15 in all)" and its params hold `officers: 5`, neither of which is in its quoted text. 5 comes from another rule, and 15 is arithmetic done by hand in a data file.

Why it matters: a figure shown to the officer should be in the quoted source, or computed by code.

Suggested fix: widen the test to every number in a message, with a short exemption list for clause and section numbers and years. Move the filming phone number to a rule that cites the Handbook. Drop "(15 in all)" or have code compute it from the two rules.

### [low] `seed_demo.py` still deletes a same-named club that has no users
Where: `scripts/seed_demo.py:36-49`; test `backend/tests/integration/test_scripts.py:112-132`.

Problem: the iteration 2 L12 fix refuses only when the club has a user whose email is not a demo email. A real "Lantern Cultural Society" with plans and events but no users yet (or users with `club_id` set to NULL) is still deleted, cascading to its plans and events. The test only covers the club-with-a-real-user case. The docstring still says "Nothing else in the database is touched".

Why it matters: this is the script that will be run against the deployed database in Phase 6.

Suggested fix: mark the demo club explicitly (a flag column or a fixed id or slug) and only ever replace that row. Add a test with a same-named club that has a plan and no users.

### [low] Request-label neutralisation is exact-string only
Where: `backend/app/ai/untrusted.py:96`.

Problem: the label is replaced only on an exact, case-sensitive match. These forms pass through unchanged:
- `request from greenlight (not from any document):`
- the same label with a double space;
- the label inside a PDF or image block.

It stays inside the escaped `<document>`, so this is defence in depth only.

Why it matters: an injection could still imitate the trusted request.

Suggested fix: use a per-request random nonce in the trusted label (and in the closing instruction). The model can then tell the real request because a document cannot know the nonce.

### [low] The architecture guard depends on file names that do not exist yet
Where: `backend/tests/unit/test_architecture.py:9`, `:14-20`.

Problem:
- **Fixed names.** `NO_AI` lists `services/rule_engine.py`, `services/deadlines.py` and `services/year_planner.py`, then filters with `target.exists()`. If Phases 2-4 use other names (for example `app/engine/`), the "code never imports the AI" guard silently checks nothing for them.
- **Missed import form.** `from app import ai` (module `app`, name `ai`) is not detected.

Why it matters: this is the test that enforces "AI reads, code checks".

Suggested fix: invert it. Allow `app.ai` imports only from an explicit list of intake and drafting modules, and fail for any other module under `app/`. Catch `ImportFrom` with `module == "app"` and `alias.name == "ai"`.

### [low] Status, deadline and trigger logic is written three times
Where: the three copies are
- `backend/app/eval_sets.py:52-80` (`_back`, `_expected_status`);
- `backend/tests/unit/test_eval_sets.py:82-89` and `:183-200`;
- the trigger scope in `tests/unit/test_eval_sets.py::test_event_obligations_agree_with_rule_triggers` and `tests/adversarial/test_phase0_eval_sets_break.py:102-129`.

Problem:
- **Diverging copies.** The rule "uncertain or yellow → `check_with_office`; office decides → `office_decides`; …" exists in three places, and Phase 2's deadline calculator and packet will be a fourth. The copies can drift apart.
- **Anchor ignored.** `_check_obligation` (`eval_sets.py:87-88`) ignores `rule.anchor` and always counts back from `event_date`. That is right only because every current "before" rule in days, weeks or months anchors on `event_date`.

Why it matters: when the copies drift, the answer key and the product can disagree with no test noticing, or agree on a mistake.

Suggested fix: when Phase 2 builds the deadline calculator and status function, have `eval_sets.py` and the tests import them, or at least share one `expected_status(ruleset, rule_id, violated)`. Make `_check_obligation` skip or refuse anchors other than `event_date`.

### [low] Two different confidence types
Where: `backend/app/models/documents.py:36`, `:47` (`LineItem.confidence: float`, 0..1); `backend/app/ai/schemas.py:13` (`Confidence = Literal["high","medium","low"]`).

Problem: the database stores a float, while the AI layer produces a three-level label and `is_confident` accepts only `high`. No mapping is defined.

Why it matters: Phase 3 will have to invent a mapping, and a threshold such as `confidence >= 0.5` would let "medium" through as confident, against "unsure is yellow".

Suggested fix: store the same three-level label (with a check constraint), or define one mapping function beside `is_confident`.

### [low] A quote that stops at a decimal point passes the word-boundary check
Where: `backend/app/rules/snapshots.py:151-152`.

Problem: "." is not alphanumeric, so a quote ending in "$35" cut from "$35.50" (or "$4" from "$4.00") counts as a clean end. The iteration 2 M7 fix covers digits only.

Why it matters: the cut quote shows a figure that is not the one in the source. No current rule does this.

Suggested fix: treat `digit + [.,] + digit` as part of one token in the boundary check.

### [low] Stale text after the calendar was confirmed and the start command changed
Where:
- `backend/app/main.py:3`: still documents `uvicorn app.main:app --reload --port ${BACKEND_PORT:-8000}`; CLAUDE.md now says `python -m app`.
- `backend/app/rules/calendar.py:3-4`: "marked unverified until a human confirms it … must therefore be shown with that caveat". The calendar is now `read`.
- `docs/PROGRESS.md:83`: the open-questions row still says the calendar is "still unverified until a person confirms".
- `frontend/src/pages/Home.tsx:112`: labels `AI_MODE=record`, which makes live calls, as "Saved responses".

Why it matters: a new session resumes from PROGRESS.md and these comments. The start page also misreports when live API calls are being made.

Suggested fix: update the four places. Show "Live (saving responses)" for `record`.
