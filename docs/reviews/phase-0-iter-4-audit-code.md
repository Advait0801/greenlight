# Phase 0, iteration 4 — audit (code, trust rules, security, earlier fixes)
Summary: 0 blockers, 3 high, 4 medium, 5 low.

Auditor (e). Commit audited: `f65afcc` on `main`. Scope: `backend/app/` (rule loader, calendar, snapshots, citations, shared types, AI client, models, config, routes, eval-set validator), `scripts/`, `frontend/src/`, `frontend/vite.config.ts`, `.github/workflows/ci.yml`, `.gitignore`, `.env.example`, and the fixes claimed for the iteration 3 code audit. Rule wording against sources belongs to the other four auditors. The rules named below are only the ones where the loader's checks come into play.

What I ran. The Claude API was never called, no USC site was contacted, and `.env` was never opened.
- Checkout: `pytest` gives **266 passed**. `pytest tests/adversarial` gives 59 passed. The other 13 failures are all in the breaker's new `test_phase0_iter4_*` files and are not reported here. `validate_rules.py` prints OK: 285 rules, 280 `read`, 5 `unverified`, calendar `read`. `run_eval.py`: all four sets valid.
- Clean copy (`git archive HEAD`) with a `.env` that sets only `BACKEND_PORT=8794`, `FRONTEND_PORT=5794` and a scratch `DATABASE_URL`, and with those variables removed from the shell:
  - `python -m app` listened on 8794. `/health` gave 200 `ok`.
  - CORS allows `http://localhost:5794` and sends no header to `http://evil.example`.
  - `npm run build` passes. `npm run dev` served on 5794, and `/api/health` and `/api/rules` (285) were proxied to the backend.
  - `seed_demo.py` ran twice, with the same counts each time (1 club, 2 users, 1 plan, 5 events), into `backend/run4.db`.
  - `validate_rules.py`, `run_eval.py --json` and `fetch_sources.py --help` all work.
  - Both servers were stopped afterwards.
- **Mutation check.** In a separate copy I made 62 single edits that each remove one guard or fix, and ran the full suite after each. Harness: `/private/tmp/claude-501/-Users-dalvi-Downloads-Projects-greenlight/238ee673-f1fb-4379-a4ec-c85ea7e316a6/scratchpad/i4/mut4.py`. Results: `/private/tmp/claude-501/-Users-dalvi-Downloads-Projects-greenlight/238ee673-f1fb-4379-a4ec-c85ea7e316a6/scratchpad/i4/mut_results.txt`. 53 of 62 edits make a test fail. The 9 that do not are listed in M4.
- Secrets and committed files:
  - `git log --all -p` has no API-key, private-key or token patterns.
  - No `.env`, `*.db`, `settings.local.json` or recording file was ever committed. `.env`, `backend/.env` and `data/ai_recordings/` are all git-ignored.
  - The only non-USC email addresses in tracked files are demo addresses and `mailer@campusgroups.com` (quoted from a source).
  - Largest tracked file: `rules/sources/raw/student-handbook.pdf` (6.6 MB).

Checks that held up:
- **One prompt.** `BASE_SYSTEM_PROMPT` (`backend/app/ai/untrusted.py:30-45`) forbids totals, per-person amounts, dates, deadlines and verdicts. Nothing in `app/` outside `app/ai/` calls the client yet.
- **Strict validation.** Answers are checked as strict JSON and against a strict model (`client.py:297-313`). `is_confident` needs `high` and a finite value.
- **Request code.** The request label carries a code that a document cannot contain (`untrusted.py:110-128`, `client.py:156-161`).
- **No send path.** There is no submit or send code. The only outbound call is the maintenance script `fetch_sources.py`.
- **Finding type.** It is frozen, a copy is checked again, and a green must carry the rule table's own citation (`schemas/common.py:54-88`).
- **Snapshots.** Committed raw files re-derive the `.txt` snapshots, and their SHA-256 values match (`test_rules_loader.py:305-325`).
- **Interface.** State is never shown by colour alone (`StatusBadge.tsx`). The start page now says "Live (saving responses)" for `record` (`Home.tsx:112`).

### Earlier fixes (iteration 3 code audit), checked one by one

| Iteration 3 finding | Fix works? | Test fails when the fix is removed? |
|---|---|---|
| H1: only `max_`/`min_`/`threshold_` params checked | Partly. Every **number** in params is now checked, including nested dicts and lists. **Dates and clock times** written as strings are still unchecked (H1 below). | Yes for top-level and dict values. **No** for list values (`numbers_no_list` survives; `range_weeks[]` was named in iteration 3). |
| M: Finding guard bypassable (assignment, copy, forged citation, green on info) | Yes for the four routes named. Red and office-decides verdicts on uncertain rules are still accepted (M1). | Yes for all four. The `citation.rule_id == rule_id` check has no test (`finding_rule_match` survives). |
| M: four guards without tests | Yes. | Yes: `offset_in_text`, `academic_week_due_null`, `env_file_port` and `lifespan_integrity` each now fail a test. |
| M: personal data in recordings and audit log | Partly. Only a required, top-level field marked PERSONAL is blanked (H3). `.gitignore` entry added. Docstrings corrected. | Top-level: yes. Nested model and list handling: **no** (`personal_nested`, `personal_list` survive). |
| L: phone "(213) …" form; `campus-filming`; "(15 in all)" | Test widened to bracketed phones and dollar amounts. Other numbers are still unchecked (L1). | Yes. |
| L: `seed_demo.py` deletes a same-named club with no users | Yes: a club with no users is refused. | Yes (`seed_no_members`, `seed_real_member`). |
| L: request-label neutralisation exact-string only | Yes: case- and space-insensitive regex, plus a per-request code. | Yes (`label_regex`, `code_in_system`, `code_in_user`). |
| L: architecture guard tied to file names; `from app import ai` | Yes for both. Relative imports are still missed (M4). | Yes for absolute imports; **no** for `from ..ai import client` (`arch_relative` survives). |
| L: duplicated status logic; anchor ignored | Anchor: refuses a dated "before" deadline with another anchor. Dated "after" deadlines are still neither recomputed nor refused (M3). Duplication not addressed (L4). | Yes (`eval_anchor`). |
| L: two confidence types | Yes: `LineItem.confidence` is now the three-level label with a check constraint. | Yes. |
| L: quote cut at a decimal point | Only when the quote stops right before the "." or ",". A quote that keeps the punctuation passes (H2). | Yes for the case covered. |
| L: stale text | Yes (`main.py:3`, `calendar.py:1-6`, `Home.tsx:112`). | n/a |

## Rule check
Only rules where a loader or validator guard is involved. The other four auditors compare rule text with the sources.

| Rule id | Matches source? | Note |
|---|---|---|
| recognition-application-window | Today, yes | `params.closes_at` (`rules/recognition.json:246`) and `opens_on` (`:245`) are not compared with the quote. `closes_at: 2026-12-22T23:59` loads as `read`, red (H1). |
| recognition-advisor-deadline | Today, yes | `params.due_on` (`recognition.json:268`) is unchecked. `2027-01-15` loads as `read`, red (H1). |
| tabling-hours | Today, yes | `params.allowed_hours` (`events.json:1722`) is unchecked. `08:00-20:00` loads as `read`, red (H1). |
| tes-no-events-first-three-weeks | Today, yes ("after January 26") | `no_events_through` / `first_allowed_date` (`events.json:128-129`) are unchecked, and `confirm_window` was worked out by hand from the calendar (H1). |
| usg-yearly-cap | Yes ($8,000) | If its quote is cut to "…a maximum of $8," with `max_usd_per_year: 8`, it loads as `read`, red (H2). |
| tes-space-request | Yes (3-6 weeks) | `range_weeks` is checked today, but no test fails if list checking is removed (M4). |
| usg-post-event-evaluation, usg-final-invoices | Dates correct today | 28 dated "after" obligations in `data/eval/` are never recomputed by the validator (M3). I recomputed them by hand and all match. |
| minors-registration | Text matches | The message says "under 18". The quoted text says "minors", and no check covers non-dollar numbers in messages (L1). |
| usg-events-per-semester-cap, usg-vendor-list | Unverified, shown yellow | The `Finding` type still accepts a certain **red** on them (M1). |

## Findings

### [high] Dates and clock times in the params of a "read" rule are never compared with the quoted source
Where: `backend/app/rules/loader.py:177-187` (`_numbers` skips strings) and `:198-201`. Affected params (all `read`):
- `rules/recognition.json:190`, `:245-246`, `:268`;
- `rules/events.json:101`, `:128-129`, `:933`, `:1294`, `:1722`;
- `rules/funding.json:326`.

Problem: the iteration 3 H1 fix checks every number in `params` against `source_text`, but dates and times are written as strings (`"2026-11-22T23:59:00-08:00"`, `"10:00-14:00"`, `"2027-01-26"`), so the loader skips them. In a copy of `rules/`, I made four changes and every rule still loaded as `read` and red:
- `recognition-application-window.closes_at` → `2026-12-22T23:59:00-08:00`;
- `recognition-advisor-deadline.due_on` → `2027-01-15`;
- `tabling-hours.allowed_hours` → `08:00-20:00`;
- `tes-no-events-first-three-weeks.no_events_through` → `2027-01-12`.

No test pins any of these values (`grep closes_at|due_on|allowed_hours|no_events_through backend/tests` finds nothing). Some values were also worked out by hand rather than quoted. `confirm_window` 2027-01-27..31 comes from the calendar, and the year in "after January 26" was added by hand. That goes against "every date … comes from plain Python".

Why it matters:
- These are the dates Phase 1 (recognition deadline, advisor deadline) and Phase 2 (tabling hours, blocked January weeks) will show as certain, next to a correct-looking quote.
- It is the same class of problem as iteration 3 H1, which was high. The fix does not cover dates.

Suggested fix:
- In `_check_numbers`, also check every string param that parses as an ISO date, datetime or `HH:MM` (or `HH:MM-HH:MM`) range. The quote must state that date (month name and day number) or that time (for example "11:59pm", "10:00 a.m.", "2:00 p.m.", "12:00 a.m.").
- Values worked out from other data (`confirm_window`, `first_allowed_date`) should be computed by code from the calendar. If they must stay in the file, list them under an explicit `derived_params` key with a reason.
- Add a regression test that changes `closes_at` and `allowed_hours` in `rules_copy` and expects `RuleLoadError`.

### [high] The decimal-point fix is bypassed when the quote keeps the "." or ","
Where: `backend/app/rules/snapshots.py:151-157`; `backend/app/rules/loader.py:171`.

Problem: the iteration 3 fix (commit 5a14885) refuses a quote whose last character is a digit when the snapshot continues with `[.,]digit`. A quote that keeps the punctuation ends in "," or ".", which is neither a digit nor a letter, so it counts as a clean end.
- `text_in_snapshot("The cap is $3,", …"$3,500"…)` returns True, and so does `"…exceed $35."` against "$35.50".
- `_number_in_text(8, "…a maximum of $8,")` also returns True, because its look-ahead only rejects `[.,]` followed by a digit, and the quote ends there.

Reproduced on a copy of `rules/`: `usg-yearly-cap` with `source_text` "Individual organizations may receive a maximum of $8," and `max_usd_per_year: 8` loads as `read`, display `red`. The officer would see a certain $8 yearly cap with a quote that appears to back it. I checked all 280 current `read` rules and none is cut this way today.

Why it matters: this is the guard that makes "matches its snapshot exactly" mean the same figure as the source. One cut-and-paste that stops at a thousands comma gives a wrong cap that is shown as certain.

Suggested fix: in `text_in_snapshot`, treat a quote that ends in `digit + [.,]` as cut when the snapshot continues with a digit, and do the same at the start for `[.,] + digit`. Add the cases `"$3,"` / `"$35."` to `test_quote_boundaries`, plus the `usg-yearly-cap` example in `rules_copy`.

### [high] The personal-data guard misses optional, list and dict fields, and other fields' `evidence`
Where:
- `backend/app/ai/schemas.py:61-72` (`without_personal_data`);
- `backend/app/ai/client.py:67-77` (`audit_payload`) and `:131-133` (recording);
- test `backend/tests/unit/test_ai_client.py` (`test_personal_fields_are_not_kept_in_recordings_or_the_audit_log`).

Problem: the function only looks for `PERSONAL` in a field's own top-level metadata. I checked each of these with `without_personal_data`, and each one leaks the name:
- `name: Annotated[ExtractedField[str], PERSONAL] | None = None`, the natural way to write an optional traveller name. Pydantic keeps the marker inside the union, so `info.metadata` is empty and the name passes through.
- `names: list[Annotated[ExtractedField[str], PERSONAL]]`.
- `by_seat: dict[str, Annotated[ExtractedField[str], PERSONAL]]`. Dict values are never visited.
- A non-personal field whose `evidence` quotes the same line. Example: `headcount.evidence = "travellers: Jordan Example, Riley Roe, …"`. The regression test avoids this case by giving headcount the evidence "4 travellers".

Separately, removing the nested-model branch or the list branch (`personal_nested`, `personal_list`) still leaves the suite green.

Why it matters:
- PROJECT_CONTEXT section 9 says "Traveller details are not stored". The `models/__init__.py:4-5` docstring and the PROGRESS log say the same.
- Phase 3 will add a traveller schema. With today's guard, the most natural way to write it saves names in `audit_log.payload` and in recordings. Recordings are git-ignored but meant to be force-added for the demo.

Suggested fix:
- Walk the field annotation (unions, `list[...]`, `dict[..., ...]`, `Annotated`) rather than `info.metadata`, or require personal data to live in a dedicated `PersonalField` type that blanks itself when serialised.
- Blank `evidence` on every field of a model that contains any personal field, or store evidence only as a hash.
- Add a test that fails unless every field whose name matches `name|email|phone|student_id|dob|birth` is marked personal.
- Extend the regression test to the optional, list, dict and evidence cases.

### [medium] The Finding type accepts a certain red on an unverified rule, and red on information and office-decides rules
Where: `backend/app/schemas/common.py:70-88`.

Problem: the validator only restricts `GREEN`. I checked each of these with `finding_for`, and all are accepted:
- `RED` on `usg-events-per-semester-cap` and `usg-vendor-list` (both `unverified`, shown yellow);
- `RED` on `dps-security` (office decides);
- `RED` on `usg-fund-closure`, an `info` rule. `rules/schema.py:39` says info is "never a pass or fail".
- `OFFICE_DECIDES` on an unverified rule.

The events test set already requires `check_with_office` for an uncertain rule (`eval_sets.py:78-88`), but the shared type does not.

Why it matters:
- CLAUDE.md: "Do not encode anything … unverified as if it were certain. Flag it and show it yellow."
- A red on an office-decides rule predicts the office's decision, which is out of scope.
- This type is meant to be the one place that makes those mistakes impossible for Phases 1-4.

Suggested fix: in `_never_a_wrong_green`, require:
- the citation to be the rule table's own for every verdict (not only green);
- `verdict == YELLOW` whenever the rule is not certain;
- for an `office_decides` rule, only `OFFICE_DECIDES` or `YELLOW`;
- for an `info` rule, no verdict other than yellow, or a separate `INFO` verdict.

Add one test per case.

### [medium] The budget answer key does not tie a rule finding's verdict to the rule's certainty
Where: `backend/app/eval_sets.py:220-264` (`_check_budgets` gets no rule set) and `:368-369`.

Problem: I made three edits to `budgets` case `bu-01` and `validate_set` returned `[]` (valid):
- the `usg-over-4000-case-by-case` finding (office decides) set to `"green"`;
- an added `{"rule_id": "usg-events-per-semester-cap", "verdict": "red"}`;
- an added `{"rule_id": "usg-vendor-list", "verdict": "red"}`.

The events and year-plan sets are checked against `_expected_status`; the budget set is not. Today's data is consistent: the three differences from the display severity are all yellow uncertainty findings.

Why it matters: the Phase 3 evaluator scores the money check against this key. A key that expects green on an office-decides rule, or a certain red on an unverified one, would reward the engine for breaking the trust rules.

Suggested fix: pass `ruleset` to `_check_budgets`. For each `reason == "rule"` finding, allow:
- `yellow` when the rule is not certain;
- `office_decides` (or `yellow`) for office-decides rules;
- never `green`.

Share this with the M1 logic, so the key and the type cannot disagree.

### [medium] The eval validator still accepts 28 dated deadlines it cannot recompute
Where: `backend/app/eval_sets.py:95-104`. Data: `data/eval/events/cases.json:2238`, `:2245`, … (`ev-17`, `ev-20`, `ev-21`, `ev-22`) and the `year_plans` calendar entries (`yp-01`, `yp-02`).

Problem: commit b610d15 ("Reject a dated deadline the eval validator cannot recompute") only refuses a date for **"before"** deadlines with another anchor. `usg-post-event-evaluation` and `usg-final-invoices` are "after" deadlines: 3 business days after `event_end_date`. They carry dates in 8 events cases and 20 year-plan entries, and no code recomputes or refuses those dates. I recomputed them all by hand and they match today. Removing the business-day rule or changing a date would not be caught.

Why it matters: these are the answer key for the Phase 2 and 4 deadline calculators. A wrong date in the key would mark a correct calculator as wrong, or the other way round, with no warning.

Suggested fix: recompute "after" deadlines from `end_date or event_date` in the same units, or refuse any date `_check_obligation` cannot recompute. Add a test that shifts one of these dates by a day.

### [medium] Nine guards have no test that fails when they are removed
Where, one line per mutation that leaves all 266 tests passing:
- `numbers_no_list`, `backend/app/rules/loader.py:185-186`: numbers inside lists in params are no longer checked. This was part of iteration 3 H1, which named `range_weeks[]`.
- `personal_nested` and `personal_list`, `backend/app/ai/schemas.py:68-71`: see H3.
- `finding_rule_match`, `backend/app/schemas/common.py:76-77`: a finding for rule A carrying rule B's citation.
- `arch_relative`: `from ..ai import client as _ai_client` added to `app/rules/citations.py` passes `tests/unit/test_architecture.py:15-29`. The check ignores `ImportFrom.level`, and `importlib.import_module("app.ai")` is not seen either.
- `refusal_validate`, `backend/app/ai/client.py:298-299`: a recording saved with `stop_reason: "refusal"` would be parsed as an answer.
- `positive_limits` (`> 0` replaced by `>= 0`), `loader.py:194-197`: a zero cap loads.
- `banned_fact`, `loader.py:390-391`: a banned rule with no `violated_when`.
- `number_lookbehind`, `loader.py:171`: param 50 would match "$35.50", and 500 would match "$3,500".

Why it matters: CLAUDE.md requires every fix to come with a test that fails without it. The architecture test is what enforces "AI reads, code checks", and a relative import gets past it unnoticed.

Suggested fix: add one `rules_copy` or unit test per line above. In the architecture test:
- resolve relative `ImportFrom` (module plus level) against the file's package;
- flag `importlib.import_module` and `__import__` calls naming `app.ai`.

### [low] The message-figure test covers only phones and dollar amounts, by substring
Where: `backend/tests/unit/test_rules_loader.py:343-360`.

Problem:
- `amount in quoted` is a substring check, so a message saying "$3" passes against a quote that says "$35".
- Numbers that are not dollar amounts are not checked at all. Scanning messages for numbers that are absent from their own quote (and the rules they name) finds, for example:
  - `minors-registration`: "under 18" (the quote says "minors");
  - `recognition-officer-trainings`: "Hazing Prevention 101" (the name is in params, not in the quote);
  - `high-risk-waivers`: "5K" (quoted as "5K run", so this one is fine).
- The iteration 3 suggestion was to check every number.

Why it matters: a figure shown to the officer should be in the quoted source or computed by code.

Suggested fix: match amounts with word boundaries, check every digit run in a message against the quote with the same `_number_in_text`, and keep a short, reasoned exemption list.

### [low] The Finding guard can still be skipped, and the `findings` table has no guard
Where: `backend/app/schemas/common.py:54-88`; `backend/app/models/findings.py:10-31`.

Problem:
- `Finding.model_construct(..., verdict=GREEN)` and `BaseModel.model_copy(f, update={"verdict": GREEN})` both give a green on `usg-events-per-semester-cap`.
- The database `findings` row allows `'green'` with no citation and no rule version, although `models/rules.py:17-18` says saved results can name the version they were checked against.

Why it matters: Phase 1-4 code that stores or rebuilds findings can skip the Pydantic guard.

Suggested fix: store findings only through a function that takes a validated `Finding`. Add `rule_version` to the table, and a check constraint or service-level test that a stored green has a certain rule.

### [low] fetch_sources.py does not update `version_date` when a source is re-fetched
Where: `scripts/fetch_sources.py:83-111`; `backend/app/rules/loader.py:266-270`.

Problem: a re-fetch rewrites the snapshot, `fetched_at` and `sha256`, but leaves `version_date`. Each rule's `effective_date` is compared with `version_date`, so after a re-fetch a new version of a document keeps the old effective date. Only the text check catches a change, and only for text that was quoted.

Why it matters: citations show "version of <effective_date>", which could then name the wrong version.

Suggested fix: after a re-fetch, print every source whose sha changed and require a person to set `version_date`. Alternatively, have `validate_rules.py` fail when `fetched_at` is newer than a manual `version_confirmed_at`.

### [low] Logic written twice, and unused scaffolding
Where:
- Verdict labels are defined in `backend/app/schemas/common.py:27-32` and again in `frontend/src/components/StatusBadge.tsx:5-11`.
- The status logic is in `backend/app/eval_sets.py:78-88` and again in `backend/tests/unit/test_eval_sets.py` (iteration 3 L, not addressed).
- Unused today: `VERDICT_LABELS`, `Settings.app_env` (`config.py:36`), `log_ai_output` (`ai/audit.py:11`), `require_calendar` (`api/deps.py:39`).

Problem: copies of the same rule can drift. The unused pieces are scaffolding for later phases.

Why it matters: when Phase 2 adds the real status function, the eval key and the product can disagree with no test noticing.

Suggested fix: serve the verdict labels from the API (or generate them), make the eval validator import the Phase 2 status function once it exists, and remove what no phase will use.

### [low] The start page counts only `unverified` rules as "not verified"
Where: `frontend/src/pages/Home.tsx:99`.

Problem: the label uses `by_verification.unverified`, while the list below it uses `verified !== "read"` (`Home.tsx:50`). If a `fetched` rule is ever added, the count and the list disagree, and the count understates what is unconfirmed. No rule is `fetched` today.

Why it matters: the start page is where a judge sees how much of the rule table is unconfirmed.

Suggested fix: count every mark other than `read`, or have `/health` return `not_read` directly.
