# Phase 4, iteration 1 — verify
Summary: 5/6 criteria passed. Blockers: 0. High: 1.

Verified on 2026-11-15 against `main` at 5bb70c5. No application code or tests were changed. Backend run on port 8014 (`AI_MODE=recorded`, `ANTHROPIC_API_KEY=` empty), Vite dev server on 5187; both stopped afterwards. Every API request below used `"as_of": "2026-11-15"`.

Baseline commands:
- `cd backend && .venv/bin/python -m pytest -q` → `681 passed, 9 warnings in 19.86s`
- `.venv/bin/python -m pytest tests/adversarial -q` → `167 passed, 1 warning in 4.51s`
- `backend/.venv/bin/python scripts/validate_rules.py` → ends `OK`
- `backend/.venv/bin/python scripts/run_eval.py` → `year_plans 2 233 0 0 evaluated` (events 456/0/0, budgets 30/0/0, constitutions 21/0/0)
- `scripts/run_eval.py --json year_plans` → `"2/2 plans match (calendar, budget totals and problems); problems found 12/12, extra 0; budget totals exact in 2/2; splits add up in 2/2"`
- `cd frontend && npm run build` → `✓ built in 543ms`, no type errors

## Exit criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | On the 2 test year plans, calendar, budget and flagged problems match | PASS | `run_eval.py --json year_plans`: 233 caught, 0 missed, 0 wrongly flagged; 2/2 plans match. The evaluator (`scripts/evaluators/year_plans.py`) compares every (event, rule) → (status, due) in both directions, the 5 budget totals exactly, and the problem set (type, rule, severity, events) in both directions. I also posted the demo plan (`GET /plans/demo` + as_of) to `POST /plans/plan`: totals were 1427000 / 150000 / 1277000 / 1125000 / 325000, the same as yp-01's key, and the 5 problems were the same as the key's 5 (semester cap yellow, ticketed red, yearly cap red, the travel deadline before the semester yellow, the mixer deadline before the semester yellow). Not covered: crowded weeks and "this week" have no expected values in the key, so nothing checks them. |
| 2 | Caps enforced: never more than allowed funded events per semester or dollars per year | **FAIL** | When "already received from USG" is left empty (the form's default; `usg_received_this_year_cents: null`), the strategy plans more than $8,000 for one academic year. I sent 5 spring events, each costing $3,000 and asking $3,000: the steps planned 4 × $3,000 = **$12,000** for 2026-27, and `budget.usg_planned_cents` = 1200000. The only signal was a yellow `yearly_cap_unknown` problem. See the finding below. The semester cap holds: in every case at most 4 planned per term. When "received" is known, the yearly cap holds: $8,000 in the demo, $0.01 left gives $0.01, $9,000 received gives $0. |
| 3 | Budget figures exact and always sum to totals shown | PASS (with a caveat) | For the demo, 40 events on one day, no events, odd cents (33333 + 1; costs 10001/99999/7) and cap cases, every row met usg + club + shortfall = cost. Σrows matched each total, total = usg_planned + club + shortfall, and available = club_used + unallocated. All of these were `True` in my checks. The page at 375 px showed $8,000 + $1,500 + $4,770 = $14,270 for the demo and $8,000 + $1,500 + $1,170 = $10,670 after a delete. Caveat: the "Over the yearly USG cap" figure is wrong when a plan spans two academic years (medium finding below). |
| 4 | Editing or deleting an event recomputes everything, nothing stale | PASS | API: stateless; `POST /plans/plan` works the plan out from the request each time. In the UI (headless Chrome, 375 px), loading the demo showed "2 red, 3 to check · $4,770.00 still to find" and 5 problems. Deleting "Spring banquet" changed it to "1 red, 2 to check · $1,170.00", 3 problems, cost $10,670.00, "Asked of USG" $8,250.00, over cap $250.00. "Spring banquet" then appeared 0 times on the page. Moving "Welcome mixer" to 2027-03-12 added the "officers are unavailable" problem, and "February 5, 2027" no longer appeared anywhere. Setting the culture night request to 0 re-ordered the strategy (1. Retreat $2,400, 2. Mixer $400, 3. Workshop $200) and gave "0 red · $6,170.00". Each UI state matched the API's answer for the same request. A request ticket (`latest` ref) throws away stale responses, and invalid input clears the report instead of leaving the old one up. |
| 5 | Plan shows at least one thing a generic chatbot could not know | PASS | The demo plan shows: "5 events in Spring 2027 ask USG for money; USG's web page says up to 4 funded events a semester (not in the guidelines, so confirm with USG)" (yellow, cited); "USG requests total $11,250.00, over the $8,000.00 yearly cap by $3,250.00" (red, cited); and the retreat's travel deadline "falls on December 25, 2026 at the latest (winter recess)", with the table copy giving Wed, Nov 18, 2026, which is labelled unconfirmed. "This week" shows "Wed, Nov 18, 2026 · Check with USG · Apply to USG: USG application deadline for travel". |
| 6 | Usable on a phone | PASS | Checked in headless Chrome (playwright-core with the installed Google Chrome) at 375×812, isMobile. `documentElement.scrollWidth` was 375 with results showing and also with the editor open. No element extended past the viewport (overflow scan of `body *` returned `[]`). The sections stack in one column (`sm:` breakpoints), and the screenshot shows readable text and full-width buttons. Minor: checkboxes are 13 px high and the nav links 18 px high, both small tap targets (low). |

## Findings

### [high] Strategy plans more than the $8,000 yearly cap when the amount already received is unknown
Expected: no plan ever sends more than $8,000 a year to USG (exit criterion 2). Received money is never negative, so whatever the unknown amount is, the plan can at most use the full $8,000. Planned amounts should be capped at $8,000 and still shown yellow because the true remainder is unknown.
Actual: `_strategy` in `backend/app/services/year_planner.py` (lines 489–491) uses `planned = requested` when `remaining[year] is None`, so it applies no cap. With 5 × $3,000 spring requests it plans 4 × $3,000 = $12,000. The budget then counts $12,000 of USG money as covering costs (`usg_planned_cents: 1200000`, "Still to find" only $3,000), which understates the gap by $4,000. The form's "Already received from USG" field is empty by default, so new users reach this path.
Reproduce:
```
POST http://127.0.0.1:8014/plans/plan
{"club_name":"X","as_of":"2026-11-15","money_on_hand_cents":0,"expected_income_cents":0,
 "events":[{"key":"e0","name":"e0","event_date":"2027-03-01","venue":"venue_classroom","headcount":30,"attributes":["food"],"estimated_cost_cents":300000,"usg_request_cents":300000},
           ... same for e1..e4 on 2027-03-02..2027-03-05]}
```
→ `strategy.steps` e0..e3 each `planned_cents: 300000`, status `apply`; `budget.usg_planned_cents: 1200000`.

### [medium] "Over the yearly USG cap" mixes academic years
Expected: the over-cap figure is per academic year, like the `over_yearly_cap` problem.
Actual: `_budget` computes `received + sum(all requests) - cap` across every event, whatever its year. A plan with $5,000 asked in spring 2027 (2026-27) and $5,000 in fall 2027 (2027-28), with 0 received, shows "Over the yearly USG cap: $2,000.00". No year is actually over, and no `over_yearly_cap` problem is raised, so the budget and the problem list disagree.
Reproduce: `POST /plans/plan` with `usg_received_this_year_cents: 0` and events `sp` 2027-03-02 and `fa` 2027-09-15, each cost and request 500000 → `budget.usg_requested_over_yearly_cap_cents: 200000`, problems contain only `outside_calendar`.

### [medium] Calendar and "this week" entries show no rule text or source link
Expected: "Every finding and every deadline shows the rule text and its source link" (PROJECT_CONTEXT section 9).
Actual: `CalendarItem` carries a `citation` in the API, but `YearPlanResults.tsx` (lines 84–100 and 194–213) shows only the date, badge, title and event name for calendar and this-week items. No "Rule text and source" control is shown. Problems, strategy steps and the budget do show sources. The full sources are one click away in each event's packet, but not on the year calendar itself.
Reproduce: load the demo club on `/` and open the "Year calendar" section; no item has a source link.

### [medium] Funding strategy never names a fund unless the officer picks one
Expected: the funding strategy says "which of the four funds" each event should go to (section 4A), and is yellow when unsure.
Actual: `_strategy` calls `match_fund(ruleset, e.plan.fund, None)`, so with no officer choice every step is `status: "unsure"`, "Choose the fund yourself". The mission and event details are never used to suggest a fund. All 3 demo steps show "Not chosen yet (needs a human look)". This is safe, since it is never a false green, but the spec's output is missing.
Reproduce: demo plan → each `strategy.steps[*].fund.status == "unsure"`, `fund == null`.

### [low] Misleading "not planned" reasons when caps interact
Expected: the reason states the cap that actually excluded the event.
Actual: (a) With 6 spring events each asking $3,000 and $0 received, s4 and s5 are listed as "Would be funded event number 5 in Spring 2027", but only 3 events were planned. The semester cap is applied before the yearly cap drops s3, so they would have been event 4 or 5, and the real limit is the yearly cap. (b) With $9,000 already received, the reason reads "The $8,000.00 yearly cap for 2026-27 is used up by the larger requests above", but there are no requests above; the cap was used by money already received.
Reproduce: `POST /plans/plan` with `usg_received_this_year_cents: 0` and six events 2027-03-01..06 at 300000/300000; or `usg_received_this_year_cents: 900000` with one event asking 5000.

### [low] "This week" lists USG application dates for events that are not in the funding plan
Actual: after deleting the banquet and moving the mixer (plan above), the Lantern-making workshop is "Not in the funding plan" (yearly cap), but "this week" still lists "2027-01-13 · Apply to USG" for it.
Reproduce: the demo request without `spring-banquet` and with `welcome-mixer.event_date = 2027-03-12` → `this_week[1]`.

### [low] Partial plan of a single cent
Actual: with $7,999.99 received, the strategy says "Ask for $0.01 of $50.00" (`apply_partly`). This is correct arithmetically but not a useful application. Consider a minimum or a note.

### [low] Small tap targets on a phone
Actual: at 375 px, event-detail checkboxes measure 13 px high, the nav links 18 px and the "Rule text and source" summaries 20 px, all under the usual 44 px touch target. Layout does not overflow.

### [low] Venue request due on a holiday (from the event packet engine)
Actual: the demo's Welcome mixer `tes-space-request` is due 2026-12-25 (Christmas, winter recess) and shows in "this week" as the third item. The date matches the answer key, so this is how the Phase 2 rule is written rather than a Phase 4 regression. Noted because the home screen is where officers will see it.

### Notes (not findings)
- The "4 funded events per semester" limit is shown yellow with "confirm with USG" in both the problem and the not-planned reason. It is not a silent block: the excluded event is listed under "Not in the funding plan" with the reason and a citation.
- Dates from the USG deadline table are always marked "unconfirmed copy" and given yellow "Check with USG" badges.
- `POST /plans/calendar.ics` for the demo returned 42 VEVENTs, the same as the 42 calendar items.
- A USG request above the event's cost is rejected with 422.
