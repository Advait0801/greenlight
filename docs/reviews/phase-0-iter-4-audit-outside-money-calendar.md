# Phase 0, iteration 4 — audit (c): outside money, academic calendar, USG deadline table
Summary: 1 blocker, 1 high, 3 medium, 8 low.

Scope:
- `rules/outside_money.json` (22 rules) and `rules/vocabulary.json` (facts).
- `rules/calendar.json`, plus every rule in any domain that rests on the calendar, business days or academic weeks.
- `rules/sources/usg-funding-deadlines.txt`, its manifest entry, `docs/research/open_questions.md`, and `usg-academic-week-definition`.
- The expected answers that depend on these, in `data/eval/events/cases.json` and `data/eval/year_plans/cases.json`.

Commit `f65afcc`.

Commands run:
- `python scripts/validate_rules.py`: OK. 285 rules; read 280, unverified 5; "14 more rules depend on an unverified rule".
- `python scripts/run_eval.py`: all four sets valid.
- `pytest` in `backend/`: 266 passed.
- SHA-256 of `raw/usc-academic-calendar.html`, `raw/student-handbook.pdf`, `raw/rso-accountability.html` and `raw/usg-funding-page.html` all match the manifest.
- The body of `usg-funding-deadlines.txt` is byte-identical to `docs/research/manual_snapshots/usg-funding-deadlines-26-27.csv`, and both hash to the manifest's `f2945352…`.

What I checked by hand:
- Every outside-money `source_text` against Handbook pp. 77 and 88-92 (snapshot lines 3455-3482 and 3905-4125), Appendix IX (line 5556), RSO Accountability (line 53) and the USG page FAQ (line 53). I read the paragraphs around each one, including the Handbook's definition of "Unrecognized Student Organization" (line 3593).
- Every calendar date against the Registrar snapshot (lines 13-90).
- Every business-day due date in both eval sets, recomputed (all match).
- Every row of the deadline table, re-counted in academic weeks.
- Each finding of the iteration-3 audit, against the current files.

## Rule check

### outside_money.json

| Rule id | Matches source? | Note |
|---|---|---|
| sponsorship-in-kind | Yes | Handbook p.91 bullet, verbatim. `condition_rules` leaves out `cosponsor-primary-audience` (L2). |
| sponsorship-cash-banned | Yes | Verbatim, red, `violated_when: sponsor_gives_money`. The message "A company cannot give the club money" is broader than "Corporate Sponsorships … may not include monetary donations"; the gift-account route is not encoded (L2). |
| cosponsor-club-primary | Yes | 5 bullets verbatim. Fires on `outside_co_host` and `sponsorship`, as the list's lead-in ("hosting an event with an outside organization") says. Iteration-3 M fixed. |
| cosponsor-primary-audience | Yes | New, verbatim, same triggers. |
| cohost-recognized-club | Text yes; message no | The message says "a co-host that is not a recognized student organization is not allowed". That contradicts its own quoted sentence, which names departments and outside agencies as co-sponsors (H1). |
| cohost-unrecognized-banned | Text yes; message, fix and fact no | The source bans "Unrecognized Student Organizations", a defined term. The rule, its fix and the fact `co_host_not_recognized` ban any co-host that is not a recognized student organization (H1). |
| no-business-vendors | Yes | Fix corrected (iteration-3 M fixed). |
| vendors-need-permission | Yes | New. Verbatim, including phone numbers; the message matches. The preceding sentence (only the Bookstores, Hospitality and Athletics may bring vendors) is not quoted (L5). |
| donations-through-university | Yes | `source_section` fixed. The message is now supported. The title still says "only" (L2). |
| own-tax-exempt-banned | Yes | Section and fix corrected; now reachable (`files_own_tax_exemption`). |
| fundraising-allowed | Yes | Every claim in the message is reached through `lead_time_rules`. |
| fundraising-approval-discretionary | Yes | New, `office_decides`, verbatim (iteration-3 M fixed). Small gaps in scope and in the fix text (L4). |
| no-individual-benefit | Yes | Verbatim, red, fact-driven. |
| ticket-sales-cover-costs | Text yes; kind no | A restriction ("only to cover that event's costs") encoded as `allowed / info` with no fact (M1). |
| raffle-purchase-banned | Yes | Verbatim, red, `drawing_requires_purchase`. |
| free-drawing-wording | Yes | Now `requirement / red`, and the message names every item. Iteration-3 H2 fixed; there is still no free-drawing eval case (L8). |
| silent-auction-advancement | Yes | The bid-sheet and gift-record lines are still not encoded (L5). |
| sponsorship-activation-banned | Yes | `source_text` extended, so the message is now supported (iteration-3 M fixed). |
| brand-ambassadors-banned | Yes | Now also fires on fundraising, ticket sales and `uses_brand_ambassadors`. |
| dues-voluntary | Yes | RSO Accountability line 53, verbatim. Now reachable via `collects_dues`. |
| dues-required-banned | Yes | Verbatim, `violated_when: dues_required`. |
| other-usc-funds-ask-usg | Yes | USG page line 53, verbatim. Now triggers on `other_usc_funding`. The message adds "school councils", which the source does not list (L3). |

### calendar.json and the rules that depend on it

| Rule / entry | Matches source? | Note |
|---|---|---|
| calendar `fall-2026` | Yes | Every date and weekday matches the snapshot. The loader re-parses the quoted text. |
| calendar `spring-2027` | Yes | Classes Jan 11 to Apr 30; MLK Jan 18; President's Day Feb 15; Spring Recess Sun-Sun Mar 14-21; study days May 1-4; exams May 5-12; commencement May 12-15. |
| calendar `summer-2027` | Yes | Independence Day "Mon July 4-5" is encoded as Jul 4-5, as the source states. |
| calendar `recesses` (Winter) | Yes | Dec 17 to Jan 10. `is_break()` includes it, so `usg-no-funding-breaks` blocks it. |
| calendar `business_days` | Unverified (correct) | Every weekday counts, which gives the earliest date for "after" deadlines. The unsupported "offices stay open" note is gone (iteration-3 M fixed). |
| calendar `academic_weeks` | Unverified (correct) | `definition: null`. |
| usc-academic-calendar-2026-27 | Yes | `read`. The validator checks that it agrees with the calendar. |
| usc-business-days-definition | Yes, unverified | The message now says which way the date may be off. |
| usg-academic-week-definition | Yes, unverified | Now records `rows_to_confirm` (all 12 doubtful rows), `date_to_row` and `while_unconfirmed` (iteration-3 H1 and M addressed). The eval method contradicts `while_unconfirmed` (M2). Lookup gaps remain (L6). |
| usg-deadline-vendor / usg-page-deadline-event-date / usg-page-deadline-nine-weeks-payment / usg-deadline-travel / usg-faq-deadline-new-vendors-travel | Yes | Each depends on `usg-academic-week-definition`, so each is yellow and undated in the answer keys. |
| usg-faq-professional-travel-eight-weeks | Text yes; use no | Calendar weeks, `read`, no dependency, so it is certain. Its date is always later than the 9-week travel deadline, yet it is presented as "the earliest", and it is listed for trips outside its fund (B1). |
| usg-no-funding-breaks / usg-faq-no-summer-funding | Yes | Calendar only. Red and yellow respectively. |
| usg-post-event-evaluation / usg-final-invoices / usg-incomplete-two-business-days / usg-faq-incomplete-three-business-days / recognition-appeal | Yes | All "after" deadlines, so every-weekday counting is the stricter choice; shown yellow. All due dates in the eval sets recomputed correctly. |
| usg-incomplete-48-hours | Yes | Hours, no calendar needed. |
| tes-no-events-first-three-weeks | Yes | Blocks through Jan 26; Jan 27-31 shown yellow. |
| social-events-not-study-days-finals / tabling-blocked-days | Yes | Depend on the calendar. |
| classroom-requests-week-4 | Yes | Now yellow with the calendar dependency (iteration-3 L fixed). |
| tes-rso-deposits / tes-outdoor-deposit-section-c2 | Yes | Now depend on `usc-business-days-definition` (iteration-3 L fixed). |
| `usg-funding-deadlines.txt` (manual) | Consistent with its notes | The hash matches, and every deadline is a Wednesday. Re-counted in academic weeks (fall weeks 1-15, winter and spring recess skipped), the rows that give fewer weeks than the guidelines are:<br>- 6-week column: Jan 11 and Jan 18.<br>- 9-week column: Jan 11 to Feb 8, and Mar 22 to Apr 26.<br>Every one of these rows is in `rows_to_confirm` (Feb 15 is listed too, which errs on the safe side). The test covers only part of this (M3). |

## Findings

### [blocker] The FAQ's 8-week travel date is shown as a certain deadline, "the earliest", but it is always later than the 9-week travel deadline. It is also listed for trips outside the Professional/Academic Fund.
Where:
- rules/funding.json:244-275 (`usg-faq-professional-travel-eight-weeks`: `verified: read`, `unit: weeks`, no `depends_on`, `fix_template` "Apply by {due_date}, the earliest of the deadlines.")
- data/eval/events/cases.json:2493-2497 (ev-20: `to_do`, due 2027-01-07), :2538-2541 (conflict with `usg-deadline-travel`, `applied: null`), and the ev-21 entry at :2649 (`to_do`, due 2027-02-13)
- data/eval/year_plans/cases.json:392-396 (yp-01 retreat: `to_do`, due 2027-01-01)
- backend/app/eval_sets.py:160-191 (`_check_conflicts` accepts `applied: null` when only one side has a date)

Problem: `usg-deadline-travel` (guidelines: 9 academic weeks before the initial payment due date) applies to every USG travel request. Nine weeks back from a date that is on or before the event is always earlier than eight weeks back from the event. So the 8-week date is never the earliest deadline, under any reading of "academic week".

Because the 9-week rule is unverified, it has no date. The 8-week rule is `read` with no dependency, so `display_severity` is red and the answer keys give it status `to_do`, a certain date:
- **ev-20** (conference, Mar 4, 2027): Jan 7, 2027. The transcribed table gives Nov 18, 2026 for that event week. Nine calendar weeks back gives Dec 31, 2026.
- **yp-01 retreat** (the demo story, Feb 26, 2027): Jan 1, 2027. That date is in winter recess, when USG does not process applications, and is not a Wednesday. The table gives Nov 18, 2026, three days after the `as_of` date. The same case's own `problems` note says so, so the calendar entry and the problem contradict each other.
- **ev-21** (bus trip, Apr 10, 2027): Feb 13, 2027, a Saturday. The table gives Feb 3, and counting academic weeks gives Jan 27.

The rule also does not apply to two of the three cases:
- Its source is the FAQ's "Professional and Academic Fund" section, and it covers "airfare and hotel" (`params.fund_rules`, `applies_to`).
- yp-01 is a cultural club's retreat. ev-21 is a service trip by charter bus, with no airfare or hotel.
- It is listed for them only because `test_event_obligations_agree_with_rule_triggers` lists every rule whose trigger (`travel`) matches. No fund fact narrows it.

Why it matters: An engine that meets these answer keys will tell the officer, in red and as certain, "Apply by Jan 1, 2027, the earliest of the deadlines". USG's own table says Nov 18, 2026, and a missed USG deadline is an automatic denial. This is the retreat in the demo, and the deadline is days away. It is a wrong date shown as certain, and it breaks "where sources disagree, the stricter rule is applied".

Suggested fix:
- A deadline whose `conflicts_with` partner is uncertain and could be stricter must not be shown as certain. Show it `check_with_office` (yellow) with the partner cited. Alternatively, apply `usg-academic-week-definition.params.while_unconfirmed` and date the 9-week deadline (table date, or the counted date if earlier) so the stricter one is shown.
- Drop "the earliest of the deadlines" from this rule's fix unless code has checked that it is the earliest.
- Restrict the rule to Professional/Academic Fund requests with airfare or hotel (a typed fund fact plus `trigger_mode: all`, or a line-item trigger). Remove it from yp-01 and ev-21.
- Make `_check_conflicts` reject `applied: null` when exactly one side has a date and the other is the longer lead time.
- Add a regression test asserting that no `to_do` due date in either set is later than a conflicting rule's deadline counted the same way.

### [high] The co-host ban turns the Handbook's "Unrecognized Student Organizations" into "any co-host that is not a recognized student organization", which bans departments and outside agencies
Where:
- rules/outside_money.json:136 (source text), :140 (message), :141 (fix), :147 (`violated_when: co_host_not_recognized`), :112 (`cohost-recognized-club` message)
- rules/vocabulary.json:92 (`co_host_not_recognized`: "A co-host is not a recognized student organization")
- rules/sources/student-handbook.txt:3593-3600 (definition) and :4045-4047

Problem:
- The Handbook defines an Unrecognized Student Organization as "any group … composed of a substantial number of USC students, that is not officially recognized by the university". The quoted ban covers only those groups.
- The same section opens by saying RSOs co-sponsor "with other student organizations, departments, and/or outside agencies". It then sets conditions for "an RSO hosting an event with an outside organization", which assumes such events are allowed.
- The rule instead says "Co-hosting with a group that is not a recognized student organization is strictly prohibited", and the fix says "Co-host only with a recognized student organization".
- The fact is defined so that a university department, a non-profit or a company co-host truthfully sets it. `cohost-recognized-club`'s message repeats the same claim, right after quoting the sentence that contradicts it.

Why it matters: An officer co-hosting with a career centre, an academic department or an outside non-profit (which the Handbook permits, with conditions) gets a red "strictly prohibited" verdict, cited to a source that does not say that. The officer would drop a lawful partner or abandon the event. This rule is marked `read`.

Suggested fix:
- Redefine the fact as "A co-host is an Unrecognized Student Organization: a group of USC students that is not recognized by the university, including suspended or banned groups" (`co_host_is_unrecognized_student_org`).
- Reword the message and fix to "Co-hosting with an unrecognized student group is strictly prohibited. Co-host only with recognized organizations, university departments or outside organizations that meet the co-sponsorship conditions."
- Correct `cohost-recognized-club`'s message.
- Add an eval case co-hosted with a department, expected `condition` (not violated) for this rule.

### [medium] Ticket sales "only to cover that event's costs" is a restriction encoded as `allowed / info` with no fact, and the charity-run case never meets it
Where: rules/outside_money.json:329-354 (`ticket-sales-cover-costs`); data/eval/events/cases.json:1215 (ev-10)
Problem:
- The Handbook makes tickets "permissible if approved proceeds from sales will help the RSOs cover expenses for that specific event". The message says "Tickets may be sold only to cover that event's own costs."
- Because the rule is `kind: allowed`, the eval method never lists it, and it has no `violated_when` fact. Nothing can ever flag proceeds that go elsewhere.
- ev-10 is a 5K with a $20 registration fee and "all money going to the American Red Cross". That is a payment for an activity whose proceeds do not cover event costs. The answer key lists nothing about it; only the generic office-decides approval appears.
- This is the same pattern as iteration-3 H2 (free drawings).

Why it matters: The restriction in PROJECT_CONTEXT's table ("Only to cover that event's costs") can never reach the officer as a check.

Suggested fix: Make it `kind: requirement` with a fact such as `ticket_proceeds_beyond_event_costs`, and red when that fact is set. Alternatively, `office_decides` when tickets fund a charity: the Handbook's charity-collection route (Process iii) may be the right one, so the office decides. Record ev-10's expected status for it.

### [medium] The rule says to show a dated academic-week deadline while unconfirmed; the eval method and validator forbid any date
Where: rules/funding.json:40 (`while_unconfirmed`: "show the earlier of the table's date and the same number of weeks counted back with breaks skipped, and cite both"); data/eval/README.md:16 ("Deadlines counted in USG 'academic weeks' have no date"); backend/app/eval_sets.py:103-104
Problem: The rule table, which code reads, prescribes a yellow but dated USG deadline. The answer keys require `due: null` for every academic-week rule, and the validator rejects any date. An engine that follows the rule (the safer behaviour, showing Nov 18, 2026 for the retreat) would be scored as wrong. An engine that matches the key gives the officer no USG date at all. That gap is what leaves the 8-week date standing in B1.
Why it matters: The accuracy test set rewards the less safe output, and the two places that define the behaviour disagree.
Suggested fix: Pick one policy. If `while_unconfirmed` stands, let academic-week entries carry a `due` with status `check_with_office`, plus the table date and counted date as separate fields. Have the validator recompute both from `usg-funding-deadlines.txt` and `calendar.json`.

### [medium] The deadline-table regression test checks only the after-recess rows; the early-spring rows, row order and blank rows are untested
Where: backend/tests/unit/test_rules_loader.py:487-513
Problem: The test checks the hash, Wednesdays and Monday starts. It collects doubtful rows only for `start >= 2027-03-22` with a 6-to-9-week gap other than 21 days.
- Removing the six early-spring rows (2027-01-11 to 2027-02-15) from `rows_to_confirm` would still pass. So would a 9-week cell edited to a later Wednesday in January.
- It does not check that rows are consecutive, that blank rows fall only in breaks, study days or finals from `calendar.json`, or that `end` is a Friday (the docstring claims "the rows run Monday to Friday").
- It does not count academic weeks per row, which is how the doubtful rows were found.

The hash check mostly protects the file, but the hash is recorded in the same commit as the file, so it does not detect an edit made together with a manifest update.
Why it matters: The iteration-3 finding asked for exactly these checks. As written, the regression test does not really exercise the fix for the early-spring rows.
Suggested fix: Count academic weeks per row against `calendar.json`. Assert that every row giving fewer than 6 or 9 weeks is in `rows_to_confirm`, that rows are consecutive Monday-to-Friday weeks, and that blank rows match break, study-day or finals weeks.

### [low] Club-to-club co-hosting still inherits the outside-organization conditions; the department co-sponsor sentence is not encoded
Where: rules/outside_money.json:118-123 (`cohost-recognized-club` `condition_rules` includes `cosponsor-club-primary`); student-handbook.txt:4073-4077
Problem: `cosponsor-club-primary` was correctly narrowed to `outside_co_host`/`sponsorship`. But `cohost-recognized-club`, which fires on any `co_hosts`, still names it as a condition. Its message says "the co-sponsorship conditions apply" for two clubs co-hosting. The Handbook sentence on co-sponsoring with university departments ("will only be considered the primary producing entity if all of the above conditions apply") is not encoded.
Suggested fix: Drop `cosponsor-club-primary` from `cohost-recognized-club`'s `condition_rules`, or word the message for the outside-organization case only. Add an `info` rule for the department sentence.

### [low] In-kind sponsorship and donation wording claims more or less than the source
Where: rules/outside_money.json:25-27, :44, :203
Problem:
- `sponsorship-in-kind`'s `condition_rules` omits `cosponsor-primary-audience`, so its message leaves out the audience condition.
- `sponsorship-cash-banned` says "A company cannot give the club money". The source restricts sponsorships. Handbook p.89 (line 3995-4002) lets RSOs "accept donations from university departments or outside entities through utilization of a gift account through University Advancement", and no rule encodes that sentence.
- The title "Donations only through the university" keeps an "only" the source does not state.

Suggested fix: Add the audience rule to `condition_rules`. Reword the message to "A corporate sponsorship cannot include money". Encode the gift-account sentence as an `info`/`allowed` rule. Drop "only" from the title.

### [low] Other-USC-funds wording and the duplicate USG denial note
Where: rules/outside_money.json:532; rules/funding.json:1922-1945 (`usg-denial-other-university-funding`)
Problem: The message lists "school councils", which the quoted FAQ sentence does not name. It names academic departments, grants, fellowships and programming assemblies. `usg-denial-other-university-funding` still triggers on every `usg_funding` application, and its `fix_template` has `{other_source}`, which cannot be filled when no other source exists.
Suggested fix: Replace "school councils" with the source's list. Trigger the funding rule on `usg_funding` + `other_usc_funding` (`trigger_mode: all`).

### [low] `fundraising-approval-discretionary` scope and fix text
Where: rules/outside_money.json:287-299
Problem:
- The quoted "may approve … based on the event details" sentence is item v ("Other types"). The general approval sentence ("RSOs will need approval from Campus Activities before conducting any fundraising efforts") is in `fundraising-meeting`, not here.
- The fix's "the meeting is due 2 weeks before the event" is not in this rule's text, and no `_rules` param points to `fundraising-meeting`.
- Charity collections (Process iii) do not trigger it.

Suggested fix: Add `lead_time_rules: ["fundraising-meeting"]`, quote the general approval sentence (or cite it), and add the `charity_collection` trigger.

### [low] Money-related Handbook passages still neither encoded nor recorded as out of scope
Where: student-handbook.txt:3915-3923 (no for-profit or commercial activity, no acting as a front for a business), :4031-4043 (bid-sheet wording and record of donated gifts), :4087-4089 (only the Bookstores, Hospitality and Athletics may bring vendors), :4097-4102 (USC emblem products for fundraisers must come from a licensed vendor), :4116-4119 (sponsor materials vetted with the Sponsorship Form)
Problem: This repeats the iteration-3 low finding. Except for the vendor permission sentence, none of these is in `rules/`, and `rules/README.md` does not list them as out of scope. Emblem merchandise matters for the bake-sale and merch cases.
Suggested fix: Encode them as requirements, or list them as out of scope in `rules/README.md`.

### [low] Deadline-table lookup gaps not stated in the rule
Where: rules/funding.json:25 (`date_to_row`), :40 (`while_unconfirmed`), :43 (notes); docs/research/open_questions.md (item 4, Nov 11)
Problem:
- `date_to_row` says to look up the initial payment due date "the same way". It does not say what happens when that date falls in a blank row (Dec 7 to Jan 10, Mar 15-19), an N/A row (Aug 24 to Oct 2) or after Apr 30. A deposit due Dec 20 for a February event has no row.
- `while_unconfirmed` says "breaks skipped" without saying whether partial-week breaks (Fall Recess Thu-Fri, Thanksgiving Wed-Sun) skip the week.
- The research note's point that the Nov 11 deadlines fall on Veterans Day (USG does not process applications on holidays) is not recorded on the rule. It is now in the past, so the impact is small.

Suggested fix: State the fallback for a payment date with no row: use the counted date and show yellow. State the partial-week convention. Add the Nov 11 conflict to the rule's notes.

### [low] Stale count in rules/README.md, and an unguarded business-day direction
Where: rules/README.md:53 ("Ten more rules depend on them"); backend/app/eval_sets.py:67-74
Problem: The validator reports 14 dependent rules. `_back` counts business days *before* an anchor with every weekday included, which gives the later (lenient) date. No rule uses business days "before" today, but nothing stops one being added.
Suggested fix: Update the count, or say "the validator lists them". Make the loader reject `unit: business_days` with `direction: before` until the assumption is confirmed, or count only in the strict direction.

### [low] No free-drawing case in the event set
Where: data/eval/events/cases.json (only ev-26, a paid raffle, uses `prize_drawing`)
Problem: The iteration-3 fix made `free-drawing-wording` a red requirement. No case checks a lawful free drawing, where it should be `to_do` and `raffle-purchase-banned` should be a `condition`.
Suggested fix: Add one free-drawing sentence with its expected obligations.

## Iteration-3 findings: status

| Iteration-3 finding | Status |
|---|---|
| H1 9-week column / early-spring rows | Recorded (`rows_to_confirm`, notes, `while_unconfirmed`). The eval method contradicts the policy (M2), and the test covers only part of it (M3). |
| H2 free drawing | Fixed, with a test. Eval case still missing (L8). |
| M `no-business-vendors` fix | Fixed. The Vendors paragraph is encoded. |
| M `cosponsor-club-primary` | Fixed. A related co-host error is now H1 above. |
| M discretionary approvals | Fixed (`fundraising-approval-discretionary`). |
| M unsupported messages | Donations and activation fixed. The co-host message was rewritten but is now wrong (H1). |
| M typed facts | Fixed (`facts`, `violated_when`, test at test_rules_loader.py:468). |
| M weekend rows | Fixed (`date_to_row`). Gaps remain (L6). |
| M business days | Fixed (earliest-date counting; note corrected). |
| M deadline-table test | Partly fixed (M3). |
| L section/fix item 14; orphan rules; calendar docstring; research note; week-4 and deposit dependencies | Fixed. |
| L duplicate other-funds note | Partly fixed (L3). |
| L brand ambassadors | Partly fixed (wider triggers). |
| L unencoded passages | Not fixed (L5). |
| L table version date | Accepted: `version_date_basis` says it is assumed. |
