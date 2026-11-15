# Test sets

Four sets, each one JSON file validated by a JSON Schema in `schemas/` and by consistency checks in `backend/app/eval_sets.py` (sums add up, rule ids exist, files exist). `python scripts/run_eval.py` loads and validates all four, then runs each feature's evaluator once that feature exists.

| Set | File | Cases | What is scored | Phase |
|---|---|---|---|---|
| Event sentences | `events/cases.json` | 30 | obligations and dates per event | 2 |
| Budgets | `budgets/cases.json` | 20 | 30 planted violations; verdict per line; fund | 3 |
| Constitutions | `constitutions/cases.json` + `texts/` | 10 | 21 planted faults; every other clause present; one empty file | 1 |
| Year plans | `year_plans/cases.json` | 2 | calendar, budget totals, problems | 4 |

## How the expected results were derived

From the source documents, never from Greenlight's output (no engine existed when they were written):

- **Events.** Attributes are what each sentence states. Obligations were chosen by reading each source rule against the event. Due dates are the event date minus the lead time the source states (calendar days, weeks or months), or the last day plus business days (every Monday to Friday, holidays and recess days included, which gives the earliest date; see `rules/calendar.json` business_days). Deadlines counted in USG "academic weeks" have no date, because no source defines an academic week; the USG deadline table that answers it is only available as an unverified hand transcription (`rules/sources/usg-funding-deadlines.txt`). Once a person confirms that table, fill these dates from it (and keep their status `check_with_office` until then). A test (`backend/tests/unit/test_eval_sets.py`) checks that the hand-written lists agree with the rules' own triggers and lead times, so a silently missing obligation in either shows up.
- **Budgets.** Planted mistakes against the USG Funding Department Guidelines. Sums and per-person figures are plain arithmetic on whole-cent amounts.
- **Constitutions.** Fixed clauses copied exactly from the 2026-27 template, blanks filled for a fictional club, then faults planted. Contradictions follow the open-membership rules on the Campus Activities RSO Accountability page, the Handbook's recognition requirements and the advisor requirements on the recognition page. Finding states:
  - `missing`: the clause is absent, or its blank is empty.
  - `weak`: the template's fixed words were changed or dropped (including the fixed words around a blank) without saying the opposite.
  - `contradicts`: a filled-in blank breaks a rule (the rule is named in `contradicted_by`), or the wording says the opposite of the template.
  Detection and state are scored separately. A clause with a condition (`params.required_if_flag` in `rules/recognition.json`) is listed in `not_applicable` exactly when the club's flag is false; such a clause may then be absent or say "Not applicable" (decision recorded in `docs/PROGRESS.md`). An empty file is `readable: false` with no findings: the check must say it could not read the file, never pass it.
- **Year plans.** Calendars use the event-set method; problems were found by reading the USG guidelines and web page, the Handbook and the Trojan Event Services pages against each plan. How money on hand is split across events is left to Phase 4; only totals are fixed.

## Event obligations: scope and status

Listed: rules in `events.json` and `outside_money.json` of kind deadline, requirement, cap, banned or blocked_period whose triggers match the event; and, when the event asks for USG funding, `funding.json` rules of kind deadline, blocked_period or ineligible whose triggers match. Document requirements of the USG application (quotes, permits, traveler details) belong to the money check.

| Status | Meaning |
|---|---|
| `to_do` | an action the officer must take; `due` is set when the source gives a lead time |
| `condition` | a rule the event must keep to, and as described it does |
| `blocked` | as described, the event breaks the rule (`violated: true`) |
| `office_decides` | the office uses judgment; shown as "contact them by" a date, never green |
| `check_with_office` | rests on something unverified (calendar, academic weeks) or the source hedges ("generally"); `violated` may still be true |

`past_due` is true when the due date is before the case's `as_of` date (2026-11-15). Each case's `source_conflicts` names the pair of rules that disagree and which one is applied (the stricter); `null` when no date can be computed.

## Budgets: scoring notes

Expected findings list every red and office-decides finding and every planted yellow. An engine may add other yellow notes (for example "confirm the vendor is on USG's list", which is unverified) without counting as wrongly flagged. A line expected red but shown green is a missed violation and a wrong green.
