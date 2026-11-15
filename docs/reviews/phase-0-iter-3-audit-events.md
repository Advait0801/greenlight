# Phase 0, iteration 3 — audit
Auditor (b): `rules/events.json` against its sources. Commit `9c3f500`.
Summary: 0 blockers, 1 high, 7 medium, 10 low.

Commands run: `python3 scripts/validate_rules.py` (259 rules load, 61 in events; "Every rule marked 'read' matches its snapshot text exactly"); `pytest` in `backend/` (208 passed). No file other than this report was changed.

Every `source_text` in `rules/events.json` was compared by hand with the passage around it in `rules/sources/` (tes-terms.txt, tes-faq.txt, tes-tabling.txt, rso-resources.txt, social-dance.txt, student-handbook.txt, usc-academic-calendar.txt). Every passage is in its snapshot and is the right one. Every lead time, unit, anchor and direction matches its source. The two conflicts PROJECT_CONTEXT section 7 names (decorations 3 vs 2 weeks; large-venue cancellation 3 vs 4 weeks) are encoded, listed in both directions, and the stricter value is named in `notes`. The problems are elsewhere: other disagreements between sources that are not recorded, triggers or params that are broader or narrower than the source, date placeholders with no deadline behind them, and rules that are missing.

## Rule check
| Rule id | Matches source? | Note |
|---|---|---|
| usc-academic-calendar-2026-27 | Yes | The text is in usc-academic-calendar.txt:55-83. `source_text` covers only Spring 2027, but the rule stands for the whole 2026-27 calendar (L10). |
| usc-business-days-definition | Yes (unverified, correct) | The quoted sentence does not define business days. `unverified` is right. The snapshot itself says staff holidays are listed elsewhere (usc-academic-calendar.txt:14). |
| tes-space-request | Yes | "generally at least 3-6 weeks". Uses 6 weeks (the stricter end) and is yellow. Correct. |
| tes-spring-booking-opens | Yes | tes-faq.txt:15. The Summer 2027 opening date (Feb 1, 2027) is not encoded (L5). |
| tes-no-events-first-three-weeks | Yes | tes-faq.txt:15. Blocked through Jan 26; Jan 27-31 yellow. Reasonable. The rule has no start bound and covers only TES venues (L7). |
| uepa-required | Yes | Handbook App. V. Has no deadline fields but `fix_template` uses `{due_date}` (M3). |
| approvals-two-weeks | Yes | T&C A.6. 2 weeks, red. |
| uepa-late-exception | Yes | Exceptional cases only, typically 48 hours; office decides. Correct. |
| dps-security | Yes | T&C A.6.i, "no less than two weeks". Shown as office decides (L8). |
| security-determined-by-dps | Yes | Handbook App. V "Security". Office decides. Correct. |
| tes-final-payment | Yes | T&C C.3.viii, 21 days. The message says something the quoted text does not (L3). Triggers leave out meeting rooms, though the source says "For all venues" (L9). |
| tes-rso-deposits | Yes, but the source contradicts itself | C.3.vii says outdoor $100; C.2.iii says "$200.00 for Student Organizations". Not recorded (M1). The 5 business days do not depend on the business-day rule (L6). |
| tes-av-equipment | Yes | T&C B.1, 3 weeks. |
| tes-decorations-terms | Yes | T&C B.4, 3 weeks. `conflicts_with` is listed both ways. |
| tes-decorations-faq | Yes | tes-faq.txt:107, 2 weeks. `conflicts_with` is listed both ways. |
| tes-decorations-prohibited | Yes | FAQ list. It is the same as the T&C B.4.i list. |
| tes-room-configuration | Yes | T&C B.6. "subject to approval", so yellow is right. |
| tes-outside-rentals | Yes | T&C R, 3 weeks. |
| fms-tables-chairs | Yes | tes-faq.txt:89, 2 weeks. |
| classroom-requests-week-4 | Text yes; the verdict goes beyond it | "accepts requests ... starting Week 4". The rule turns this into a red ban on events before week 4, and "Week 4" is defined nowhere (M6). |
| tes-cancellation-meeting-rooms | Yes | T&C D.1.ii, 2 weeks. The FAQ agrees. |
| tes-cancellation-large-terms | Yes | T&C D.1.iii, 3 weeks. `conflicts_with` is listed both ways. |
| tes-cancellation-large-faq | Yes | tes-faq.txt:35, 4 weeks. `conflicts_with` is listed both ways. |
| social-events-not-study-days-finals | Yes | Handbook App. V. `depends_on` the calendar. Correct. |
| social-event-hours | Yes | Midnight / 2 a.m. for events without alcohol. The end times for events with alcohol are not encoded (L5). |
| social-dance-start | Yes | social-dance.txt, 3 months. The source is the 2023 document (L5). |
| social-dance-events-meeting | Yes | Step 4, 7 weeks. |
| social-dance-form | Yes | 5 weeks; the hold is removed. |
| alcohol-register-campus-activities | Yes | Handbook p.117. |
| alcohol-not-at-dances | Yes | Trigger mode `all` (alcohol and social_dance). Correct. |
| alcohol-thursday-saturday | Yes | Thursday-Saturday; service ends 1 hour before the end. |
| alcohol-requirements | Yes | Bullet list, verbatim. |
| alcohol-uepa-two-weeks | Yes | Handbook p.118, 2 weeks. |
| minors-registration | Yes | tes-faq.txt, 60 days. |
| lafd-division-5-permit | Yes | Open flame, or tent over 450 sq ft. Contradicts `no-candles-flames`, and the conflict is not recorded (H1). |
| no-candles-flames | Text yes; who it applies to does not | A red "banned" verdict fires on `open_flame`, which the vocabulary says includes Sterno. The source points Sterno to separate guidelines (H1). |
| props-approval | Yes | 2 weeks. The message adds details that are not in `source_text` (L3). |
| high-risk-waivers | Yes | Red. Whether an activity counts as "medium" risk is the office's call (L8). |
| special-event-insurance | Yes | "case-by-case", office decides. `{due_date}` has no deadline behind it (M3). |
| food-approved-provider | Yes | T&C K. Depends on the unverified caterer rule, so it shows yellow. Correct. |
| usc-approved-caterers | Yes (unverified, correct) | Purchasing confirms caterers by phone. PROJECT_CONTEXT section 8 lists this as an open question. |
| amplified-sound-register | Yes | Handbook App. V. |
| amplified-sound-90-dba | Yes | 90 dBA measured at 45 ft. The params match the text. |
| amplified-sound-outdoor | Yes | tes-faq.txt:82. Office decides. |
| amplified-sound-hahn-plaza | Yes | T&C F.2. Office decides. `{due_date}` has no published lead time behind it (M3). |
| fundraising-meeting | Yes | Handbook "Process a.", 2 weeks. RSO Resources says the same. |
| fundraising-form-tes | Yes | T&C P.ii. |
| cash-collection-approval | Yes | T&C O.3, "at the event". The trigger `ticket_sales` is broader than that (L9). |
| item-sales-bookstore | Yes | Handbook b.i. |
| charity-collection-letter | Yes | Handbook "Non-Profit Collections", 2 weeks. |
| cosponsors-named-in-uepa | Yes | Handbook "RSO Co-Sponsorship". |
| campus-filming | Yes | T&C A.6.viii. The phone number in the message comes from the Handbook and differs from the one in the T&C (L2). `{due_date}` (M3). |
| dignitaries-clearance | Yes | T&C A.6.vi. `{due_date}` (M3). |
| parking-transportation | Yes, but the source contradicts itself | A.6.iii says "may require"; section M says "will require". Not recorded (M2). `{due_date}` (M3). |
| fpm-outdoor-electrical | Yes | T&C A.6.iv. `{due_date}` (M3). |
| advertising-after-confirmation | Yes | Handbook App. V. |
| advertising-no-outstanding-approvals | Yes | T&C I. |
| tabling-permit | Yes | tes-tabling.txt:15. |
| tabling-fundraising-uepa | Yes | Triggers miss item, ticket and cash sales at a table (L1). |
| tabling-hours | Yes | 10-2, Mon-Fri. The blackout days (holidays, Welcome Week, football) are missing (M5). |
| tabling-limits | Number yes; meaning can drift | "two (2) consecutive days per week" was encoded as a limit on consecutive runs only, so 4 days a week would pass (M7). |

## Findings

### [high] H1. Open flame: one rule bans it, another allows it with a permit, neither is marked as a conflict, and Sterno is caught by the ban
Where: rules/events.json:918-939 (`no-candles-flames`, red, `banned`, trigger `open_flame`); rules/events.json:892-917 (`lafd-division-5-permit`, red, `requirement`, trigger `open_flame`, `conflicts_with: null`); rules/vocabulary.json:15 (`"open_flame": "Open flame, candles or canned heat (Sterno)"`); rules/sources/tes-faq.txt:114-115 and :42-44.
Problem: The same TES FAQ says "USC does not allow candles or flames on campus" and also that a Division 5 permit is needed "if your event contains ... Open flame". For Sterno it points to separate guidelines; it does not ban Sterno. In the rule table, one trigger (`open_flame`) fires a red "banned" verdict and a red "get this permit" requirement at the same time. Neither rule lists the other in `conflicts_with`. The note at :938 says "Greenlight shows both", but nothing in the data enforces that. Because the vocabulary puts Sterno inside `open_flame`, a catered event with chafing-dish Sterno gets a red "banned" verdict, which the source does not support.
Why it matters: Who a rule applies to must match the source. Here the rule produces a false red on a common catering setup, and it hides a disagreement between sources instead of showing it (CLAUDE.md, PROJECT_CONTEXT section 9).
Suggested fix: Split `canned_heat` out of `open_flame` in the vocabulary. Mark `no-candles-flames` and `lafd-division-5-permit` as `conflicts_with` each other (the stricter one, the ban, applies; both are cited). Make Sterno a yellow or "office decides" rule that points to the USC Sterno guidelines.

### [medium] M1. Outdoor deposit for clubs: the T&C says $100 in one place and $200 in another; the rule shows only $100
Where: rules/events.json:292-323 (`tes-rso-deposits`, `params.deposit_usd.venue_outdoor: 100`); rules/sources/tes-terms.txt:225-228 (C.2.iii: "A non‐refundable deposit of $200.00 for Student Organizations and $200.00 for University Departments"); tes-terms.txt:248-250 (C.3.vii: $100.00).
Problem: The T&C states two outdoor deposit amounts for student organizations. The rule quotes only the $100 one and does not mention the other.
Why it matters: Sources that disagree must both be shown, with the stricter one applied. Showing the officer $100 as the only figure presents an unsettled number as certain.
Suggested fix: Quote C.2.iii in a second rule (or a second source passage), mark the two with `conflicts_with`, show $200 as the stricter figure, and say that TES confirms the amount.

### [medium] M2. Parking: the T&C says both "may require" and "will require"; the rule quotes only the softer one
Where: rules/events.json:1344-1364 (`parking-transportation`); rules/sources/tes-terms.txt:97-99 (A.6.iii "may require a parking reservation") vs tes-terms.txt:482-484 (M: "will require a parking reservation and must be approved by USC Transportation Services").
Problem: The rule cites only A.6.iii and shows "office decides". Section M of the same document makes the reservation mandatory, and also requires advance approval for vendor loading and oversize vehicles.
Why it matters: The stricter reading is never shown, so a reservation that is mandatory looks optional.
Suggested fix: Add the section M text as a separate rule, red when `outside_guests_parking` is present. Mark the two with `conflicts_with` and apply the stricter one.

### [medium] M3. Seven rules ask for `{due_date}` but have no deadline that defines it
Where: rules/events.json:152 (`uepa-required`), :1000 (`special-event-insurance`), :1139 (`amplified-sound-hahn-plaza`), :1316 (`campus-filming`), :1337 (`dignitaries-clearance`), :1358 (`parking-transportation`), :1379 (`fpm-outdoor-electrical`). None of them has `anchor`, `offset`, `unit` or `direction`. The eval set expects `"due": null` for `uepa-required` (data/eval/events/cases.json:41-46).
Problem: Code cannot fill `{due_date}` from the rule's own data. Either the officer sees a raw placeholder, or the engine borrows a date from another rule that the finding does not cite. For the insurance and Hahn Plaza rules no source gives any lead time, so any date would be made up. For the A.6 sub-items the 2-week date really does come from `approvals-two-weeks`, but no field says so. `uepa-required` also triggers on `venue_classroom`, and `approvals-two-weeks` does not cover classrooms.
Why it matters: Every deadline must carry its own rule text and source link, and nothing unverified may look certain. A "contact them by <date>" with no cited source breaks both.
Suggested fix: For the A.6 sub-items, add `depends_on: ["approvals-two-weeks"]` and a field that says the date comes from that rule. For insurance and Hahn Plaza, remove `{due_date}` or explicitly state that no lead time is published. Add a loader check that rejects `{due_date}` when a rule has no deadline fields and no rule it takes the date from.

### [medium] M4. Missing rule: alcohol cannot be combined with ticket sales or required donations
Where: rules/sources/student-handbook.txt:5160-5165 ("The selling, either directly or indirectly, of alcoholic beverages ... is prohibited. This includes selling cups, mixes, ice, tickets for admission, required donations, etc."); rules/sources/tes-terms.txt:440-443 (same text). No rule in rules/events.json or rules/outside_money.json encodes it.
Problem: An RSO event with alcohol and paid admission (for example a ticketed gala) breaks a written Handbook and T&C rule. The rule table has nothing that catches it. Also missing from the same section: "Alcohol may not be the main 'focus'" (student-handbook.txt:5149-5150), and the end times for events with alcohol ("Thursday events with alcohol must end by 12:00 a.m.", Friday and Saturday by 2:00 a.m.; student-handbook.txt:5170-5172).
Why it matters: A realistic event gets no warning about a rule from a source the project calls READ.
Suggested fix: Add a red `banned` rule with `triggers: ["alcohol", "ticket_sales"]` (and a required-donation equivalent), `trigger_mode: "all"`, quoting the Handbook. Add the end times for events with alcohol to the hours check.

### [medium] M5. Missing blocked periods: home football days, and tabling blackout days
Where: rules/sources/tes-faq.txt:72 ("Trojan Event Services does not reserve outdoor spaces on home football game days."); rules/sources/tes-tabling.txt:16 ("RSO Tabling is not permitted during official university functions or holidays including but not limited to Welcome Week, Orientation, and home football game days ..."). Related: rules/events.json:1477-1507 (`tabling-hours` checks only weekday and hours). The research notes list home football days among the "hard calendar blocks the planner can enforce" (docs/research/club_platform.md, section 1, Inferences).
Problem: An outdoor event on a home game Saturday, or tabling on a university holiday or during Welcome Week, passes every rule in the table.
Why it matters: These are wrong passes on blocks the sources state outright.
Suggested fix: Add `blocked_period` rules for both. The football schedule and the Welcome Week and Orientation dates are not in any snapshot, so mark the dates `unverified` and show yellow until a person adds and confirms them. University holidays can come from `calendar.json`.

### [medium] M6. Classroom "Week 4" becomes a red ban on a week count no source defines
Where: rules/events.json:503-529 (`classroom-requests-week-4`, `blocked_period`, red, `depends_on: ["usc-academic-calendar-2026-27"]` only); rules/sources/rso-resources.txt:28 ("Classroom Scheduling accepts requests for classroom spaces starting Week 4."); rules/calendar.json `academic_weeks.definition: null, verified: "unverified"`.
Problem: The source says when requests are accepted. The rule turns that into "a classroom event cannot be booked earlier" (message at :516) and shows it red. "Week 4" is not defined in the source or the calendar: is it counted from the first day of classes, does recess count, is it this semester's week 4 or the previous one's? The only dependency is the calendar, which is `read`, so the verdict shows as certain.
Why it matters: A red verdict rests on a reading the source does not state and on a count no source defines. That is unverified material shown as certain.
Suggested fix: Make it yellow (or have it depend on an unverified week-numbering rule), state how Greenlight counts week 4 (classes begin + 21 days), and ask Classroom Scheduling to confirm.

### [medium] M7. Tabling limit encoded as "consecutive runs of at most 2", which lets 4 days a week pass
Where: rules/events.json:1508-1532 (`params.max_consecutive_days_per_week: 2`, `max_days_per_month: 6`); rules/sources/tes-tabling.txt:33 ("You can table for two (2) consecutive days per week. You can not exceed six (6) days per month.").
Problem: The most natural reading of the source is "at most 2 days a week, and they must be consecutive". The param caps only the length of a consecutive run. With that param, Monday-Tuesday plus Thursday-Friday (4 days in one week) passes, and so do Monday, Wednesday and Friday.
Why it matters: A wrong pass. The number is right but its scope is wrong, so the check can say green when the club is over the limit.
Suggested fix: Encode `max_days_per_week: 2` and a separate "must be consecutive" condition, both from the quoted text. If the meaning is uncertain, show yellow with a note to confirm with TES.

### [low] L1. Tabling fundraising trigger is narrower than the rule's own `applies_to`
Where: rules/events.json:1454-1476 (`triggers: ["tabling", "fundraising"]`, `trigger_mode: "all"`; `applies_to: "Walk-up tabling that raises money or sells items"`).
Problem: Selling at a table (`item_sales`, `ticket_sales`, `cash_collection`) does not fire the rule, but the message talks about "fundraise or sell at the table".
Suggested fix: Make the money triggers alternatives, combined with `tabling`. The current trigger model cannot express "A and any of B" in one rule, so either split the rule or extend the trigger model.

### [low] L2. Campus Filming Office phone number in the message is not the one in the cited source
Where: rules/events.json:1315 (message gives "(213) 740-6951"; the rule cites the T&C); rules/sources/tes-terms.txt:395 (T&C J: "213‐713‐3767"); rules/sources/student-handbook.txt:5135-5138 (Handbook: 740-6951).
Problem: The two sources give different numbers. The message uses the number from the source it does not cite.
Suggested fix: Cite the Handbook "Filming" section for the number, or show both numbers.

### [low] L3. Some messages state things that are not in the quoted `source_text`
Where: rules/events.json:279 (`tes-final-payment`: "or the reservation is cancelled"; the quote stops before "Failure to remit payment on time will result in the cancellation", tes-terms.txt:254-255); :953 (`props-approval`: "with photos", "non-metallic; no weapons" are outside the quote); :999 (`special-event-insurance`: "co-sponsors, vendors, performers and exhibitors" are outside the quote).
Problem: Each claim is in the snapshot, but the citation shown to the officer does not support it.
Suggested fix: Extend `source_text` to cover each claim, or trim the messages.

### [low] L4. Payment methods: FAQ and T&C disagree about cash, and this is not recorded
Where: rules/events.json:275-279; rules/sources/tes-faq.txt:31 ("We accept cash (for payments under $50)") vs tes-terms.txt:252-253 ("Cash, personal or group checks are not accepted.").
Suggested fix: Record the disagreement. Keep the stricter "no cash" and cite both.

### [low] L5. Smaller rules from the snapshots and research table that are not encoded
Where (sources): Summer 2027 booking opens Feb 1, 2027 (tes-faq.txt:19-20); Annual Event Early Booking (tes-faq.txt:24-29); Grand Ballroom discount once a year, up to 10 hours (tes-faq.txt:68); late-cancellation fees of $50 or 100%, the 15-minute no-show rule, and series cancellation after two no-shows (tes-terms.txt:266-279; student-handbook.txt:5068-5072); tabling locations, table and 2 chairs only, no canopy, no activations, no amplification, return by 2:15 p.m., 5 organizations a day (tes-tabling.txt:14-22, 32; student-handbook.txt:5088-5101); the Smoke Free plan of action every event needs (student-handbook.txt:4860-4866; tes-faq.txt:103); single-use plastic bottles (tes-faq.txt:61); the accessibility statement on publicity (student-handbook.txt:4881-4883); the "Outdoor Events and Social Dance Policy" the Handbook requires (student-handbook.txt:4970-4972), which has no snapshot. The social dance rules rest on a document "As of 9/2023" (social-dance.txt:9).
Suggested fix: Add the ones the research table lists (summer opening, early booking, ballroom discount, cancellation fees and no-shows, tabling setup) as `info` or `requirement` rules. Add an `unverified` pointer rule for the Outdoor Events and Social Dance Policy until it has a snapshot, and give the 2023 dance rules a note asking TES whether the document is still current.

### [low] L6. Deposit due date is counted in business days without depending on the business-day rule
Where: rules/events.json:320 (`due_business_days_after_processing: 5`); `depends_on` is absent.
Problem: The loader requires `usc-business-days-definition` only when the rule's `unit` is `business_days`. This business-day count sits in `params`, so the check never sees it.
Suggested fix: Add `depends_on: ["usc-business-days-definition"]`.

### [low] L7. First-weeks block has no start date and covers only TES venues
Where: rules/events.json:105-137 (`applies_to: "... dated on or before January 26, 2027"`; params have `no_events_through` but no start date).
Problem: Read literally, the rule blocks every event before Jan 27, 2027, including Fall 2026 events and events during winter recess. The source says "RSOs can not host events" without limiting it to TES venues.
Suggested fix: Add `no_events_from: "2027-01-11"` (or the start of the term). Decide whether other campus venues should be yellow.

### [low] L8. The same kind of approval gets different severities
Where: rules/events.json:1225 (`cash-collection-approval`, "require the approval of", red) vs :1314, :1335, :1377 (filming, dignitaries and FPM, "must obtain/must be approved", office decides); :228 (`dps-security`: the duty to contact DPS is firm but is shown as office decides); :977 (`high-risk-waivers`: red, though deciding whether an activity is "medium" risk is the office's call).
Problem: The trust rule separates the office's judgment (office decides) from the club's duty to ask (a requirement). These rules mix the two without a consistent pattern.
Suggested fix: Use red for "you must ask" and office decides for "they decide the outcome". Or document the convention in rules/README.md and apply it the same way everywhere.

### [low] L9. Trigger scope wider or narrower than the source
Where: rules/events.json:1229-1232 (`cash-collection-approval` fires on any `ticket_sales`; the source says "at the event", tes-terms.txt:504); :282-285 (`tes-final-payment` leaves out meeting rooms; the source says "For all venues", and meeting rooms can still carry A/V and staffing charges).
Suggested fix: Narrow the first rule to sales at the event. Widen the second, or add a condition: "when Trojan Event Services charges are due".

### [low] L10. Calendar pointer rule: quoted text and confirmation URL
Where: rules/events.json:14 (`source_text` is Spring 2027 only); :22 (says the dates were checked against `https://www.usc.edu/academic-calendar/`, while `source_url` and the snapshot are `https://academics.usc.edu/calendar/`).
Suggested fix: Quote the line that introduces the 2026-27 calendar, or note that each term's text lives in calendar.json. Record which URL the person used.
