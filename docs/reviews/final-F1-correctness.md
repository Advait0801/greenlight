# Final review F1 — correctness
Verdict: READY AFTER FIXES
Must fix: 2. Known issues: 6.

Reviewed on `main` at 8919e42, as of 2026-11-15. Suites run: `pytest` 821 passed; `pytest tests/adversarial` 201 passed; `scripts/validate_rules.py` OK (289 rules, 284 read, 5 unverified, 15 inherit yellow); `scripts/run_eval.py`: events 456/0/0, budgets 30/0/0, constitutions 21/0/0, year plans 233/0/0; `npm run build` OK. The app ran on port 8810 against a temporary database (`AI_MODE=recorded`, no key) and I drove `/plans/demo`, `/plans/plan`, `/plans/calendar.ics`, `/money/check` and `/recognition/readiness`.

## Must fix before submission

### 1. A cap shows green when an unsure line could push it over
Where: backend/app/services/money_check.py:476-481 (food, $35 per person) and :498-503 (venue and personnel, $4,000)
Problem: The food total and the venue-and-personnel total count only lines whose category is sure (`category_sure`). A line the reader was unsure about is shown yellow, but the sure lines next to it still get a green "within the cap" pass. That pass is worked out without the unsure line.
Reproduced through `POST /money/check` with an event at `venue_tes_large`:
- line 1 is `venue_rental`, sure, $3,500
- line 2 is `personnel`, unsure (`category_sure: false`), $1,000

Result: line 1's badge is **green**, with the pass "Venue and personnel total $3,500.00, within the $4,000.00 USG covers". If line 2 is personnel, as the reader guessed, the total is $4,500 and the cap is broken. That is a wrong green on the line badge.
The same thing happens with food: a sure line at $30 per person plus an unsure food line at $10 per person gives a green `usg-food-cap` pass and a "Food per person: $30.00" headline. The real figure could be $40. Food lines also carry "office decides", so here the green appears only in "Rules this line meets", but it is still a green the code cannot back.
Smallest fix: before each "else: pass" branch, add the amounts of unsure lines whose guessed category is in the cap's categories (food, or `vp_categories`). If the total with them would go over the cap, do not add the pass. Instead, add a yellow finding to each sure line, for example: `b.item(rule.id, Verdict.YELLOW, f"If line(s) {nums} are also {label}, the total is {money(t)}, over the {money(cap)} cap; needs a human look.", reason="cannot_compute")`. Otherwise keep the pass. Add one regression test for each cap. No budget in `data/eval/budgets` has an unsure line, so the evaluation numbers do not change.
Risk of fix: safe (about 10 lines in one function, covered by `tests/unit/test_money_check.py` and the budgets set)

### 2. A line from a vendor not on USG's list is shown green
Where: backend/app/services/money_check.py:678 (the line verdict is `_worst` of `entry.findings` only; `vendor_checks` is left out); frontend/src/pages/MoneyCheck.tsx:529
Problem: USG's guidelines say "We will not accept a vendor not on the list." The vendor check correctly makes a yellow finding with the status `not_on_list`, but that finding is not counted in the line's verdict. So a line from an unlisted vendor shows a **green** badge. The `not_on_list` result sits in a closed `<details>` whose summary reads the same for every vendor ("Vendor list check (separate from eligibility): needs a human look").
Reproduced: one `printing` line, $200, vendor "Totally Unknown Catering LLC", quote attached. The line is green, and its vendor status is `not_on_list`. The demo budget's "Westside Event Rentals" and "Campus Print Shop" lines are also not on Greenlight's copy of the list, and both turn green.
The officer sees green on the exact problem USG lists as a reason to refuse an application.
Smallest fix (UI only, does not change any figure or the test sets): in MoneyCheck.tsx:529,
- open the details when the vendor was not found: `<details open={line.vendor_check.status !== "on_list"} ...>`
- name the status in the summary, for example `Vendor list check: {line.vendor_check.status === "not_on_list" ? "not found on Greenlight's copy of USG's list" : line.vendor_check.status === "no_vendor" ? "no vendor named" : "needs a human look"}`
Risk of fix: safe (one JSX line, display only)
Backend alternative: count the vendor finding in the line verdict when the status is `not_on_list` or `no_vendor`. That is moderate risk: all 19 lines the budgets set expects green use unlisted vendors (for example "Campus Print Shop" and "Trojan Event Services"), so the answer key and several tests would change. Do not do it now.

## Known issues (do not fix now)

1. **The demo script's retreat date does not match the app.** PROJECT_CONTEXT section 11 says the retreat's travel deadline "lands in January". For the seeded retreat (Feb 26–28, 2027), the app gives **Wednesday, November 18, 2026**. That is the 9-week column of the transcribed table (row 2027-02-22), and the 9-calendar-week count lands on December 25, 2026, in winter recess. The app is consistent with its sources. Say "next Wednesday, before the semester even starts" in the pitch, not "January".
2. **A deadline can land on a closed day.** For the demo's welcome mixer (Feb 5, 2027), "Request the venue 3 to 6 weeks ahead" is due Friday, December 25, 2026, in winter recess. It appears third in "This week". Deadlines that fall on a break or holiday are not moved to the last open day before it. The item is yellow ("generally at least 3–6 weeks"), so this is a usability gap, not a wrong red or green. (backend/app/services/deadlines.py `shift`)
3. **The calendar-week count can give an "apply by" date that is not a Wednesday.** `apply_by = min(calendar_count, table_date)` (year_planner.py:240). For an event on a Monday, for example Feb 22, 2027, the count gives Monday, January 11, earlier than the table's Wednesday, January 13. USG applications open only on Wednesdays, and not during breaks. The item is marked "Check with USG", unconfirmed, yellow.
4. **The "nine weeks before the first payment" reading is never dated.** USG's web page also says 9 academic weeks before the initial payment, "whichever comes first" (rule `usg-page-deadline-nine-weeks-payment`). The year plan's "apply by" uses only the 6-week column for vendor events. The packet shows this rule yellow with no date, so nothing is shown as certain. Under the strictest reading, a non-travel event's real deadline could be earlier than the "apply by" date the plan shows (for example, the table's 9-week column says November 11 for the February 1–19 weeks).
5. **One tabling check shows green for less than its quote covers.** `tabling-blocked-days` can be green after checking holidays only. Its quoted text also names Welcome Week, Orientation and football days, which the separate yellow rule `tabling-blocked-university-functions` covers. Both are shown, but a green appears next to a quote that names days Greenlight did not check. Low exposure: tabling is weekdays only, and none of these days falls in spring 2027.
6. **Two eval differences, both in the safe direction.**
   - Events ev-28 (no date given): the engine shows `social-events-not-study-days-finals` as "check with the office" where the answer key expects "condition".
   - Constitution co-09: `clause-viii-a-2` is shown "weak" where the key expects "contradicts".

   Neither is a miss. The answer keys could be updated after the freeze.

## What I checked and found sound

- **Rules against their snapshots (Phase 0, in full).** I read every non-clause rule in funding.json (76), events.json (71), outside_money.json (22) and recognition.json against PROJECT_CONTEXT section 7 and grepped the snapshots for the key numbers:
  - Caps: $35 per person "should not exceed" (equal to $35 passes), $400 per night, $4,000 venue and personnel, "over $4,000" case by case (strictly over), $8,000 a year, 50% fund closure.
  - Deadlines: 6 and 9 academic weeks, 3 business days after the event, 2 business days / 48 hours / 3 business days for an incomplete application, 21 days, 60 days, 2, 3 and 4 weeks, social dance at 3 months, 7 weeks and 5 weeks.
  - Conflicts are listed both ways and resolved to the stricter side: decorations 3 weeks over 2; large-venue cancellation 4 weeks over 3; travel 9 academic weeks before payment over 8 weeks; 48 hours over 2 and 3 business days. The outdoor deposit ($100 vs $200, plan for $200) and parking ("may" vs "will") conflicts are shown too.
  - Direction and anchor are right for each deadline. No "before" rule counts business days, so counting holidays as business days always gives the earlier, safe date.
- **Nothing unverified is encoded as certain.**
  - These rules are marked unverified, with notes: the 4-events-per-semester limit, the academic-week definition, the vendor list, approved caterers and business days.
  - Deadlines counted in academic weeks give no date ("check with USG"); the loader requires them to depend on the definition rule.
  - The FY27 budget figures ($388,000 / $356,100) appear nowhere in the code or rules.
  - The recognition window (Oct 27 to Nov 22, 2026, 11:59 pm, stored as -08:00, correct after daylight saving ends) and the advisor date (Dec 1) match the snapshot.
- **USG deadline table.** The `usg-funding-deadlines.txt` rows are parsed with an overlap check; a weekend is mapped to the Monday row, a blank row to "no deadline" and N/A to "not applicable". Every table date the demo plan shows matches its row: Nov 18 (Feb 1–5 row, 6 weeks), Jan 13 (Feb 22–26 row, 6 weeks), Nov 18 (Feb 22–26 row, 9 weeks), Feb 17 (Apr 5–9 row) and Mar 3 (Apr 19–23 row). The table is always shown as an unconfirmed, yellow "check with USG".
- **calendar.json.** Every date in Fall 2026, Spring 2027 and Summer 2027 is checked against the quoted Registrar text, including weekdays, by `check_against_text`. I re-read the snapshot lines: classes begin Jan 11; MLK Day Jan 18; Presidents' Day Feb 15; spring recess Mar 14–21; classes end Apr 30; study days May 1–4; exams May 5–12; winter recess Dec 17 to Jan 10.
- **Loader guards.** I tested each in a temporary copy of `rules/`. Each of these was rejected with a clear message:
  - a missing `source_url`, `source_text`, `effective_date` or `verified`
  - an empty `source_text`
  - a duplicate id
  - a quote that is not in the snapshot
  - a food cap changed to 40
  - an offset changed to 5, or a direction changed to "before"
  - a "green" severity, or an unknown field
  - "unverified" with no note
  - the 4-event limit re-marked "read" without a quote that states it

  Loading is all or nothing.
- **Dates.** I checked these by hand against the engine:
  - Culture night (Apr 9, 2027): space request Feb 26; final payment Mar 19; approvals and the Department of Public Safety contact Mar 26; cancellation Mar 12 (stricter 4 weeks); evaluation and invoices Apr 14.
  - Retreat: evaluation Mar 3 after a Sunday end.
  - A social dance on Dec 1, 2026: Sep 1, Oct 13, Oct 27.
  - The "move the event" fallback correctly skips Thanksgiving, winter recess, the January block and Presidents' Day (Feb 16).
  - Blocks are red where they should be: spring recess with USG funding; finals with a social event; Jan 20 at a Trojan Event Services venue; alcohol on a Sunday.
  - Jan 28 is in the "confirm" window and shows yellow.
  - Month arithmetic clamps to the month's last day, which is earlier and so safe. Weekend-to-row mapping is correct.
  - The `.ics` file is CRLF, lines at most 75 characters, 40 VEVENTs.
- **Money.** All money is whole-cent integer arithmetic.
  - Demo budget: $38.00 per person, over by $450.00, "at least 163 people" (the ceiling of 5700/35); the DJ fee is red as a performer; tickets are red; the total is $7,070.00; ineligible $800.00; no draft while any red remains.
  - Hotel, yearly-cap and duplicate-line checks read their limits from the rule params.
  - The browser only formats cents (`toCents` and `dollars` are exact).
  - The model's reading never supplies a total: quantity times unit price is computed in code, and the date must be written with its year in the sentence.
- **Year plan (demo).** Total $14,270.00; available $1,500.00; requested $11,250.00, over the cap by $3,250.00; planned from USG exactly $8,000.00 (culture night $5,250.00, retreat $2,400.00, mixer $350.00 partly). The banquet is left out because it is ticketed (red), and the workshop because the cap is used up (red). Club money $1,500.00 goes in date order, leaving a shortfall of $4,770.00. Planned money, club money and shortfall add up to the total, row by row and overall. The 5-events-in-Spring-2027 limit is shown yellow; the strategy plans at most 4 events a semester.
- **Green only where certain.** `Finding` refuses a green on any rule that is unverified, decided by an office, not red, or the less strict side of a conflict, and refuses a red on a rule shown yellow. Green findings are only date checks on certain rules (with partial checks excluded) and money passes. Apart from the two must-fix items, I found no green the rule table cannot back.
- **Exit criteria, phases 1–6, as far as code and test sets show them.**
  - Recognition: 21/21 planted faults found; no missing clause shown present.
  - Events: 30/30 obligation lists match; nothing silently missing; every conflict list matches.
  - Budgets: 30/30 violations found, 0 wrong greens in the answer key, fund right or yellow in 20/20, totals exact.
  - Year plans: 2/2 match.
  - The gap helper's options come from a fixed list in code.
  - The `.ics` file is well formed.
  - Checking the live link, phone layout and keyboard use is outside this lens.
