# Phase 2, iteration 1 — verify
Summary: 11/11 criteria passed (6 exit criteria + 5 spec checks). Blockers: 0. High: 0. Medium: 3. Low: 6.

Verified on branch `phase-2/event-packet` at a5ac5e7, 2026-11-15. Backend run on port 8012 with `AI_MODE=recorded` set in the shell. The repo `.env` sets `AI_MODE` to something else: `/health` reported `"ai_mode":"live"` on the first start. See L6. Frontend ran on port 5185. I stopped every process I started.

## Exit criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Obligation lists match on at least 27 of 30, and no expected obligation is silently missing | PASS | `python scripts/run_eval.py` printed `events 30 456 0 0 evaluated`. `--json events` notes: "end to end (recorded reading step): 30/30 obligation lists match, 0 silently missing; engine on the test set's attributes: 30/30 match, 1 status/date differences, 30/30 conflict lists match". I called `evaluate()` directly with `AI_MODE=recorded`. Both runs had missing=0 and extra=0. The status differences are all more cautious, never less: end to end, ev-23 `amplified-sound-register` was check_with_office where to_do was expected, and `amplified-sound-90-dba` was check_with_office where condition was expected; in both runs, ev-28 `social-events-not-study-days-finals` was check_with_office where condition was expected. There were no due-date differences. The evaluator's "silently missing" check is weak (M2), but it does not change this result, because nothing was missing. |
| 2 | Every date in the deadline calculator's unit tests is exactly right | PASS | `pytest -q tests/unit/test_deadlines.py` gave 34 passed. That includes a day-by-day independent count for every counted deadline rule from 2026-11-01 to 2028-03-01, and an exhaustive earliest-date check. I recounted these by hand: 2027-01-05 minus 60 days is 2026-11-06; 2026-12-30 plus 3 business days is 2027-01-04; 2027-03-22 minus 10 business days is 2027-03-08; 2028-02-29 minus 3 months is 2027-11-29; 2027-01-31 minus 3 months is 2026-10-31. All are right. I also checked ev-01's packet dates by hand: Feb 26 (6 weeks), Mar 12 (4 weeks), Mar 19 (21 days and 3 weeks), Mar 26 (2 weeks). All correct. Full suite: `pytest -q` gave 386 passed, and `pytest tests/adversarial -q` gave 105 passed. |
| 3 | No date or number in the output was produced by the model | PASS | In `app/services/event_intake.py` the model returns only the year, month, day and weekday the sentence states, plus the headcount as read. Code builds the date in `_build_date`, rejects impossible dates, and rejects a weekday that does not match the date. `as_of` is not sent to the model. `rule_engine.py`, `deadlines.py` and `ics.py` import nothing from `app.ai`. Every due date has `due_note` "…counted by Greenlight's deadline calculator." The ev-28 recording ("sometime in early April") gave event_date null and a question; it did not guess. |
| 4 | "Office decides" items are never shown as green | PASS | I built 4,000 random packets with `build_packet`: random dates from 2026-10 to 2028-06, random subsets of all 52 attributes, possible attributes, all venues, headcounts None/0/1/50/150/10000. The status/verdict pairs seen were only (office_decides, office_decides), (check_with_office, yellow), (blocked, red), (to_do, red/None) and (condition, green/None). There were 0 office_decides, check_with_office or blocked items with a green verdict, and 0 possible-attribute items that were not check_with_office. In the UI (`badgeFor`), office_decides shows the "?" badge labelled "The office decides", as the screenshot shows. |
| 5 | Each known conflict between sources is shown with both citations and the stricter value applied | PASS | ev-01-style packet with decorations: `tes-decorations-terms` vs `-faq` applies terms (3 weeks), and `tes-cancellation-large-terms` vs `-faq` applies faq (4 weeks). Each has 2 citations with source_text, URL and effective date. The all-attributes packet had 9 conflicts. USG pairs choose the stricter one; `usg-deadline-vendor`/`usg-page-deadline-event-date` and the parking pair give `applied: null` and say "follow whichever comes first and check with the office". That is correct when no date can be computed. The random sweep found 0 conflicts with fewer than 2 citations. Rendered page: a "Sources disagree" box shows both quotes and links (headless Chrome). |
| 6 | The .ics file opens in a calendar app (valid RFC 5545) | PASS | `POST /events/packet.ics` returned 200 with `text/calendar; charset=utf-8` and a download header. The `icalendar` library in a separate scratch virtual environment parsed the ev-01 file (7 VEVENTs) and an all-attributes file (23 VEVENTs, with a name containing `;`, `,`, `\`, quotes, accented letters, an emoji and more than 75 octets). Both files: CRLF only, no bare LF, maximum line 75 octets, unique UIDs, every VEVENT has UID, DTSTAMP and DTSTART, and the escaped text decoded back to the original. I did not import it into a desktop calendar app, to avoid changing the user's calendar. Edge case: L4. |
| 7 | Low confidence asks the officer instead of guessing | PASS | `POST /events/parse` with ev-28 gave event_date null, headcount null, `needs_officer_input: ["event_date","headcount"]` and a note. ev-29 ("20 (or maybe 500)") gave headcount null and needs headcount. In the UI the fields show "Please answer" and possible details show "Not sure: tick if true". |
| 8 | Hard blocks for impossible dates | PASS | Each of these gave a hard block: first 3 weeks of spring (2027-01-20); a social event on 2026-12-10 (study days or finals); USG funding on 2026-11-27 (holiday); alcohol on a Monday; alcohol at a dance; an event tomorrow (approvals were due 2026-11-02); minors on 2026-12-12 (registration due 2026-10-13); an event in the past. The API rejected 2027-02-29, an end date before the start date, headcount -1 and an unknown attribute, each with 422. |
| 9 | Fallback options when a deadline has passed | PASS | Event tomorrow: move-date fallback (earliest 2026-12-27) plus a change-format option on each passed item. USG in a break: other_funding fallback. 2,146 of 4,000 random packets had fallbacks. Quality issue: L2. |
| 10 | Timeline page works | PASS | Headless Chrome on http://localhost:5185/events/packet: "Use an example", then "Read my event" (recorded), then "Build the packet" rendered the result. The timeline shows 6 dated items plus the event day in date order, each with an icon and text badge, linked to its card. `npm run build` succeeded. |
| 11 | Keyboard use and labels (PROJECT_CONTEXT section 10) | PASS | I ran the whole flow with keyboard events only (Tab, Shift+Tab, Enter over the Chrome DevTools protocol). The tab order was skip link, nav, textarea, buttons. "Build the packet" was reached after 19 tabs, and the .ics button after that. The focused button has a 3px solid outline. All inputs are inside `<label>` or have `for=`. Badges always carry an icon and text. At 390 px wide the page's scroll width was 390 (no sideways scrolling). Small acronym gaps: L5. |

## Findings

### [medium] Unknown venue: the packet lists no venue obligations at all
Expected: when the venue is unknown, the obligations it would bring in (event permit, all approvals 2 weeks before, the Department of Public Safety, space request, advertising) appear as yellow "check with the office" items, the same way possible attributes do. Nothing should silently drop.
Actual: with `venue: null` the packet has zero obligations. Counts are all 0, and the only output is the question "Where is the event…". For example, `{"event_date":"2027-03-05","headcount":10000}` returns `counts` all 0. The reading step sets venue to null when it is unsure (prompt: "If the sentence names no place at all, set venue to null with low confidence"), so a vague sentence leads to an empty checklist with only a question. The UI also offers "No venue … or not known" as a valid choice that builds the packet. None of the 30 test cases has an unknown venue, so the test set does not catch this.
Reproduce: `curl -s -X POST localhost:8012/events/packet -H 'Content-Type: application/json' -d '{"event":{"event_date":"2027-03-05","headcount":10000},"as_of":"2026-11-15"}'`

### [medium] The evaluator's "silently missing" check covers every case
Expected: a missing expected obligation counts as "not silent" only if a yellow note covers that obligation.
Actual: `scripts/evaluators/events.py` `compare()` sets `yellow_cover = any(o.status == "check_with_office" for o in packet.obligations) or bool(packet.questions)`. One yellow item anywhere in the packet, or any question, covers every missing obligation. Almost every packet has at least one check_with_office item, so the "silently missing" figure for the second half of exit criterion 1 is close to always 0, whatever is missing. It does not change this run's result, because missed = 0.
Reproduce: read `scripts/evaluators/events.py` lines 52–53.

### [medium] Most "office decides" items have no contact-by date
Expected (PROJECT_CONTEXT 4C and 9): "office decides" items are shown as "the office decides — contact them by this date".
Actual: only `dps-security` has a date. In ev-01, `special-event-insurance`, `amplified-sound-outdoor` and `fpm-outdoor-electrical` show "The office decides" with no contact-by date and no note about why there is none. The badge is correct (never green), but the officer gets no date to act by.
Reproduce: build the ev-01 packet (`{"event":{"event_date":"2027-04-09","venue":"venue_outdoor","headcount":150,"attributes":["social_event","amplified_sound","performers","food"]},"as_of":"2026-11-15"}`) and look at the `due` of the office_decides obligations.

### [low] "After" deadlines that have passed are not marked past due
Expected (data/eval/README.md): "`past_due` is true when the due date is before the case's `as_of` date".
Actual: `rule_engine.py:280` sets `past_due` only for `direction == "before"`. For an event on 2026-11-05 with USG funding and as_of 2026-11-15, `usg-post-event-evaluation` and `usg-final-invoices` are due 2026-11-10 but have `past_due: false`. 174 of my random packets had this.
Reproduce: `build_packet(EventFacts(event_date=date(2026,11,5), venue="venue_tes_meeting_room", headcount=20, attributes=["usg_funding","food"]), get_ruleset(), get_calendar(), date(2026,11,15))`

### [low] The "move the date" fallback suggests blocked dates
Expected: the suggested date is usable, or the next date that is not blocked.
Actual: for an event on 2026-11-16 or a social event on 2026-12-10, the fallback is "move to Sunday, December 27, 2026 or later". That date is in winter recess and before spring club events may start (after Jan 26, 2027). A caveat sentence says to "check the new date again", and the engine already has the calendar to do that check itself.
Reproduce: POST `/events/packet` with `{"event":{"event_date":"2026-11-16","venue":"venue_tes_meeting_room","headcount":30,"attributes":["food"]},"as_of":"2026-11-15"}` and read `fallbacks`.

### [low] An .ics with no dated items is an empty VCALENDAR
Expected: RFC 5545 requires at least one component in a VCALENDAR.
Actual: `POST /events/packet.ics` with `{"event":{"venue":"venue_outdoor"}}` returns 200 with a calendar that has no VEVENT. The UI disables the button when the timeline is empty, so only a direct API call reaches this. It could return 422 instead.
Reproduce: `curl -s -X POST localhost:8012/events/packet.ics -H 'Content-Type: application/json' -d '{"event":{"venue":"venue_outdoor"}}'`

### [low] A few office acronyms appear without their full name
Expected (CLAUDE.md, section 10): no office acronym without its full name.
Actual: the `alcohol-requirements` message uses "DPS" and `sponsorship-activation-banned` uses "GSG", both without expansion. "USG" appears without expansion in 35 messages, titles and fallback texts ("ask USG at usgfunds@usc.edu"). For USG, the card's owner line does expand it ("Undergraduate Student Government (USG) Funding Department"); the fallback texts in the hard-block box have no expansion nearby.
Reproduce: build a packet with all attributes and search the titles, messages and fallbacks for `\b[A-Z]{2,6}\b`.

### [low] Status differences in the end-to-end run (more cautious, never less)
Expected: statuses as in the test set.
Actual: ev-23's amplified-sound items and ev-28's study-days item are "check with the office" where to_do or condition was expected. This is not a wrong green, but each case's `cases.json` expectation and the engine disagree. Either the expectation or the reading should be adjusted on purpose.
Reproduce: from `backend/`, `AI_MODE=recorded python -c "…evaluate(load_set('events'), rs)['details']['end_to_end']['details']"`, as in the criterion 1 evidence.

### [low] `python -m app` in this checkout does not start in recorded mode
Expected (run brief and CLAUDE.md): AI_MODE defaults to recorded.
Actual: the code default is recorded (`config.py:47`), but the repo's `.env` sets `AI_MODE`. `/health` returned `"ai_mode":"live"` until I started the app with `AI_MODE=recorded` in the shell. Anyone running the documented command here would call the live API. This is environment configuration, not code. I did not read or print the `.env` values; I listed only the key names.
Reproduce: `cd backend && BACKEND_PORT=8012 python -m app`, then `curl localhost:8012/health`.

Counts: blocker 0, high 0, medium 3, low 6.
