# Phase 0, iteration 4 — audit
Scope: auditor (a), `rules/funding.json` against its sources, and the expected answers that rest on it (`data/eval/budgets/`, the USG obligations in `data/eval/events/` and `data/eval/year_plans/`). Commit `f65afcc`.
Summary: 1 blocker, 2 high, 5 medium, 6 low.

How I checked: I read all 75 rules in `rules/funding.json` next to `rules/sources/usg-funding-guidelines.txt`, `usg-funding-page.txt`, `usg-funding-faq.txt`, `usg-funding-deadlines.txt`, `usg-vendor-list.txt` and `usg-vendor-list-other.txt`. I also ran my own check, separate from the loader: each rule's `source_text`, whitespace-collapsed and NFC-normalised, against its snapshot body, and each `effective_date` against the manifest `version_date`. All 75 quotes are found, including the 2 unverified rules, and every date matches. I grepped the raw downloads for the passages that carry the numbers: page "and or nine academic weeks … (whichever comes first)" and "up to 4 events", FAQ "eight weeks prior to the date of travel", "Can I apply for summer event funding?" and "three business days to provide". All are present. I recomputed every USG due date in the event and year-plan keys by hand: the post-event business-day dates are all correct, and the arithmetic of the FAQ 8-week dates is correct. I also re-checked every budget sum and per-person figure. `python scripts/validate_rules.py` gives OK (funding 75, read 280, unverified 5). `python scripts/run_eval.py` reports all four sets valid. `pytest` gives 266 passed. The only file I changed is this report.

## Iteration 3 findings: what was fixed
| Iter-3 item | Status | Evidence |
|---|---|---|
| H1 page 9-week clause | Fixed in part | New rule `usg-page-deadline-nine-weeks-payment` (funding.json:113-147), linked both ways through `whichever_first_rules`. It does not record its conflict with `usg-deadline-vendor` (M1 below). |
| H2 summer | Fixed in part | `usg-faq-no-summer-funding` (364-394), yellow. Its period names are defined nowhere (L2). |
| M1 FAQ 3 business days | Fixed | `usg-faq-incomplete-three-business-days` (807-838), conflicts listed in both directions. The eval test pins "shorter is stricter". |
| M2 FAQ Professional travel | Fixed in part | Two new rules (243-304). "No written appeal process" was removed. The new deadline rule brings the blocker and H1 below. |
| M3 one conflict policy | Fixed in part | The messages now say "earliest". The event keys still apply `usg-deadline-travel` (M3 below). |
| M4 submissions during breaks | Fixed | `also_blocks_submissions` (356) and new message wording. |
| M5 eligibility | Fixed, no test | `usg-faq-eligibility` (495-521). No test or test data names it (M5 below). |
| M6 venue cap | Fixed | Check at l.881, note at l.894, `test_venue_cap_checks_what_usg_is_asked_to_pay`. |
| M7 alcohol | Fixed | Trigger `alcoholic_drinks` (1495-1497), plus a test. |
| M8 buses | Fixed in part | Vocabulary l.67 changed, and the rideshare message notes the conflict. ev-21 still has no bus finding (M4 below). |
| L1-L13 | Mostly open | See L1 below. |
| Test gap (USG anchors) | Fixed in part | `test_usg_deadline_rules_pin_their_anchors_and_offsets` covers 5 rules. It leaves out the new FAQ 8-week rule and the three incomplete-application rules. |

## Rule check
| Rule id | Matches source? | Note |
|---|---|---|
| usg-academic-week-definition | Yes (unverified) | Guidelines l.41. Yellow is correct. `rows_to_confirm` covers the doubtful rows of the transcribed table. |
| usg-deadline-vendor | Yes | Guidelines l.36: 6 academic weeks before the initial payment. "Denied automatically" in the message comes from l.39 (L1). No conflict is recorded with the page's 9-week rule (M1). |
| usg-page-deadline-event-date | Yes | Page l.49. 6 academic weeks before the event date. The message now credits "whichever comes first" to the page. |
| usg-page-deadline-nine-weeks-payment | Yes | Page l.49: 9 academic weeks before the payment. The reading of the garbled sentence is stated in notes. `conflicts_with` is null although the rule disagrees with `usg-deadline-vendor` on the same anchor (M1). |
| usg-deadline-travel | Yes | Guidelines l.38: 9 academic weeks before the payment, covering airfare, ground transport and overnight hotels. Notes follow the earliest-date policy. |
| usg-faq-deadline-new-vendors-travel | Yes | FAQ l.26: 8 academic weeks before the event. The message follows the earliest-date policy. The keys contradict it (M3). |
| usg-missed-deadline-denial | Yes | Guidelines l.39. The message now gives the FAQ discretion and no longer claims there is no appeal. |
| usg-faq-professional-travel-eight-weeks | Text yes; encoding no | FAQ l.70 says "eight weeks prior to the **date of travel**", "(airfare and hotel)", Professional/Academic Fund only. The rule counts from `event_date` and triggers on any `travel` (ground included). Its plain-week dates fall on non-Wednesdays and in recess, and are shown as certain (blocker, H1). The FAQ's "four week deadline" is not recorded (L4). |
| usg-faq-late-travel-director-discretion | Yes | FAQ l.70. `office_decides` is correct. Its triggers are narrower than its sibling rule's (L4). |
| usg-application-window | Yes | Guidelines l.35. "Money is given first come, first served" is still in the message (L1). FAQ #5's 8:00 AM opening is not recorded. |
| usg-no-funding-breaks | Yes | Guidelines l.40. Both events and submissions are covered. Certain, because it rests on the confirmed calendar. |
| usg-faq-no-summer-funding | Yes | FAQ l.19-20 (question and answer). Yellow with a stated reading. The params name periods the calendar does not define (L2). |
| usg-post-event-evaluation | Yes | Guidelines l.42: 3 business days after the last day. Agrees with FAQ #12. Yellow through the business-day definition. |
| usg-post-event-photos | Yes | Guidelines l.43. |
| usg-final-invoices | Yes | Guidelines l.44. The message softens l.45's "will result in" to "can lead to" (L1). FAQ #13's consequence is not recorded. |
| usg-funding-modules | Yes | Guidelines l.47. `info`, with FAQ #2 now carried by the next rule. |
| usg-faq-eligibility | Yes | FAQ l.12. Red. "This year" stands in for "re-recognition", a fair reading. No test covers it (M5). |
| usg-quote-required | Yes | Guidelines l.53. Agrees with FAQ #11. |
| usg-cart-screenshot | Yes | Guidelines l.54. |
| usg-amazon-wishlist | Yes | Guidelines l.55. |
| usg-traveler-information | Yes | Guidelines l.57. All six fields are listed. The message says the details are not stored. |
| usg-hotel-point-of-contact | Yes | Guidelines l.58. |
| usg-travel-statement-of-purpose | Yes | Guidelines l.60. |
| usg-conference-logins | Yes | Guidelines l.61. There is still no "not stored" statement for credentials (L1). |
| usg-esr-on-campus | Yes | Guidelines l.62. `venue_classroom` is still not a trigger (L1). |
| usg-hospitality-food-form | Yes (text) | Guidelines l.63 is a sub-bullet of on-campus ESRs. The trigger `food` also fires off campus (L1). |
| usg-uepa-event-id | Yes | Guidelines l.64. Yellow fits "if applicable". |
| usg-incomplete-two-business-days | Yes | Guidelines l.65. Conflicts with the 48-hour and FAQ 3-day rules are listed in both directions. |
| usg-incomplete-48-hours | Yes | Guidelines l.67. 48 hours is never later than 2 business days, so it is correctly the one applied. |
| usg-faq-incomplete-three-business-days | Yes | FAQ l.40: offset 3, business_days, after the notice. Depends on the business-day definition. |
| usg-yearly-cap | Yes | Guidelines l.78: $8,000. The check text still sums "usg_funding_this_year" (L1). The year-plan validator uses received plus requested, which is correct. |
| usg-venue-personnel-cap | Yes | Guidelines l.79: $4,000 of what USG is asked to pay. The per-event versus per-year question is noted. |
| usg-over-4000-case-by-case | Yes | Guidelines l.80. `office_decides`. |
| usg-multi-day-case-by-case | Yes | Guidelines l.81. `office_decides`. |
| usg-fund-closure | Yes | Guidelines l.82: 50%, and "may". |
| usg-events-per-semester-cap | Yes (unverified) | Page l.47. Shown yellow. The FAQ document (#4) does not mention the limit. |
| usg-fund-professional-academic | Yes | Guidelines l.84. |
| usg-professional-free-open | Yes | Guidelines l.89. |
| usg-fund-philanthropy | Yes | Guidelines l.93. |
| usg-philanthropy-no-service-payments | Yes | Guidelines l.96. |
| usg-fund-social-recreation-startup | Yes | Guidelines l.98. |
| usg-tshirts-licensed-vendor | Yes | Guidelines l.102. |
| usg-fund-performing-visual-arts | Yes | Guidelines l.105. |
| usg-pva-po-vendor | Yes | Guidelines l.107. |
| usg-food-case-by-case | Yes | Guidelines l.112. `office_decides`, but the budget keys never expect it (H2). |
| usg-food-justification | Yes | Guidelines l.113. |
| usg-food-health-permit-insurance | Yes | Guidelines l.114. |
| usg-food-cap | Yes | Guidelines l.115: $35 per person, expected attendance. The fix still suggests raising headcount (L1). |
| usg-lodging-case-by-case | Yes | Guidelines l.116. `office_decides`, but the budget keys never expect it (H2). |
| usg-hotel-price-comparison | Yes | Guidelines l.117. The fix says "at least one other hotel" (L1). |
| usg-hotel-cap | Yes | Guidelines l.119: $400 per night. |
| usg-lodging-justification | Yes | Guidelines l.120. |
| usg-approved-vendor | Yes | Guidelines l.37. Yellow through `usg-vendor-list`. "The stricter" is correct here. |
| usg-vendor-list | Text present (unverified) | Vendor list l.11. The quote is still the PO-registration note, which does not support the message (L1). |
| usg-ineligible-reimbursements | Yes | Guidelines l.123-142. The exception note matches l.142. |
| usg-ineligible-charity | Yes | |
| usg-ineligible-alcohol | Yes | Line category only, which is fixed. |
| usg-ineligible-gifts | Yes | |
| usg-ineligible-durable-goods | Yes | |
| usg-ineligible-raw-food | Yes | |
| usg-ineligible-restaurant | Yes | "Restaurant diners" is quoted exactly as written. |
| usg-ineligible-rideshare | Yes | Red with a note about the bus conflict, as PROJECT_CONTEXT section 7 asks. |
| usg-ineligible-deposits-fees | Yes | |
| usg-ineligible-peer-to-peer | Yes | |
| usg-ineligible-performers | Yes (text) | Vocabulary still counts "speakers' fees" as talent (L1). |
| usg-ineligible-subscriptions | Yes | |
| usg-ineligible-ticketed-events | Yes | |
| usg-ineligible-closed-on-campus-events | Yes | |
| usg-ineligible-private-residences | Yes | |
| usg-ineligible-international-travel | Yes | |
| usg-ineligible-jewelry | Yes | |
| usg-ineligible-balloons | Yes | |
| usg-denial-reasons | Yes | Guidelines l.148-153. "Never predicts a decision." |
| usg-denial-same-day-events | Yes | Guidelines l.151. Yellow. |
| usg-denial-other-university-funding | Yes | Guidelines l.152. Yellow. Triggers on every USG application (L3). |

## Findings

### [blocker] B1. The FAQ's 8-week travel deadline gives certain dates on which USG accepts no applications
Where: rules/funding.json:243-276 (`usg-faq-professional-travel-eight-weeks`: anchor l.269, unit `weeks` l.271, no `depends_on`); data/eval/events/cases.json:2493-2499 (ev-20, due `2027-01-07`), :2648-2654 (ev-21, due `2027-02-13`); data/eval/year_plans/cases.json:391-395 (yp-01 retreat, due `2027-01-01`); backend/app/eval_sets.py:93-102 and backend/tests/unit/test_eval_sets.py:70-79 (both require due = event date minus 8 weeks exactly); sources rules/sources/usg-funding-faq.txt:70, usg-funding-guidelines.txt:35, 40
Problem: This is the only USG pre-event deadline with a computable date that rests on nothing unverified, so it is shown as a certain red `to_do`. The date is the event date minus 56 days, with no adjustment:
- ev-20 gives Thursday 2027-01-07 and yp-01 gives Friday 2027-01-01. Both fall inside Winter Recess (rules/calendar.json:119-125). USG "does not process applications … during University holidays, breaks, study days, or finals" (guidelines l.40). The rule table encodes this itself as `also_blocks_submissions: true` (funding.json:356). Applications open only on Wednesdays (guidelines l.35). The last Wednesday USG processes applications before either date is 2026-12-02: study days and exams cover Dec 5-16, and recess runs to Jan 10.
- ev-21 gives Saturday 2027-02-13. The last Wednesday on or before it is 2027-02-10.
- The FAQ counts from "the date of travel" (l.70). The rule counts from `event_date`. Travel that starts the day before the event, which is usual for a conference, gets a date one day too late.

The validator and `test_event_due_dates_agree_with_rule_lead_times` require the plain subtraction. A correct engine that moves the date back to the last open Wednesday would therefore be scored as wrong.
Why it matters: For yp-01 the officer would be told, as certain, "apply by January 1, 2027". USG takes nothing between December 2 and January 13. Every other date for that trip has no value (academic weeks) or is yellow, so this certain date is the one the officer would act on. This is a wrong date shown as certain.
Suggested fix:
- Give the rule `depends_on: ["usc-academic-calendar-2026-27"]`.
- Record in params (and in the method for the test sets) that USG submission deadlines move back to the last Wednesday that is not a holiday, break, study day or finals day.
- Make the eval validator and the test apply that rule. Correct the three due dates: ev-20 → 2026-12-02, yp-01 → 2026-12-02, ev-21 → 2027-02-10. Check against the calendar.
- Either add a `travel_date` anchor, or note that `event_date` is used for the travel date and mark the result yellow when travel starts earlier. Add a regression test that fails for a deadline landing on a non-Wednesday or in a blocked period.

### [high] H1. The FAQ Professional-Fund travel deadline is applied to trips outside its fund and outside "airfare and hotel"
Where: rules/funding.json:258-268 (triggers `travel`, `lodging`, `airfare`; the fund limit is only in `params.fund_rules`); data/eval/events/cases.json:2548-2549 and 2648-2654 (ev-21: a Philanthropy-type service trip by charter bus); data/eval/year_plans/cases.json:391-395 (yp-01: a cultural club's social retreat to Big Bear, reached by road); backend/tests/unit/test_eval_sets.py:35-55 (obligations must equal trigger matches, ignoring `fund_rules`)
Problem: The source limits this deadline to the Professional and Academic Fund and to "(airfare and hotel)". The `travel` trigger covers ground transport too (vocabulary l.34). The trigger-agreement test forces every travel event to list the rule, whatever its fund. The events set has no fund field to exclude it. So ev-21 (bus, no hotel, service trip) and yp-01 (social retreat) expect a certain red deadline from a rule that does not apply to them.
Why it matters: The answer key rewards an engine that shows Professional-Fund deadlines on Philanthropy and Social trips as certain. Those are dates the source does not give.
Suggested fix: Drop the `travel` trigger and keep `airfare` and `lodging`. Make the trigger-agreement test honour `params.fund_rules`, or list such rules as `check_with_office` with a note when the fund is not known. Remove the entry from ev-21 and from the yp-01 retreat, or mark it `check_with_office` with "applies only to the Professional/Academic Research Fund".

### [high] H2. Budget keys show food and hotel lines green, though USG reviews every food and lodging request case by case
Where: rules/funding.json:1194-1213 (`usg-food-case-by-case`, `office_decides`, trigger `food`), 1283-1302 (`usg-lodging-case-by-case`, `office_decides`, trigger `lodging`); data/eval/README.md:41 ("Expected findings list every red and office-decides finding"); data/eval/budgets/cases.json: bu-02 line 1 (from l.149), bu-04 line 1 (l.307), bu-06 line 1 (l.489), bu-09 line 1 (l.749), bu-12 line 1 (l.1147), bu-13 line 1 (l.1247), bu-15 line 3 (l.1408), bu-17 line 1 (l.1575)
Problem: No budget case lists either case-by-case finding, although food or lodging lines appear in 12 of the 20 cases. Eight food or lodging lines are expected `green`. Other discretionary rules are listed (`usg-over-4000-case-by-case`, `usg-multi-day-case-by-case`), so this omission is not a deliberate policy.
Why it matters: PROJECT_CONTEXT section 9 says discretionary rules are shown as "the office decides", never green. The key scores a green food line as correct and would score the correct office-decides verdict as a wrong flag.
Suggested fix: Add the `office_decides` finding to every food and lodging line, or at application level, and set those line verdicts to `office_decides`. Add a validator check: every budget line whose category triggers an `office_decides` rule carries that finding.

### [medium] M1. The page's 9-weeks-before-payment rule does not record its conflict with the guidelines' 6-weeks-before-payment rule
Where: rules/funding.json:142 (`conflicts_with: null`), 69-71 (`usg-deadline-vendor` lists only the event-date page rule); backend/tests/unit/test_rules_loader.py:415
Problem: Both rules count back from `initial_payment_due_date`, one by 6 academic weeks and one by 9. This is the most direct disagreement among the USG sources, and the iteration 3 fix asked for "mutual conflicts". Because the pair is not recorded, `_check_conflicts` (eval_sets.py:160-188) never requires the keys to name it, or to apply the 9-week rule, which would be the stricter here.
Why it matters: The README says a disagreement is applied stricter and both are shown, and `conflicts_with` is how that happens. A later engine that resolves conflicts from this field will miss the strongest one.
Suggested fix: List the two rules in each other's `conflicts_with`. Add the pair to each event and year-plan key that lists both rules, with `applied: usg-page-deadline-nine-weeks-payment`. Pin it in the loader test.

### [medium] M2. Year-plan notes quote November 18 when the encoded 9-week reading gives November 11, already past
Where: data/eval/year_plans/cases.json:811 (yp-01 welcome mixer, Feb 5) and :1687 (yp-02 speaker series and resume workshop, Feb 3); rules/sources/usg-funding-deadlines.txt:32-33 (event weeks Feb 1 and Feb 8: 9-week column `2026-11-11`); rules/funding.json:25 (`date_to_row`: "the initial payment due date is looked up the same way and the earlier deadline applies")
Problem: The notes give the table's 6-week date (Wednesday, November 18, 2026). Under `usg-page-deadline-nine-weeks-payment` and the stated earliest-date policy, a payment due on or before an event in the week of Feb 1 gives the table's 9-week date, 2026-11-11. That is four days before the cases' `as_of` (2026-11-15).
Why it matters: The key tells the planner the deadline is three days away when, on the rule table's own reading, it may already have passed. The status is yellow, but the key misses a "may already be too late, ask USG now" problem.
Suggested fix: State both table dates in the notes. Add a yellow "deadline may have passed" problem for those three events, citing both page rules.

### [medium] M3. Event keys apply the guidelines' travel deadline, against the earliest-date policy
Where: data/eval/events/cases.json:2521 (ev-20) and :2684 (ev-21) (`"applied": "usg-deadline-travel"` for the pair with `usg-faq-deadline-new-vendors-travel`); rules/funding.json:182, 197 ("shows the earliest")
Problem: One rule counts 9 academic weeks back from the first payment; the other counts 8 academic weeks back from the event. Which is earlier depends on the payment date, which neither case gives. The other pairs with different anchors in these keys use `applied: null`. The validator does not catch this, because it cannot decide the stricter when the anchors differ.
Why it matters: The key still encodes "the guidelines win", the policy iteration 3 (M3) asked to remove. It contradicts the message the officer is shown.
Suggested fix: Set `applied: null` for this pair in ev-20 and ev-21. Have the validator require `null` when two conflicting deadlines have different anchors and no due dates.

### [medium] M4. ev-21 does not flag the charter bus USG is asked to pay for
Where: data/eval/events/cases.json:2549 ("asking USG to pay for the charter bus"), attributes at :2557-2561; rules/funding.json:1604-1627 (`usg-ineligible-rideshare`, "Buses"); rules/vocabulary.json:67-68
Problem: The attributes are `travel`, `international_travel` and `usg_funding`. `rideshare`, which the vocabulary now uses for buses, is not among them, so the bus ineligibility is missing. The verdict is still blocked because of international travel, but one of the two reasons is gone.
Why it matters: The vocabulary change was made to fix iteration 3's M8. The one event that names a bus does not use it, so the event set never checks it.
Suggested fix: Add `rideshare` to ev-21's attributes and the `usg-ineligible-rideshare` obligation (blocked, violated, with a note on the bus conflict).

### [medium] M5. Some iteration-3 fixes have no test that fails if they are undone
Where: rules/funding.json:495-521 (`usg-faq-eligibility`: no test or test data names it); backend/tests/unit/test_rules_loader.py:401-416 (does not pin `usg-faq-professional-travel-eight-weeks` (event_date, 8, weeks), the three incomplete-application rules, or the rideshare and bus vocabulary)
Problem: Deleting `usg-faq-eligibility`, or changing the FAQ travel rule to 9 weeks or another anchor, would leave all 266 tests green. The FAQ travel rule's `offset` is checked against the quoted text (the number "eight"), but its anchor and unit are not checked.
Why it matters: CLAUDE.md: "Every bug fix comes with a test that fails before the fix."
Suggested fix: Add these rules to the anchor and offset table test, and add one test that asserts the eligibility rule exists, is red and triggers on `usg_funding`.

### [low] L1. Iteration-3 lows still open
Where and what:
- funding.json:58 ("denied automatically", from l.39, not this rule's quote).
- :458 ("can lead to", where the source says "will result in", from the unquoted l.45).
- :318 ("Money is given first come, first served").
- :1270 ("plan for at least {min_headcount} people").
- :1317 ("at least one other hotel").
- :671 (log-in credentials, with no "not stored" statement; guidelines l.88 calls them "credentials").
- :718-720 (hospitality form fires off campus).
- vocabulary.json:65 (speakers' fees counted as talent).
- funding.json:855 (yearly-cap check wording).
- :1411 and :1417 (vendor-list quote does not support the message; the Purchasing phone number comes from the TES FAQ).
- rules/README.md:34 (`conflicts_with` defined as "another source", yet same-source pairs are encoded).
- FAQ↔`usg-deadline-vendor` pair not listed.
- :695-699 (no `venue_classroom` for ESR).
- Unencoded FAQ items: #5 opens at 8:00 AM; #13 invoice trouble means future denial; the durable-good definition.
Suggested fix: As in iteration 3's report.

### [low] L2. The summer rule names periods nothing defines, and adds a yellow item to every spring event
Where: rules/funding.json:383-388 (`blocked: ["summer", "between_semesters"]`); rules/calendar.json (no such names; summer-2027 is a term; there are no gaps between terms and no Fall 2027 term); every USG event in the event and year-plan keys lists `usg-faq-no-summer-funding` as `check_with_office`
Problem: No code or test maps these names to dates, so the iteration-3 H2 fix depends on a later engine interpreting them. Because the rule's severity is yellow, every spring event also gets a "check with the office" item for a rule it clearly meets.
Suggested fix: Define the periods in calendar.json, or in params as date ranges, and have the loader check the names. Give the rule a definite applies/does-not-apply test (event date outside the fall and spring terms), so spring events show nothing.

### [low] L3. The "other University funding" denial note fires on every USG application
Where: rules/funding.json:1937-1939 (triggers `usg_funding`); rules/vocabulary.json:101 (`other_usc_funding` exists)
Problem: Every USG request gets a yellow "Ask USG before using {other_source}", and the placeholder cannot be filled when there is no other source.
Suggested fix: `trigger_mode: "all"` with `usg_funding` and `other_usc_funding`.

### [low] L4. The FAQ's "four week deadline" is not recorded, and the two FAQ travel rules trigger differently
Where: rules/funding.json:252 and 286 (FAQ l.70 mentions both "eight weeks … (airfare and hotel)" and "this four week deadline, or eight week deadline in the event of air travel"); triggers at 259-263 versus 293-295
Problem: The FAQ contradicts itself (hotel 4 or 8 weeks). The rule takes the stricter 8 weeks without noting the contradiction. The discretion rule triggers only on `travel`; the deadline rule triggers on `travel`, `lodging` and `airfare`.
Suggested fix: Add a note about the 4-week clause. Give both rules the same (narrowed) triggers.

### [low] L5. The eval validator does not recompute deadlines counted after the event
Where: backend/app/eval_sets.py:93-102 (only `direction == "before"` is recomputed); backend/tests/unit/test_eval_sets.py:75
Problem: Every post-event evaluation and invoice date (14 checked by hand) is correct today, but a wrong one would pass validation.
Suggested fix: Count business days forward for `after` rules anchored on `event_end_date` (or on `event_date` when there is no end date).

### [low] L6. "Coach seats" in `ground_transport` overlaps "Buses"
Where: rules/vocabulary.json:67
Problem: A coach seat on an intercity bus is a bus fare, which guidelines l.131 lists as ineligible. A train-coach seat is eligible as "ground" travel (l.38). The vocabulary does not separate the two.
Suggested fix: "Train seats (not Amtrak cabins)". Send any bus fare to `rideshare`.
