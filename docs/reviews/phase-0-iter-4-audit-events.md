# Phase 0, iteration 4 — audit
Auditor (b): `rules/events.json` against its sources, and the event and year-plan answers that rest on it. Commit `f65afcc`.
Summary: 0 blockers, 1 high, 2 medium, 13 low.

Commands run, from the repo root with `backend/.venv` active: `python scripts/validate_rules.py` (285 rules, 69 in events; "Every rule marked 'read' matches its snapshot text exactly"); `python scripts/run_eval.py` (all four sets valid); `cd backend && pytest` (266 passed). No file other than this report was changed. `docs/PROGRESS.md` was not used as evidence.

Method: I compared every `source_text` in `rules/events.json` by hand with the passage around it in `rules/sources/` (tes-terms.txt, tes-faq.txt, tes-tabling.txt, rso-resources.txt, social-dance.txt, student-handbook.txt, usc-academic-calendar.txt, and tes-forms.txt for the permit names). For each rule I checked the number, the unit, the anchor, the direction, who and which venues it covers (triggers against `rules/vocabulary.json`), its kind and severity, its params including `violated_when`, and whether its message and fix are supported by the quoted text. I then checked all 30 event cases and both year plans against the rules and the validator in `backend/app/eval_sets.py`, and checked the 18 findings from `phase-0-iter-3-audit-events.md`.

What is right: every passage is in its snapshot and is the right passage. Every lead time, unit, anchor and direction matches its source. Every recorded conflict is listed both ways and the eval applies the stricter side (decorations: Terms and Conditions 3 weeks; large-venue cancellation: FAQ 4 weeks; deposits $100/$200; parking may/will). Each weekday named in an eval sentence matches its date. Each dated obligation in the eval equals the event date minus the rule's own lead time. Of the iteration-3 findings, these are really fixed: H1 (Sterno no longer gets the red ban), M1, M2, M3 (the loader now rejects `{due_date}` on a non-deadline rule, loader.py:205-206), M6 and M7 in the data, L2 and L6. M4 and M5 are only partly fixed (see the high finding and M1 below). L1, L3, L4, L5, L7, L8, L9 and L10 are unchanged.

## Rule check
| Rule id | Matches source? | Note |
|---|---|---|
| usc-academic-calendar-2026-27 | Yes | usc-academic-calendar.txt. `source_text` still covers only Spring 2027; the notes name a different URL from `source_url` (L9). |
| usc-business-days-definition | Yes (unverified, correct) | Yellow. Calendar `business_days` carries the same mark. |
| tes-space-request | Yes | Handbook App. V, "generally at least 3-6 weeks". Uses 6 weeks, yellow. `range_quote` is in the text. |
| tes-spring-booking-opens | Yes | tes-faq.txt:16. Info. |
| tes-no-events-first-three-weeks | Yes | tes-faq.txt:16. Blocked through Jan 26, Jan 27-31 yellow. The data has no start date (L6). |
| uepa-required | Yes | Handbook App. V. The fix's "2 weeks" claim also reaches classroom events, where no cited rule says it (L2). |
| approvals-two-weeks | Yes | T&C A.6, 2 weeks, red. |
| uepa-late-exception | Yes | 48 hours typical; office decides. |
| dps-security | Yes | T&C A.6.i, 2 weeks; office decides with a contact-by date. |
| security-determined-by-dps | Yes | Handbook App. V "Security". |
| tes-final-payment | Yes | T&C C.3.viii, 21 days. The message goes beyond the quote (L2); meeting rooms are left out though the source says "For all venues" (L8). |
| tes-rso-deposits | Yes | T&C C.3.v-vii. Conflict with C.2.iii is recorded both ways. The message still gives $100 without mentioning $200 (L3). |
| tes-outdoor-deposit-section-c2 | Yes | T&C C.2.iii, $200 for Student Organizations. Conflict listed both ways; depends on the business-day rule. |
| tes-av-equipment | Yes | T&C B.1, 3 weeks. |
| tes-decorations-terms | Yes | T&C B.4, 3 weeks; conflict both ways; applied in ev-27. |
| tes-decorations-faq | Yes | tes-faq.txt:107, 2 weeks; conflict both ways. |
| tes-decorations-prohibited | Yes | FAQ list, same as T&C B.4.i; `violated_when: prohibited_decoration`. |
| tes-room-configuration | Yes | T&C B.6, 2 weeks, yellow. The message's "later changes ... fees" is outside the quote (L2). |
| tes-outside-rentals | Yes | T&C R, 3 weeks. |
| fms-tables-chairs | Yes | tes-faq.txt:95, 2 weeks. |
| classroom-requests-week-4 | Yes | rso-resources.txt:29. Now yellow. How Week 4 is counted is not written in the rule (L10). |
| tes-cancellation-meeting-rooms | Yes | T&C D.1.ii, 2 weeks; the FAQ agrees. "In writing" comes from D.1.i, outside the quote (L2). |
| tes-cancellation-large-terms | Yes | T&C D.1.iii, 3 weeks; conflict both ways. |
| tes-cancellation-large-faq | Yes | tes-faq.txt:38, 4 weeks; conflict both ways; stricter. |
| social-events-not-study-days-finals | Yes | Handbook App. V; depends on the calendar. |
| social-event-hours | Yes | Midnight Sun-Thu, 2 a.m. Fri-Sat, no alcohol. |
| social-dance-start | Yes | social-dance.txt:13, 3 months. The document is dated 9/2023 (L5). Months arithmetic differs between test and validator (L11). |
| social-dance-events-meeting | Yes | Step 4, 7 weeks. |
| social-dance-form | Yes | 5 weeks; the hold is removed. |
| alcohol-register-campus-activities | Yes | Handbook p.117. |
| alcohol-not-at-dances | Yes | `all` on alcohol and social_dance. |
| alcohol-thursday-saturday | Yes | The source says "served by the host organization"; the `alcohol` trigger also covers alcohol that is only present (L8). |
| alcohol-requirements | Yes | Bullet list, verbatim. |
| alcohol-no-sales | Text yes; scope too narrow | Fires only with `ticket_sales`. Selling drinks, cups or required donations at an alcohol event is not caught (M1). |
| alcohol-end-times | Yes | 12:00 a.m. Thursday, 2:00 a.m. Friday/Saturday. |
| alcohol-not-main-focus | Yes | `violated_when: alcohol_is_main_focus`. |
| alcohol-uepa-two-weeks | Yes | 2 weeks. |
| minors-registration | Yes | tes-faq.txt:49-53, 60 days. |
| lafd-division-5-permit | Yes | tes-faq.txt:42-44. The canned-heat example in the message is not in the quote; any tent fires it (L4, L8). |
| no-candles-flames | Yes | Narrowed to `candles`. The FAQ's own conflict (no flames vs a permit for open flame) is explained in notes, not recorded (L4). |
| sterno-guidelines | Yes | tes-faq.txt:114. Office decides. Also fires for a grill with a Sterno-only message (L4). |
| props-approval | Yes | 2 weeks. "Photos", "non-metallic", "no weapons" are outside the quote (L2). |
| high-risk-waivers | Yes | Red; whether an activity counts as "medium" risk is the office's call (L7). |
| special-event-insurance | Yes | Office decides. The message's list of co-sponsors, vendors and so on is outside the quote (L2). |
| food-approved-provider | Yes | T&C K; depends on the unverified caterer rule, so yellow. |
| usc-approved-caterers | Yes (unverified, correct) | Phone check only. |
| amplified-sound-register | Yes | Handbook App. V. |
| amplified-sound-90-dba | Yes | 90 dBA at 45 ft. |
| amplified-sound-outdoor | Yes | tes-faq.txt:87; office decides. |
| amplified-sound-hahn-plaza | Yes | T&C F.2; kind `info` with severity `office_decides`. |
| fundraising-meeting | Yes | Handbook Process a., 2 weeks; RSO Resources agrees. |
| fundraising-form-tes | Yes | T&C P.ii. |
| cash-collection-approval | Yes | T&C O.3 "at the event"; the `ticket_sales` trigger is broader (L8). |
| item-sales-bookstore | Yes | Handbook b.i. |
| charity-collection-letter | Yes | Handbook "Non-Profit Collections", 2 weeks. |
| cosponsors-named-in-uepa | Yes | Handbook "RSO Co-Sponsorship". |
| campus-filming | Yes | T&C A.6.viii. The phone number is gone (L2 fixed). The trigger leaves out "photographed" (L8). |
| dignitaries-clearance | Yes | T&C A.6.vi. |
| parking-transportation | Yes | T&C A.6.iii "may require"; conflict both ways. |
| parking-reservation-required | Yes | T&C M "will require"; red; stricter. |
| fpm-outdoor-electrical | Yes | T&C A.6.iv. Indoor "special electrical or custodial needs" has no trigger (L8). |
| advertising-after-confirmation | Yes | Handbook App. V. |
| advertising-no-outstanding-approvals | Yes | T&C I. |
| tabling-permit | Yes | tes-tabling.txt:15. The SKS desk and "displayed" are outside the quote (L2). |
| tabling-fundraising-uepa | Yes | tes-tabling.txt:18. Item, ticket and cash sales at a table do not fire it (L1). |
| tabling-blocked-days | Text yes; certainty wrong | tes-tabling.txt:16. Red and certain, but Greenlight has no dates for 3 of the 4 blocks the text names (H1). |
| tes-no-outdoor-football-days | Yes | tes-faq.txt:72. Info only, because Greenlight has no football schedule. Acceptable for a spring plan. |
| tabling-hours | Yes | 10-2, Monday-Friday. |
| tabling-limits | Yes | `max_days_per_week: 2`, the days must be consecutive, `max_days_per_month: 6` (M7 fixed). |

## Findings

### [high] H1. The tabling blackout rule is marked certain, but Greenlight cannot check Welcome Week, Orientation, football days or Trousdale-wide reservations; the eval records a certain pass
Where: rules/events.json:1648-1672 (`tabling-blocked-days`: `verified: read` at :1659, `severity: red` at :1660, `depends_on: ["usc-academic-calendar-2026-27"]` at :1668-1670, notes at :1671); rules/sources/tes-tabling.txt:16; data/eval/events/cases.json:1141 (ev-09) and :4000 (ev-30), both `status: "condition"`; backend/app/eval_sets.py:78-88 (`_expected_status`).
Problem: The source blocks tabling "during official university functions or holidays including but not limited to Welcome Week, Orientation, and home football game days, or when there is a reservation that is using all of Trousdale. For example, a Career Fair." Greenlight's data holds only the holidays (rules/calendar.json). The rule's own note admits that the other dates "are not in Greenlight's data, so the officer checks those dates with Trojan Event Services". Even so, the rule is `read`, red, and depends only on the calendar, which is `read`, so `is_certain` is true (loader.py:78-81). Code can therefore only say "not a holiday, so the rule is met", and the display severity stays red/certain rather than yellow. The test set fixes that outcome: ev-09 (Wednesday, February 10, 2027) and ev-30 (Wednesday, February 3, 2027) expect `condition`, meaning "as described it keeps to the rule". The validator also rejects `check_with_office` for this rule unless a note is attached (eval_sets.py:105-108). Early-February Trousdale-wide events such as career fairs are exactly the case the source names.
Why it matters: A date check the code cannot do is presented as done. The officer is told the tabling day is fine, with certainty, when Greenlight never looked at three of the four reasons it could be blocked. That breaks "nothing unverified is presented as certain" and "never guesses green".
Suggested fix: Split the rule. (a) A holiday rule that is red and certain, checked against calendar.json holidays. (b) A rule for university functions and Trousdale-wide reservations that is `unverified`, or depends on a new unverified "university functions calendar" rule, so it shows yellow: "check this date with Trojan Event Services". Change ev-09 and ev-30 so the second rule is `check_with_office`. Add a regression test that `ruleset.display_severity(...)` is yellow for the functions rule. The existing regression test (backend/tests/unit/test_rules_loader.py:462-463) only checks that the rule exists.

### [medium] M1. The alcohol sales ban fires only on ticket sales; selling drinks, cups or required donations at an alcohol event is not caught
Where: rules/events.json:887-912 (`alcohol-no-sales`: `applies_to` at :902 says "sells tickets or collects money"; `triggers: ["alcohol", "ticket_sales"]`, `trigger_mode: "all"` at :903-907; `violated_when: "ticket_sales"` at :909); rules/sources/student-handbook.txt:5161-5165; tes-terms.txt:440-443.
Problem: The source bans selling alcohol "either directly or indirectly ... This includes selling cups, mixes, ice, tickets for admission, required donations, etc." The rule fires only when both `alcohol` and `ticket_sales` are present. An event with alcohol and `cash_collection` (for example drink tickets or a cash bar run by the club), `item_sales` (cups) or `fundraising` (a "suggested" donation at the door) never gets the ban. The rule's own `applies_to` promises more than its triggers deliver. This is the remaining part of iteration-3 M4.
Why it matters: A ban the source states outright is never shown for the commonest form of the violation, so the event can look clean on that point.
Suggested fix: Add `alcohol`+`cash_collection` and `alcohol`+`item_sales` variants with `trigger_mode: "all"`, each with its own `violated_when`. Alternatively, extend the trigger model to "A and any of B". Add a fact such as `required_donation` for a donation required for entry. Add an eval case with alcohol and cash collection.

### [medium] M2. Bans and "must" rules stated in the snapshots that no rule encodes, so an event check passes them silently
Where (sources):
- Tabling set-up: rules/sources/tes-tabling.txt:19-22 ("a table and 2 chairs only. No canopy or tent. ... No activations. No amplification.") and student-handbook.txt:5099-5100. Also listed in the research table (docs/research/club_platform.md, section 1, "Tabling" row), which PROJECT_CONTEXT section 7 says to load. A tabling event with `tent` or `amplified_sound` gets no finding.
- Single-use plastic bottles: rules/sources/tes-faq.txt:66 ("the university is prohibiting single-use plastic beverage containers on campus ... All USC facilities, events ... are subject to this policy").
- Smoke-free plan: rules/sources/student-handbook.txt:4860-4866 and tes-faq.txt:103-105 ("Event organizers must provide a plan of action to address potential violations during their scheduled events"), which applies to every event in USC space.
- Outdoor Events and Social Dance Policy: student-handbook.txt:4970-4972 ("Outdoor events and social dances must adhere to the guidelines detailed on the Outdoor Events and Social Dance Policy"). There is no snapshot and no pointer rule, so the demo event (outdoor, ev-01) never mentions it.
Problem: Each one is stated as a prohibition or a duty in a snapshot Greenlight already holds. None is in `rules/events.json`, so none can appear in a checklist. This is the part of iteration-3 L5 that matters most; the rest of L5 is in L5 below.
Why it matters: These are obligations missing from a pre-check whose job is to list what an event must do, and two of them apply to almost every event.
Suggested fix: Add red `banned` rules for tabling with `tent` or `amplified_sound`, with `trigger_mode: "all"`. Add a ban for single-use plastic beverage bottles on events with `food`, using a fact such as `single_use_plastic_bottles`. Add a requirement for a smoke-free plan with trigger `any_event`, or the venue triggers. Add an `unverified`, yellow pointer rule for the Outdoor Events and Social Dance Policy (triggers `venue_outdoor`, `social_dance`) until it has a snapshot. Update the affected eval cases.

### [low] L1. Tabling fundraising rule: trigger narrower than its `applies_to` (unchanged from iteration 3, L1)
Where: rules/events.json:1640-1645 (`applies_to: "... raises money or sells items"`; `triggers: ["tabling", "fundraising"]`, `all`).
Problem: A table that sells items, sells tickets or collects cash, without the `fundraising` attribute, does not fire the rule.
Suggested fix: Add `tabling`+`item_sales`, `tabling`+`ticket_sales` and `tabling`+`cash_collection` variants, or extend the trigger model.

### [low] L2. Messages and fixes that state things the quoted `source_text` does not (iteration 3, L3, unchanged and wider)
Where: rules/events.json:279 (`tes-final-payment`: "or the reservation is cancelled"; the quote stops before tes-terms.txt:251-253); :481 (`tes-room-configuration`: later changes and fees, from B.6 outside the quote); :585 (`tes-cancellation-meeting-rooms`: "in writing", from D.1.i); :533 (`fms-tables-chairs`: the Forms and Permits checklist); :1027 (`lafd-division-5-permit`: "for example canned heat"; the FAQ sends Sterno to separate guidelines); :1099 (`props-approval`: photos, non-metallic, no weapons); :1145 (`special-event-insurance`: co-sponsors, vendors, performers, exhibitors); :1394 (`item-sales-bookstore`: "given in the permit application"); :1617 (`tabling-permit`: SKS desk, displayed on the table); :152 (`uepa-required` fix: "every approval it starts must be in place 2 weeks before the event". The rule also fires on classrooms, which `approvals-two-weeks` (T&C, TES bookings) does not cover, and it names no rule).
Problem: Each claim is in a snapshot, except "canned heat" for Division 5 and the 2-week claim for classrooms, but the citation shown with the finding does not support it.
Suggested fix: Extend each `source_text` to cover its claims, or trim the message. For `uepa-required`, either drop the 2-week sentence for classroom events or add `depends_on: ["approvals-two-weeks"]` and limit the claim to Trojan Event Services venues.

### [low] L3. Source disagreements still not recorded, or recorded on only one side
Where: tes-faq.txt:31 ("We accept cash (for payments under $50)") vs tes-terms.txt:251-253 ("Cash, personal or group checks are not accepted"), for which no rule has `conflicts_with` (iteration 3, L4). Also rules/events.json:305: the `tes-rso-deposits` message states "outdoor venues $100" flatly, and only the other rule (:344) says to plan for $200.
Suggested fix: Record the cash disagreement and keep "no cash" as the stricter rule. In the `tes-rso-deposits` message, say that section C.2 gives $200 and that $200 is applied.

### [low] L4. Open flame: the narrower reading of "USC does not allow candles or flames on campus" is not recorded as a conflict, and the Sterno rule fires for grills
Where: rules/events.json:1015-1039 (`lafd-division-5-permit`, `conflicts_with: null`), :1041-1064 (`no-candles-flames`, triggers `candles` only, notes :1063), :1066-1085 (`sterno-guidelines`, trigger `open_flame`, message about Sterno only); rules/vocabulary.json `open_flame` ("canned heat (Sterno) for food, or a grill"); tes-faq.txt:42-44, :114; tes-terms.txt:573-575 (T&C R: "barbeques ... You may be required to secure additional approvals and permits").
Problem: The fix for iteration-3 H1 removes the false red on Sterno. The general sentence "USC does not allow ... flames on campus" is now applied only to candles. That reading is supported by T&C R, which allows barbeques with approvals, but neither rule cites T&C R or records the disagreement. A grill also triggers `sterno-guidelines`, whose message talks only about canned heat.
Suggested fix: Quote T&C R in `lafd-division-5-permit` (or in a new rule for barbeques and open flame) as the basis for the reading, or mark the two FAQ rules as conflicting. Split `grill` from `open_flame`, or make the Sterno message conditional on canned heat.

### [low] L5. Smaller rules from the snapshots and the research table that are still not encoded (iteration 3, L5, remainder)
Where: Summer 2027 requests from February 1, 2027 (tes-faq.txt:20); Annual Event Early Booking (tes-faq.txt:24-29); Trojan Grand Ballroom discount once a year, up to 10 hours (tes-faq.txt:68); late-cancellation fee of $50 or 100%, series cancellation after two no-shows (tes-terms.txt:279-291), and no-show after 15 minutes (student-handbook.txt:5067-5068); 5 organizations a day and return by 2:15 p.m. for tabling (student-handbook.txt:5093-5094; tes-tabling.txt:32); accessibility statement on publicity (student-handbook.txt:4880-4883); amplified sound not during or near classroom instruction (student-handbook.txt:4902-4905). The social dance rules rest on a document "As of 9/2023" (social-dance.txt:9); the note at events.json:738 does not ask anyone to confirm it is current.
Suggested fix: Add these as `info` or `requirement` rules. Add a verification note to the dance rules asking Trojan Event Services whether the 2023 process still applies.

### [low] L6. First-weeks block: no start date in the data, and the eval relies on a bound the rule does not state (iteration 3, L7)
Where: rules/events.json:126-134 (`no_events_through: "2027-01-26"`, `term: "spring-2027"`, no start date); data/eval/events/cases.json ev-08 (December 12, 2026) and ev-12 (November 16, 2026) list the rule as `condition`.
Problem: An engine that reads the params literally blocks every Fall 2026 event. The eval expects it not to, so the expected answer rests on an unwritten meaning of `term`. Whether January 1-10 (winter recess, "the first 3 weeks of the January") counts is also not stated.
Suggested fix: Add `no_events_from` (January 1 or the term start, with a note on which one and why).

### [low] L7. The same kind of duty gets different severities (iteration 3, L8, unchanged)
Where: rules/events.json:1371 (`cash-collection-approval`, red) vs :1460, :1481, :1548 (filming, dignitaries and FPM approvals, office decides); :1123 (`high-risk-waivers`, red, though whether an activity is "medium" risk is the office's call).
Suggested fix: Document one convention in rules/README.md (red for "you must ask", office decides for the outcome) and apply it everywhere.

### [low] L8. Trigger scope wider or narrower than the source
Where: :1375-1378 (`cash-collection-approval` on any `ticket_sales`; the source says "at the event", tes-terms.txt:504); :282-285 (`tes-final-payment` leaves out meeting rooms; the source says "For all venues"); :1464-1466 (`campus-filming` triggers on `recording` only; the source says "recorded and/or photographed", tes-terms.txt:118); :1030-1033 (`lafd-division-5-permit` fires on any `tent`; the permit is for tents over 450 sq ft, and nothing in the vocabulary carries the size); :853-855 (`alcohol-thursday-saturday` fires on alcohol merely present; the source says "served by the host organization"); :1551-1553 (`fpm-outdoor-electrical` misses indoor "special electrical or custodial needs").
Suggested fix: Adjust the triggers, or add a fact or attribute for each condition: `tent_over_450_sqft`, `photographed`, `sales_at_event`, `special_electrical_needs`.

### [low] L9. Calendar pointer rule: quoted text and confirmation URL (iteration 3, L10, unchanged)
Where: rules/events.json:14 (`source_text` is Spring 2027 only, while the rule stands for 2026-27); :22 and rules/calendar.json `verification_note` (checked against `https://www.usc.edu/academic-calendar/`, but `source_url` and the snapshot are `https://academics.usc.edu/calendar/`).
Suggested fix: Quote the calendar's introductory line, or say that each term's text is in calendar.json. Record which page the person compared against and whether it is the same document.

### [low] L10. "Week 4" for classrooms: the eval asserts a date the rule does not define
Where: rules/events.json:545-571 (no note on how Week 4 is counted); data/eval/events/cases.json:2338 (ev-18 note: "Classroom requests open in week 4 (February 1, 2027)").
Problem: The rule is now yellow (iteration-3 M6 fixed), but the count Greenlight uses (classes begin January 11, plus 21 days) is written only in an eval note.
Suggested fix: Add `notes` to the rule giving the count and asking Classroom Scheduling to confirm it.

### [low] L11. "3 months before" is computed two different ways
Where: backend/app/eval_sets.py:58-66 (a day that does not exist becomes the last valid day of the month: April 30 minus 3 months is January 30) vs backend/tests/unit/test_eval_sets.py:62-65 (any day after the 28th becomes the 28th: January 28).
Problem: For a social dance on the 29th, 30th or 31st of a month, the validator and the test disagree. Whichever date the eval records, one of them fails. No case hits this today (ev-03 is on the 17th, ev-04 on the 5th). This is duplicated logic that has already drifted.
Suggested fix: Have the test import the validator's `_back`, or the future deadline calculator, instead of keeping its own copy.

### [low] L12. The event set's `method` text contradicts the business-day rule
Where: data/eval/events/cases.json:5 ("Monday to Friday, minus the university holidays in the Registrar's calendar") vs data/eval/README.md:16 and rules/calendar.json `business_days` ("holidays and recess days are counted too").
Problem: The dates follow the README. A maintainer who follows the `method` text would produce different dates. Separately, `_check_obligation` recomputes only `before` deadlines (eval_sets.py:95-104), so business-day dates counted after the event are not checked by the validator.
Suggested fix: Correct the `method` text. Recompute `after` deadlines in the validator too.

### [low] L13. Regression tests for iteration-3 fixes check that rules exist, not the behaviour that was fixed
Where: backend/tests/unit/test_rules_loader.py:458-465.
Problem: For M7 the test asserts the `days_in_a_week_must_be_consecutive` flag but not `max_days_per_week == 2`, which was the actual fix. For M4 and M5 it asserts only that rule ids exist. For M1 and M2 it does not check that the stricter rule is the red one. None of the tests would fail if, for example, `alcohol-no-sales` lost a trigger or `tabling-blocked-days` became `info`.
Suggested fix: Assert the fixed values: max days per week, triggers and `violated_when`, the severity of the stricter side of each conflict, and the display severity of the tabling blackout once H1 is fixed.
