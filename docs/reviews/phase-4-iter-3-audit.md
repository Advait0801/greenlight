# Phase 4, iteration 3 — audit
Summary: 0 blockers, 1 high, 5 medium, 7 low.

Auditor: fresh agent, on `main` at 8dd0805, as of 2026-11-15, `AI_MODE=recorded` only.
Commands run: `cd backend && .venv/bin/python -m pytest -q` (691 passed); `backend/.venv/bin/python scripts/validate_rules.py` (OK); `backend/.venv/bin/python scripts/run_eval.py` (year_plans 2 cases, 233 caught, 0 missed, 0 wrongly flagged; other sets clean); `npx tsc -b --noEmit` in `frontend/` (clean). Probe scripts were run from the scratchpad against `plan_year` directly; no repository file was changed apart from this report.

## Rule check
| Rule id | Matches source? | Note |
|---|---|---|
| usg-yearly-cap | Yes | `rules/sources/usg-funding-guidelines.txt:77-78` "Section 3: Maximum Funding per Academic Year … maximum of $8,000 … per year". $8,000, per club, per academic year all match. Read through `limit_cents` (`year_planner.py:283`), not hard-coded. |
| usg-events-per-semester-cap | Yes (text); status correct | `usg-funding-page.txt:47` "up to 4 events funded per semester". Marked `unverified` as the humans decided; the planner keeps it yellow everywhere (`year_planner.py:425`, `:536`) and says "confirm with USG". |
| usg-denial-same-day-events | Yes | `usg-funding-guidelines.txt:151` "Conflicting events requested on the same day". Shown yellow (a possible reason to deny, not a ban): correct. |
| usg-academic-week-definition | Yes | `usg-funding-guidelines.txt:41`. `unverified`; its `deadline_table_snapshot` points to `usg-funding-deadlines.txt`, which is labelled a hand transcription. |
| usg-page-deadline-event-date | Yes | `usg-funding-page.txt:49` "six academic weeks before the event date … nine academic weeks before the initial payment due date (whichever comes first)". Offset 6, academic weeks, anchor event date: match. New param `deadline_table_column: "6_week"` is consistent with the table. |
| usg-deadline-travel | Yes | `usg-funding-guidelines.txt:38` "at least 9 academic weeks prior to the date of initial payment due date". Offset 9, anchor initial payment: match. New param `deadline_table_column: "9_week"`. Note: the planner counts this one from the event date, not the payment date (see the high finding and `schemas/plans.py:133-134`, which states the assumption). |
| usg-faq-no-summer-funding (used through the packet) | Yes (text) | `unverified`-style yellow; summer events are left out of the funding plan, yellow (`year_planner.py:492-495`). |
| USG deadline table (`usg-funding-deadlines.txt`) | Read only, shown unconfirmed | Every date taken from it is labelled "unconfirmed copy" / "Check with USG", yellow (`year_planner.py:244-252`, `:664-669`; `ics.py:124-130`). |

No rule marked `read` lacks its text in the snapshot.

## Findings

### [high] The plan's "certain" deadline bound contradicts USG's own table, and the plan shows the later date as the date to apply
Where: `backend/app/services/year_planner.py:228` (`latest = deadlines.shift(start, rule.offset, "weeks", "before")`), `:475` (`_apply_by` prefers `table_date`), `:664-669` (calendar shows only the table date); `backend/app/schemas/plans.py:133-135`; `frontend/src/pages/YearPlanResults.tsx:54-59`.
Expected: PROJECT_CONTEXT section 7 ("Not in the guidelines"): "Academic week is not defined … Get that table and use it as the source of truth instead of computing weeks." A date presented as "at the latest" must really be the latest, and the plan must not show two contradicting deadlines without saying the sources disagree.
Actual: The planner computes "event date minus N calendar weeks" and labels it the latest possible date ("An academic week is at least seven days, so the deadline is no later than this"). USG's table (keyed by event week, deadline on the Wednesday) gives a *later* date for many event weeks. Scanning every date Aug 24, 2026 to Apr 30, 2027, the table date is after the "at the latest" date for 37 event days (6-week column: Nov 17–Dec 1, 2026 and Feb 22–Mar 9, 2027; 9-week column: Oct 26–Dec 1, 2026, Jan 11–12 and Mar 22–Apr 27, 2027). Example, event Monday Feb 22, 2027: the step's "Apply by" reads "USG's table (Greenlight's unconfirmed copy) says Wednesday, January 13, 2027; counted in calendar weeks it is Monday, January 11, 2027 at the latest." The calendar and the .ics only carry January 13. Meanwhile the Phase 2 packet uses the earlier bound for `past_due`: with `as_of=2027-01-12` the same event gets `deadline_passed` problems for `usg-page-deadline-event-date` and is dropped from the funding plan ("the deadline has passed"), even though the calendar entry the officer was following says January 13. So the officer is given a date in the calendar that the plan itself later calls passed.
Why it matters: Trust rule "nothing unverified is presented as certain": the "at the latest" figure rests on an assumption (counting from the event day) that the only USG-published counting method contradicts, and the date shown to act on is the later one. It also computes weeks where the spec says to use the table.
How to reproduce: `plan_year(YearPlanRequest(usg_received_this_year_cents=0, events=[PlanEvent(key="f", name="F", event_date=date(2027,2,22), estimated_cost_cents=100000, usg_request_cents=50000)]), …, date(2026,11,15), …)` → `usg_deadlines[0].latest_possible == 2027-01-11`, `table_date == 2027-01-13`, `strategy.steps[0].apply_by.table_date == 2027-01-13`. Re-run with `as_of=date(2027,1,12)` → event not planned, "deadline has passed".
Suggested fix: When the table date is later than the computed bound, say the two disagree (both cited) and put the earlier date in the calendar, "this week" and "Apply by"; drop the words "at the latest" or call it "Greenlight's count from the event day". Add a test for the Feb 22, 2027 week.

### [medium] With the amount received unknown, a certain overage of the yearly cap is shown only as "unknown"
Where: `backend/app/services/year_planner.py:444-449` (`continue` skips the over-cap check), `:619-622` (budget figure becomes `None`); `frontend/src/pages/YearPlanResults.tsx:164`.
Expected: Money received cannot be negative, so requests alone above $8,000 in one academic year are over the cap for certain (the strategy already uses this reasoning at `:549-553`). The problem list and the budget's "Over the yearly USG cap" should say at least that much is over.
Actual: Two spring 2027 requests of $6,000 each with `usg_received_this_year_cents=None` give only `yearly_cap_unknown` (yellow) and the budget shows "Unknown: enter what USG already gave"; no `over_yearly_cap` red. The strategy caps planned money at $8,000, so exit criterion 2 still holds for the plan itself.
How to reproduce: probe above, `[('yearly_cap_unknown', 'yellow')]`, `usg_requested_over_yearly_cap_cents is None`.
Suggested fix: When requested alone exceeds the cap, add `over_yearly_cap` red with "at least $X over" and show that lower bound in the budget, keeping the question.

### [medium] Calendar and .ics still say "Apply to USG" for events the plan has ruled out of USG funding
Where: `backend/app/services/year_planner.py:664-669` (calendar), `backend/app/services/ics.py:124-130` (.ics). Iteration 2's fix only filtered "this week" (`year_planner.py:298-300`).
Expected: An event the plan leaves out (red, e.g. ticketed) should not get an "Apply to USG" date.
Actual: A ticketed event (red in "Not in the funding plan", rule `usg-ineligible-ticketed-events`) still gets calendar item "Apply to USG: USG application deadline as stated on the USG web page" on Feb 17, 2027 and an .ics entry "Check with USG: apply for T". These items also count towards crowded weeks.
How to reproduce: event `t`, 2027-04-09, `attributes=["ticket_sales"]`, request $500 → `report.calendar` has a `usg_table` item; `plan_to_ics(report)` has `SUMMARY:Check with USG: apply for T`.
Suggested fix: Apply the same filter (in the funding plan, or at least not red) to calendar `usg_table` items and to `plan_to_ics`, or relabel them "Not in the funding plan".

### [medium] The funding strategy never names a fund (spec output), still open from iteration 1
Where: `backend/app/services/year_planner.py:575` (`match_fund(ruleset, e.plan.fund, None)`); `frontend/src/pages/YearPlanResults.tsx:129-131`.
Expected: PROJECT_CONTEXT 4A "Which events to send to USG and to which of the four funds".
Actual: Unless the officer picks a fund, every step says "Not chosen yet (needs a human look)". This is honest (yellow, no guess), but the spec output is not produced. It is listed as open in `docs/PROGRESS.md`.
Suggested fix: Leave as is for the phase, or match the fund in code from the club's purpose and event type with the money check's matcher, shown "unsure" when not certain.

### [medium] The reader's notes on a pasted list are dropped before the officer confirms the rows
Where: `frontend/src/pages/YearPlan.tsx:390-403` (shows `text`, `error`, `had_instructions` but not `r.notes`), `:262-277` (adds rows without notes); `backend/app/api/plans.py:134`.
Expected: Trust rule "when the model is unsure, the result is yellow" and the officer checks every detail. The notes (e.g. "The start date is not complete or not clear", a weekday that does not match) explain why a field is empty or unsure.
Actual: The API returns `notes` but the page never shows them. Unsure details still surface as an empty date (yellow "needs a date") or as "not sure" ticks, so nothing becomes green, but the reason is lost.
Suggested fix: Show each row's notes beside it before "Add these to the plan".

### [medium] The evaluator does not compare the plan's own calendar, strategy or "this week"
Where: `scripts/evaluators/year_plans.py:57-62`.
Expected: Exit criterion 1: "calendar, budget and flagged problems match".
Actual: "calendar" is checked on each event's packet obligations (`report.events[*].packet.obligations`), not on `report.calendar` (which adds contact-by dates and table dates, filters superseded items and is what the page shows). The funding strategy (which events, in what order, how much) and "this week" have no answer key. A regression in `_calendar` or `_strategy` would not show in `run_eval.py` (unit tests cover parts of the strategy).
Suggested fix: Add the expected strategy steps and the table-date calendar items to `data/eval/year_plans/cases.json` and compare them.

### [low] Every event past the semester limit is called "funded event number 5"
Where: `backend/app/services/year_planner.py:531-536`.
Actual: With six spring requests, both left-out events read "Would be funded event number 5 in Spring 2027"; `per_term` is not increased for skipped events. Use a running count or "beyond the 4 a semester".

### [low] An unconfirmed table date is labelled "Passed" in the calendar
Where: `frontend/src/pages/YearPlanResults.tsx:21`.
Actual: A past date from the unconfirmed table copy gets a yellow badge with the plain label "Passed"; in the calendar list (unlike "this week", `:95`) no "unconfirmed copy" text is shown next to it. Suggest "Passed, per the unconfirmed table".

### [low] "Either way it falls before the semester" can be said when only the table date does
Where: `backend/app/services/year_planner.py:233`, `:378-380`.
Actual: `before_semester` is true if either date is before the semester, but the note always says "Either way". No current table row triggers this (checked every date), so it is latent.

### [low] "This week" is the next three dated items, however far away
Where: `backend/app/services/year_planner.py:298-301`; heading at `frontend/src/pages/YearPlanResults.tsx:83`.
Actual: Items months ahead appear under "This week". The spec says "the next three things to do", so the heading is what misleads.

### [low] The plan does not ask how many events USG has already funded this semester (open from iteration 2)
Where: `backend/app/services/year_planner.py:415-429`, `:527-539`.
Actual: The money check asks this (`money_check.py:617-618`); the plan counts only planned events, so fall 2026 could be planned up to 4 more. The limit is yellow anyway.

### [low] No regression test for iteration 1's fix "calendar and this week items show rule text and source"
Where: `backend/tests/unit/test_year_planner.py` (no assertion on `CalendarItem.citation`).
Suggested fix: Assert every non-event calendar item and every "this week" item has a citation.

### [low] Small duplicated logic in the frontend and the planner
Where: `frontend/src/pages/YearPlanResults.tsx:68-73` (`weekOf` recomputes the Monday of a week for busy-week shading, already computed in `CrowdedWeek`); `backend/app/services/year_planner.py:96-107` (`_where` walks breaks and recesses, as the calendar module does). Harmless, but the busy-week shading could use the server's `week_start`/`week_end` instead of date maths in the browser.

## Checked and found sound
- AI reads, code checks: `year_planner.py` imports no AI code (architecture test); the only model use in this phase is `/plans/read-events`, through Phase 2's `parse_sentence`, where code builds every date from stated parts and costs are never read. No prompt asks for a date, sum, cap comparison or verdict. Every figure on the page comes from the report; the browser only formats cents.
- Reuse: obligations, blocked periods and passed deadlines come from `build_packet`; case-by-case reviews come from `check_budget`'s own findings; fund from `match_fund`; caps from rule params through `limit_cents`. No rule numbers are hard-coded (`test_planner_reuses_the_phase_2_and_3_engines`).
- Caps: in 200 random plans the strategy never planned more than 4 events in a term or more than $8,000 (with what was received) in a year; the semester limit is always yellow with "confirm with USG", never a silent block.
- Budget: in the same 200 plans every row and the totals add up exactly (USG planned + club money + still to find = cost; club money never negative).
- Staleness: the plan is recomputed from the whole request, nothing derived is stored; the page hides the old report while recomputing or on an input error.
- Citations: every problem with a rule carries its citation and a finding built by `finding_for`; table-based problems also cite `usg-academic-week-definition`.
- Human approval: no route submits, sends or publishes; the .ics is a download.
- Security and privacy: plan data is kept only in the browser's local storage; routes are stateless; no secrets in the phase's files; text pasted in is passed as untrusted data and instruction-like lines are reported.
- Earlier fixes: iteration 1 H1 (unknown received still caps the plan) and both per-year figures, and all eight iteration 2 tests exercise the fixed behaviour and pass.
