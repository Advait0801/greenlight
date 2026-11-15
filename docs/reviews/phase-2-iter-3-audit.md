# Phase 2, iteration 3 — audit
Summary: 0 blockers, 1 high, 8 medium, 9 low.

Audited on branch `phase-2/event-packet` at `cf5b22e` (working tree as checked out). Commands run:
`pytest -q` (412 passed), `pytest tests/adversarial -q` (128 passed), `python scripts/validate_rules.py` (OK; every `read` rule matches its snapshot), `python scripts/run_eval.py` (events: 456 caught, 0 missed, 0 wrongly flagged; end to end 30/30 lists match, 0 silently missing; 3 status differences end to end, 1 on the engine run, all toward "check with the office").

Exit criteria as audited:
1. 30/30 obligation lists match end to end, 0 silently missing. Met.
2. Calculator unit tests are exact (I recomputed every row in `backend/tests/unit/test_deadlines.py:35-55` by hand, including leap day, month ends, year boundary and business days over a holiday). Met.
3. The model gives only date parts, venue, headcount and details; code builds every date and verdict. Met, with a gap (M5).
4. "Office decides" items never green (`rule_engine.py:167-194`, `Finding` refuses green). Met.
5. Both citations shown for every conflict that reaches the packet. Partly met: two conflicts say "cannot tell which is stricter" although the rule table says which applies (M2); two event-relevant conflicts never reach the packet (M3); the less strict date is still listed as a plain to-do in the timeline and .ics (M1).
6. .ics is well-formed RFC 5545 by inspection and test; no parser or calendar app test (L5).

## Rule check
Source text checked against the snapshots (the validator confirms each `read` quote verbatim; I compared number, unit, anchor and who it applies to by hand for every rule that produces a date or a date check).

| Rule id | Matches source? | Note |
|---|---|---|
| tes-space-request | Yes | "generally at least 3-6 weeks"; 6 weeks used, yellow because hedged. |
| approvals-two-weeks | Yes | "at least two weeks before the event". |
| dps-security | Yes | 2 weeks; DPS decides, shown office decides. |
| tes-final-payment | Yes (number) | 21 days. Source says "For all venues"; rule omits meeting rooms (L4). |
| tes-av-equipment | Yes | 3 weeks. |
| tes-decorations-terms / -faq | Yes | 3 weeks (Terms) vs 2 weeks (FAQ); Terms applied. |
| tes-room-configuration | Yes | 2 weeks. |
| tes-outside-rentals | Yes | 3 weeks. |
| fms-tables-chairs | Yes | 2 weeks. |
| tes-cancellation-meeting-rooms | Yes | 2 weeks. |
| tes-cancellation-large-terms / -faq | Yes | 3 weeks (Terms) vs 4 weeks (FAQ); FAQ applied. |
| social-dance-start | Yes | 3 months. |
| social-dance-events-meeting | Yes | 7 weeks. |
| social-dance-form | Yes | 5 weeks. |
| alcohol-uepa-two-weeks | Yes | 2 weeks. |
| minors-registration | Yes | 60 days before the event date. |
| props-approval | Yes | 2 weeks. |
| fundraising-meeting | Yes | 2 weeks. |
| charity-collection-letter | Yes | 2 weeks. |
| usg-deadline-vendor | Yes | 6 academic weeks before initial payment; undated, yellow. |
| usg-page-deadline-event-date / -nine-weeks-payment | Yes | 6 academic weeks before event / 9 before payment, "whichever comes first". |
| usg-deadline-travel | Yes | 9 academic weeks before initial payment. |
| usg-faq-deadline-new-vendors-travel | Yes | 8 academic weeks before the event date. |
| usg-faq-professional-travel-eight-weeks | Yes | 8 weeks before the travel date. |
| usg-post-event-evaluation / usg-final-invoices | Yes | 3 business days after the final day; every weekday counted (earliest), yellow. |
| usg-incomplete-two-business-days / -48-hours / usg-faq-incomplete-three-business-days | Yes | 2 business days / 48 hours / 3 business days from notification; 48 hours applied. |
| tes-no-events-first-three-weeks | Yes (dates) | "Events can start after January 26". Scope limited to TES venues while the source and spec say RSOs/club events (M7). |
| classroom-requests-week-4 | Yes | "starting Week 4"; week 4 = Monday of the first class week + 3 weeks (Feb 1, 2027). |
| alcohol-thursday-saturday | Yes | Thu-Sat; only the weekday part checked, never green. |
| tabling-hours | Yes | Mon-Fri 10-2; time not known, never green. |
| tabling-blocked-days | Yes | Holidays red; university functions in a separate yellow rule. |
| social-events-not-study-days-finals | Yes | |
| usg-no-funding-breaks | Yes (text) | Applied as green on a summer date although the FAQ answers the summer question with this sentence (H1). |
| usg-faq-no-summer-funding | Yes | Interpretation, correctly yellow. |
| lafd-division-5-permit | Yes (text) | Source: tents "larger than 450 Sq Ft"; engine applies it to every tent (M6). |
| parking-transportation / parking-reservation-required | Yes | "may require" vs "will require"; engine does not apply the stricter (M2). |
| tes-rso-deposits / tes-outdoor-deposit-section-c2 | Yes | $100 vs $200 outdoor deposit; conflict never shown (M3). |

## Findings

### [high] "No USG funding during breaks" shown green for a summer event
Where: backend/app/services/rule_engine.py:138-140, 296; rules/funding.json `usg-no-funding-breaks`, `usg-faq-no-summer-funding`
Problem: For an event in Summer Session 2027 (for example 2027-05-25), `usg-no-funding-breaks` is green ("Meets the rule (date checked)") because the calendar's summer term has no `breaks`. In the same packet `usg-faq-no-summer-funding` is yellow and violated: "Tuesday, May 25, 2027 is outside the fall and spring semesters." USG's own FAQ answers "Can I apply for summer event funding?" with the very sentence this rule quotes, so whether summer counts as a "break" is exactly what is uncertain.
Expected: no green on this rule for a date outside fall and spring; yellow "check with USG" (or blocked as the FAQ implies).
Actual: green verdict with a "date checked" badge, next to a yellow item saying the opposite.
Reproduce:
```python
p = build_packet(EventFacts(event_date=date(2027,5,25), venue="venue_tes_meeting_room", attributes=["usg_funding"]), get_ruleset(), get_calendar(), date(2026,11,15))
o = {x.rule_id: x for x in p.obligations}
assert o["usg-no-funding-breaks"].finding is None or o["usg-no-funding-breaks"].finding.verdict is not Verdict.GREEN  # fails today
```
Why it matters: a wrong green on a funding rule; the trust rule says unsure is yellow, never green.
Suggested fix: in `_date_check` for `usg-no-funding-breaks`, return `confirm=True` (yellow) when any day falls in a summer term or outside every term; add the test above.

### [medium] The less strict side of a conflict is still listed as an ordinary to-do in the timeline and .ics
Where: backend/app/services/rule_engine.py:339-343; backend/app/services/ics.py:74-82; frontend/src/components/EventTimeline.tsx:12-17
Problem: For a decorated event in the Trojan Grand Ballroom on 2027-04-17 the .ics holds both "To do: Decorations approved 3 weeks before (Terms and Conditions)" on 2027-03-27 and "To do: Decorations approved 2 weeks before (FAQ)" on 2027-04-03. Neither the obligation, the timeline entry nor the .ics description says that the later date is superseded; only the separate "Sources disagree" box does, and it is not in the .ics at all.
Expected: the stricter value applied everywhere the date appears (exit criterion 5); the less strict entry marked "not applied, see conflict" or dropped from the timeline and .ics.
Actual: two to-dos for the same approval, the later one looking as valid as the earlier.
Reproduce: `build_packet(EventFacts(name="Gala", event_date=date(2027,4,17), venue="venue_tes_large", attributes=["decorations"]), ...)` then `packet_to_ics(...)`; grep SUMMARY lines.
Suggested fix: after `_conflicts`, mark obligations on the non-applied side (`ruleset.less_strict_side` already exists, `loader.py:93`) and either leave them out of `timeline`/.ics or prefix them "Not applied (sources disagree)"; test that no non-applied rule appears in the .ics as "To do".

### [medium] Two known conflicts say "cannot tell which is stricter" although the rule table says which applies
Where: backend/app/services/deadlines.py:113-125 (equal lead returns None before the anchor order is used); rule_engine.py:379-385; rules/events.json `parking-reservation-required` message; rules/funding.json `usg-page-deadline-event-date` message
Problem: (a) `parking-transportation` ("may require") vs `parking-reservation-required` ("will require"): `applied` is None and the explanation says "Greenlight cannot tell which is stricter ... check with the office", while the rule's own message says "Greenlight applies 'will require' and shows both". (b) `usg-deadline-vendor` (6 academic weeks before first payment) vs `usg-page-deadline-event-date` (6 academic weeks before the event): equal leads return None at line 120, so the anchor rank (payment never after event, the assumption used two lines later for unequal leads) is never consulted. The rule message says "Greenlight shows the earliest of these".
Expected: the stricter one applied and named, consistent with the rule messages (exit criterion 5).
Actual: `applied: null` for both pairs (see `source_conflicts` of any packet with `outside_guests_parking` or `usg_funding`).
Reproduce: `build_packet(EventFacts(event_date=date(2027,4,17), venue="venue_tes_large", attributes=["outside_guests_parking","usg_funding"]), ...)`; both conflicts have `applied is None`.
Suggested fix: for equal leads with different anchor ranks return the earlier anchor; for requirement pairs, carry the applied side in the rule table (for example `params.applied_in_conflict`) and use it. Test both pairs.

### [medium] Two event-relevant conflicts never reach the packet
Where: backend/app/services/rule_engine.py:33-34, 367-392 (only rules in scope are compared); rules/events.json `tes-rso-deposits` / `tes-outdoor-deposit-section-c2`; rules/funding.json `usg-missed-deadline-denial` / `usg-faq-late-travel-director-discretion`
Problem: both pairs are `kind: info`, so neither side is an obligation and the conflict is silently dropped. The outdoor deposit ($100 vs $200, a sum the club pays) is never shown for an outdoor event. A Professional/Academic travel request whose academic-week deadline has "certainly passed" is hard-blocked (rule_engine.py:304-308, 416-417) while the FAQ says late travel is at the Funding Director's discretion; that conflict is not shown.
Expected: "Each known conflict between sources is shown with both citations."
Actual: no conflict entry for either pair in any packet (checked by building packets with every vocabulary attribute for every venue type).
Reproduce: `build_packet(EventFacts(event_date=date(2027,4,15), venue="venue_outdoor", attributes=[...all names...]), ...)`; `source_conflicts` holds neither pair.
Suggested fix: include conflicting `info` rules whose triggers match as informational conflict notes (or as info obligations), with both citations; test that an outdoor event shows the deposit conflict.

### [medium] Top-level fallback claims "every passed deadline is met" when it is not
Where: backend/app/services/rule_engine.py:344-349; deadlines.py:86-98
Problem: the move date is the latest of the counted-unit fallbacks only. Academic-week deadlines that have "certainly passed" contribute nothing. For an event on 2026-11-25 with `usg_funding` (as of 2026-11-15) the packet says "Every passed deadline is met if the event moves to Sunday, December 27, 2026 or later". Six academic weeks before Dec 27 is no later than Nov 15 even counting calendar weeks, and Dec 27 is in winter break, when USG funds nothing.
Expected: no statement that every passed deadline is met unless every passed deadline was counted; academic-week deadlines named as not covered.
Actual: an unconditional claim (with a generic "check the new date again").
Reproduce: `build_packet(EventFacts(event_date=date(2026,11,25), venue="venue_tes_meeting_room", attributes=["usg_funding","food"]), ..., date(2026,11,15)).fallbacks[0].text`.
Suggested fix: word it "Every passed deadline Greenlight can date is met ..." and list the undated ones; or use `offset * 7` days as a lower bound for academic weeks in the move date. Test the wording.

### [medium] Date parts and headcount from the model are not checked against the sentence
Where: backend/app/services/event_intake.py:158-181, 214
Problem: the code trusts any high-confidence year, month, day and headcount the model returns. The prompt asks it not to fill a missing year, but nothing checks that the year (or the headcount) appears in the officer's text or in `evidence`, or that `evidence` is a substring of the sentence. "Culture night on Friday, April 9" with a model-supplied year would give a dated packet with every deadline worked back from a year the officer never typed (a matching weekday only narrows it).
Expected: "No date or number in the output was produced by the model" enforced in code, not only in the prompt.
Actual: no such check; all 30 test sentences state the year, so the eval cannot show it.
Reproduce: unit test with `_reading(... start={"year": 2027, "month": 4, "day": 9, "weekday": None, "confidence": "high", "evidence": "April 9"})` for sentence "Culture night on April 9 at McCarthy Quad"; `facts.event_date == date(2027,4,9)` today.
Suggested fix: require the year's digits and the day number to appear in the sentence (and the headcount's digits, or a number word), else treat as unsure and ask. Pass the sentence into `facts_from_reading`.

### [medium] The fire-permit requirement fires on every tent; the source says tents larger than 450 sq ft
Where: rules/events.json `lafd-division-5-permit` (triggers `open_flame`, `tent`; `params.tent_area_sqft_over` 450 unused); backend/app/services/rule_engine.py:83
Problem: the engine never reads the 450 sq ft condition, so a 10x10 canopy gets a red "To do: Los Angeles Fire Department Division 5 permit". Who the rule applies to is wider than the source ("Tents, canopies, or membrane structures with an area larger than 450 Sq Ft").
Expected: required for tents over 450 sq ft; for a tent of unknown size, "check with the office" (yellow).
Actual: `to_do` for any tent.
Reproduce: `build_packet(EventFacts(event_date=date(2027,4,15), venue="venue_outdoor", attributes=["tent","outside_rentals"]), ...)`; `lafd-division-5-permit` status `to_do`.
Suggested fix: add a fact such as `tent_over_450_sqft` to the vocabulary; with `tent` alone show yellow "applies if the tent is over 450 square feet".

### [medium] "No club events in the first three weeks" is silent for classroom and off-campus events
Where: rules/events.json `tes-no-events-first-three-weeks` triggers (TES venues only); PROJECT_CONTEXT.md section 7 "No club events | First 3 weeks of a semester"
Problem: a club social in a Taper Hall classroom or off campus on 2027-01-20 gets no item about the rule (the classroom one only gets the unrelated week-4 note). The source sentence reads "RSOs can not host events the first 3 weeks", and the spec lists it as a rule for club events, owned by TES and Student Life. The breaker raised this as an open question; it has not been answered.
Expected: at least a yellow "check with Trojan Event Services / Student Life" for non-TES venues in that window.
Actual: nothing.
Reproduce: `build_packet(EventFacts(event_date=date(2027,1,20), venue="venue_off_campus", attributes=["social_event"]), ...)`; no `tes-no-events-first-three-weeks`.
Suggested fix: trigger on every venue; keep red for TES venues and yellow for the others until a person confirms.

### [medium] Most "office decides" items have no contact-by date
Where: backend/app/services/rule_engine.py:301-302 (due only for `kind: deadline`); PROJECT_CONTEXT.md 4C
Problem: the spec says office-decides items are "shown as a contact-by date". `special-event-insurance`, `amplified-sound-outdoor`, `parking-transportation`, `campus-filming`, `dignitaries-clearance`, `fpm-outdoor-electrical`, `sterno-guidelines` have none. This was left open in iteration 1 (M3).
Expected: a contact-by date, for example the `approvals-two-weeks` date ("all required approvals at least two weeks before"), cited.
Actual: `due: null`.
Suggested fix: give office-decides requirements on TES venues the approvals-two-weeks date as "contact them by", citing that rule; otherwise say why there is no date.

### [low] Answer key and engine disagree on three statuses (always toward yellow)
Where: data/eval/events/cases.json ev-28 (`social-events-not-study-days-finals` expected `condition` with no date), ev-23 (`amplified-sound-*` end to end).
Problem: the engine is right for ev-28 (no date means no check); the answer key is wrong. The evaluator prints the count but does not fail on it.
Suggested fix: correct ev-28's key to `check_with_office`.

### [low] Stricter-of and date checks written twice
Where: backend/app/eval_sets.py:150-180 (own stricter logic, only same unit and anchor), 345-375 (`_decided_violation` hard-codes alcohol weekdays as `(3, 4, 5)` instead of `params.allowed_weekdays`); deadlines.py:101-131; rule_engine.py:109-164
Problem: two implementations can drift; one ignores the rule's params.
Suggested fix: have the validator call `deadlines.stricter_of` and read weekdays from params.

### [low] Final payment rule omits meeting rooms although the source says "For all venues"
Where: rules/events.json `tes-final-payment` triggers
Problem: defensible because RTCC meeting rooms are free for clubs, but AV and staffing charges can still apply there. The rule does not record why.
Suggested fix: add a note, or include meeting rooms as yellow when `av_equipment` is present.

### [low] No parser-based test that the .ics opens
Where: backend/tests/integration/test_events_api.py:49-67
Problem: the test checks structure by string matching. Exit criterion 6 is about a calendar app opening it; nothing parses it with an iCalendar library or records a manual import.
Suggested fix: parse with the `icalendar` package in a test, or record a manual import (Apple Calendar or Google) in docs/PROGRESS.md.

### [low] Hard blocks have no citation
Where: backend/app/services/rule_engine.py:407-418; frontend/src/pages/EventPacket.tsx (hard_blocks list)
Problem: hard blocks are plain strings; the rule and source link are only on the obligation card further down.
Suggested fix: return `rule_id` with each block and link it to `#ob-<rule_id>`.

### [low] `_certainly_passed` assumes the first payment is never after the event
Where: backend/app/services/rule_engine.py:395-404; deadlines.py:105-106, 134-136
Problem: if a vendor's first payment falls after the event (invoice after delivery), "6 academic weeks before the payment" can be later than 6 weeks before the event, and the "has already passed" hard block would be wrong. The assumption is not sourced.
Suggested fix: state the assumption in the note, or count payment-anchored rules as undated unless a payment date is given.

### [low] `/events/parse` has no rate limit and writes audit rows with no club
Where: backend/app/api/events.py:65-80
Problem: once deployed with `AI_MODE=live`, anyone can call the paid model repeatedly, and each call writes an `AuditLog` row with `club_id=None` holding evidence quotes from the sentence. No club data is returned, so this is not a leak.
Suggested fix: a simple per-IP limit on `/events/parse`; tie the log row to a club once clubs exist.

### [low] Comment says the first-three-weeks source names spring dates only
Where: backend/app/services/rule_engine.py:128
Problem: the TES FAQ snapshot also says fall events "can start after September 22" (rules/sources/tes-faq.txt:12). This has no effect now (fall 2026 is past), but the comment and the officer-facing text ("the source gives dates for spring 2027 only") are inaccurate.
Suggested fix: reword to "Greenlight has dates for spring 2027 only".

### [low] Past-due "office decides" deadlines are not hard blocks
Where: backend/app/services/rule_engine.py:411-417
Problem: for an event 10 days away, "Contact the Department of Public Safety 2 weeks before" has passed but only shows "(passed)" on its card; it is not in the hard blocks list, unlike passed to-do items.
Suggested fix: list passed office-decides contact dates among the hard blocks (as "contact them now").

Counts: blocker 0, high 1, medium 8, low 9.
