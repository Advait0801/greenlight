# Phase 0, iteration 3 — audit
Scope: auditor (a), `rules/funding.json` against its sources. Commit `9c3f500`.
Summary: 0 blockers, 2 high, 8 medium, 13 low.

How I checked: I read every rule in `rules/funding.json` (69 rules) next to `rules/sources/usg-funding-guidelines.txt`, `usg-funding-page.txt`, `usg-funding-faq.txt`, `usg-funding-deadlines.txt` and the two vendor-list snapshots. I also ran my own check, separate from the loader: whitespace-collapsed `source_text` against each snapshot, and `effective_date` against the manifest `version_date`. All 69 match, including the 3 unverified rules. For the passages that matter most, I grepped the raw downloads in `rules/sources/raw/` (page "and or nine academic weeks", "up to 4 events", "Restaurant diners", the doubled "six academic weeks", FAQ "three business days", "eight academic weeks", "four week deadline"). They match. `python scripts/validate_rules.py` gives OK (funding 69, read 254, unverified 5). `pytest` gives 208 passed. I did not change any file other than this report.

No rule's number, unit, anchor or direction differs from the text it quotes. Every `read` quote is in its snapshot, and all 18 ineligible items are encoded. The open questions from PROJECT_CONTEXT section 8 (deadline table / academic weeks, 4 events per semester, vendor list) are marked `unverified`, and the rules that rest on them inherit yellow. The iteration 1 fix M3 (`usg-approved-vendor` depends on `usg-vendor-list`) is in place, and `test_vendor_and_caterer_rules_rest_on_their_unverified_lists` covers it. The problems are in what the rules leave out, and in a few messages, scopes and vocabulary choices that say more than the source does.

## Rule check
| Rule id | Matches source? | Note |
|---|---|---|
| usg-academic-week-definition | Yes | Guidelines l.41. Unverified, yellow: correct. Notes treat "N/A" and blank rows the same (L10). |
| usg-deadline-vendor | Yes | Guidelines l.36: 6 academic weeks before the initial payment due date, approved vendors. Message adds "denied automatically" from another passage (L1). |
| usg-page-deadline-event-date | Partly | Page l.49. Encodes only "6 weeks before event date". The quoted sentence's second clause, "nine academic weeks before the initial payment due date (whichever comes first) for approved USC Vendors", is not encoded (H1). |
| usg-deadline-travel | Yes | Guidelines l.38: 9 academic weeks before the initial payment, airfare/ground/overnight hotel. Note claims "the stricter", which is not always true (M3). |
| usg-faq-deadline-new-vendors-travel | Yes | FAQ l.26: 8 academic weeks before the event date. Message ("applies the guidelines") and fix ("the earlier") disagree (M3). Does not list its conflict with usg-deadline-vendor (L11). |
| usg-missed-deadline-denial | Yes | Guidelines l.39. "There is no written appeal process" is not in the source, and the FAQ's Professional Fund passage gives the Director discretion over late travel (M2, L1). |
| usg-application-window | Yes | Guidelines l.35. "Money is given first come, first served" overstates "reviewed on a first come first serve basis" (L2). FAQ's 8:00 AM opening is not recorded (L12). |
| usg-no-funding-breaks | Partly | Guidelines l.40. Encodes the event half. "Does not process applications … during" is not encoded (M4). Summer is not blocked (H2). |
| usg-post-event-evaluation | Yes | Guidelines l.42: 3 business days after the final day. Depends on the business-day definition: correct. Agrees with FAQ #12. |
| usg-post-event-photos | Yes | Guidelines l.43. |
| usg-final-invoices | Yes | Guidelines l.44. Message softens "will result in disciplinary action" to "can lead to", from an unquoted bullet (L1). |
| usg-funding-modules | Yes (text) | Guidelines l.47. Severity `info` understates FAQ #2, "Organizations that have not gone through this process will not receive funding" (M5). |
| usg-quote-required | Yes | Guidelines l.53. |
| usg-cart-screenshot | Yes | Guidelines l.54. |
| usg-amazon-wishlist | Yes | Guidelines l.55. |
| usg-traveler-information | Yes | Guidelines l.57. Six fields correct. Message says details are not stored (matches section 9). |
| usg-hotel-point-of-contact | Yes | Guidelines l.58. |
| usg-travel-statement-of-purpose | Yes | Guidelines l.60. |
| usg-conference-logins | Yes | Guidelines l.61. Yellow is conservative. No "not stored" statement for credentials (L5). |
| usg-esr-on-campus | Yes | Guidelines l.62. "Event Status Report" is confirmed by tes-terms l.241. Triggers leave out `venue_classroom` (L13). |
| usg-hospitality-food-form | Yes (text) | Guidelines l.63 is a sub-bullet of "ESRs for on campus events". The trigger `food` applies it to off-campus events too (L6). |
| usg-uepa-event-id | Yes | Guidelines l.64. Expansion confirmed by the handbook. Yellow fits "if applicable". |
| usg-incomplete-two-business-days | Yes | Guidelines l.65. FAQ #16 says **three** business days. No conflict is recorded (M1). |
| usg-incomplete-48-hours | Yes | Guidelines l.67. 48 h is never later than 2 business days, so "earlier" is right. Same-source conflict (L11). |
| usg-yearly-cap | Yes | Guidelines l.78: $8,000 per organization per year. Source caps money *received*; the check sums "usg_funding_this_year" (L8). |
| usg-venue-personnel-cap | Partly | Guidelines l.79: $4,000. Message and applies_to add "for an event". The check caps the total cost, not USG's share (M6). |
| usg-over-4000-case-by-case | Yes | Guidelines l.80: office_decides. Total-expense reading is noted. |
| usg-multi-day-case-by-case | Yes | Guidelines l.81: office_decides. |
| usg-fund-closure | Yes | Guidelines l.82: 50%, CFO "reserves the authority": "may close". |
| usg-events-per-semester-cap | Yes | Page l.47. Unverified, shown yellow. The FAQ document (#4) gives only the $8,000 cap, which supports keeping it unverified. |
| usg-fund-professional-academic | Yes | Guidelines l.84. "Research & Fieldwork Supplies (Case-by-Case Basis)" not encoded (L12). |
| usg-professional-free-open | Yes | Guidelines l.89. |
| usg-fund-philanthropy | Yes | Guidelines l.93. |
| usg-philanthropy-no-service-payments | Yes | Guidelines l.96. FMS estimate requirement (l.97) not encoded (L12). |
| usg-fund-social-recreation-startup | Yes | Guidelines l.98. "Two academic semesters (fall or spring)" kept. |
| usg-tshirts-licensed-vendor | Yes | Guidelines l.102. |
| usg-fund-performing-visual-arts | Yes | Guidelines l.105. Example params "performances", "exhibitions" are not in the source (harmless). |
| usg-pva-po-vendor | Yes | Guidelines l.107. |
| usg-food-case-by-case | Yes | Guidelines l.112: office_decides. |
| usg-food-justification | Yes | Guidelines l.113. |
| usg-food-health-permit-insurance | Yes | Guidelines l.114. |
| usg-food-cap | Yes | Guidelines l.115: $35 per person, expected attendance. Fix suggests raising headcount (L3). |
| usg-lodging-case-by-case | Yes | Guidelines l.116: office_decides. |
| usg-hotel-price-comparison | Yes | Guidelines l.117. Fix says "at least one other hotel"; source says "other hotels" (L4). |
| usg-hotel-cap | Yes | Guidelines l.119: $400 per night. |
| usg-lodging-justification | Yes | Guidelines l.120. |
| usg-approved-vendor | Yes | Guidelines l.37. Depends on the vendor list, so yellow (iteration 1 M3 fixed). Conflict with FAQ new vendors listed both ways. |
| usg-vendor-list | Text present (unverified) | Vendor list l.11. The quoted note is about incomplete PO registration, not "list not complete". Only the Food tab URL is cited (L9). |
| usg-ineligible-reimbursements | Yes | Guidelines l.123–142. Exception note matches l.142. Agrees with FAQ #21. |
| usg-ineligible-charity | Yes | |
| usg-ineligible-alcohol | Yes (text) | Trigger `alcohol` is also the event attribute "Alcohol present or served"; the source bans the expense (M7). |
| usg-ineligible-gifts | Yes | |
| usg-ineligible-durable-goods | Yes | FAQ's durable-good definition (3+ years, glass vs paper plates) not recorded (L12). |
| usg-ineligible-raw-food | Yes | |
| usg-ineligible-restaurant | Yes | "Restaurant diners" is quoted as written. The reading as "meals" is stated openly. |
| usg-ineligible-rideshare | Yes (text) | Source puts "Buses" here; vocabulary calls a chartered coach eligible `ground_transport` (M8). |
| usg-ineligible-deposits-fees | Yes | |
| usg-ineligible-peer-to-peer | Yes | |
| usg-ineligible-performers | Yes (text) | Vocabulary puts "speakers' fees" under performer_fee: an interpretation (L7). |
| usg-ineligible-subscriptions | Yes | |
| usg-ineligible-ticketed-events | Yes | Agrees with outside_money `ticket-sales-cover-costs`. |
| usg-ineligible-closed-on-campus-events | Yes | |
| usg-ineligible-private-residences | Yes | |
| usg-ineligible-international-travel | Yes | |
| usg-ineligible-jewelry | Yes | |
| usg-ineligible-balloons | Yes | |
| usg-denial-reasons | Yes | Guidelines l.148–153. "Never predicts a decision": good. Section 6 permanent-ban text not recorded (L12). |
| usg-denial-same-day-events | Yes | Guidelines l.151. Yellow. |
| usg-denial-other-university-funding | Yes | Guidelines l.152. Yellow, as PROJECT_CONTEXT section 7 requires. |

## Findings

### [high] H1. The web-page deadline rule drops the 9-week clause it quotes
Where: rules/funding.json:61-91 (`usg-page-deadline-event-date`; source_text l.70, message l.74, anchor/offset l.81-84); source rules/sources/usg-funding-page.txt:49
Problem: The quoted sentence has two parts: "six academic weeks before the event date when using an approved vendor, **and or nine academic weeks before the initial payment due date (whichever comes first) for approved USC Vendors**." The rule encodes only the first part: anchor `event_date`, offset 6. Nothing encodes "9 academic weeks before the initial payment due date" for approved vendors, and no note explains why it was left out. In the message, "whichever deadline comes first" is presented as Greenlight's own choice between the page and the guidelines. On the page, "whichever comes first" chooses between 6 weeks before the event and 9 weeks before the initial payment.
Why it matters: When the first payment is due close to the event date, 9 weeks before the payment is earlier than both encoded deadlines (6 weeks before the event, 6 weeks before the payment). PROJECT_CONTEXT section 9 says to apply the stricter source and cite both. As encoded, Greenlight can show a later date than the page's own reading. The rule says less than the source it quotes. The date is yellow (academic weeks unverified), but it would still be the wrong yellow date.
Suggested fix: Add a second page rule (`anchor: initial_payment_due_date`, `offset: 9`, `academic_weeks`) with mutual conflicts. Or put the clause in the rule's notes with a stated reason and a `verification_note`, since the page sentence is garbled ("and or"). Change the message so it does not credit "whichever comes first" to Greenlight.

### [high] H2. Summer events are not blocked from USG funding
Where: rules/funding.json:209-240 (`usg-no-funding-breaks`, params.blocked l.228-235); rules/calendar.json:94-118 (summer-2027 has `"breaks": []`); source rules/sources/usg-funding-faq.txt:19-20; rules/sources/usg-funding-deadlines.txt:44 (table ends with week 2027-04-26)
Problem: FAQ #6 asks "Can I apply for summer event funding?" and answers with the holidays/breaks/study days/finals sentence, which means no. No rule encodes this. The blocked-period rule uses the calendar's holidays, breaks, study days and finals. The calendar models Summer Session 2027 as a term with only three holidays, and the gaps May 13-18 and Aug 11-23 are not breaks. The deadline table has no rows after April 30, 2027.
Why it matters: A USG-funded event on, say, June 15, 2027 gets no blocked-period finding at all: a silent pass where the source implies a block. This breaks "nothing unverified is presented as certain". It is also the Phase 2 exit criterion that no expected obligation is silently missing.
Suggested fix: Add a rule quoting FAQ #6 (question and answer), kind `blocked_period`, for events outside the fall and spring semesters. Mark it `unverified` or yellow with a note ("the FAQ implies no summer funding; confirm with usgfunds@usc.edu"). Also treat event weeks the deadline table does not list as "no USG deadline listed: check with USG", never as fundable.

### [medium] M1. FAQ's "three business days" for incomplete applications is not recorded as a conflict
Where: rules/funding.json:566-623 (`usg-incomplete-two-business-days`, `usg-incomplete-48-hours`); source rules/sources/usg-funding-faq.txt:39-40
Problem: FAQ #16: "you will have three business days to provide the necessary information before your application is denied." The guidelines say 2 business days (= 48 hours). The FAQ rule set records the travel/vendor disagreement (8 vs 9 weeks) but not this one.
Why it matters: PROJECT_CONTEXT section 9 says "Where official sources disagree, the stricter rule is applied and both are cited." The stricter value is already applied, but an officer reading USG's FAQ will see a different number with no explanation.
Suggested fix: Add `usg-faq-incomplete-three-business-days` (FAQ source, offset 3, business_days, depends on the business-day definition) with `conflicts_with` both incomplete rules.

### [medium] M2. The FAQ's Professional Fund travel passage is not encoded and contradicts "automatically denied"
Where: rules/funding.json:92-126 (`usg-deadline-travel`), 163-183 (`usg-missed-deadline-denial`, message l.176); source rules/sources/usg-funding-faq.txt:69-70
Problem: "Travel expense requests (airfare and hotel) must be made at least eight weeks prior to the date of travel … Applications received within this four week deadline, or eight week deadline in the event of air travel requests, will be considered at the discretion of the Director of the Academic Fund." This is a third version of the travel deadline: plain weeks, counted from the travel date. It also makes late travel requests discretionary, not automatically denied. `usg-missed-deadline-denial` says "denied automatically. There is no written appeal process."
Why it matters: Sources disagree on the deadline and on what happens when it is missed. Only one side is shown. Presenting automatic denial as certain for Professional Fund travel is more certain than the sources allow.
Suggested fix: Add a FAQ rule for this passage, with conflicts against `usg-deadline-travel` and `usg-missed-deadline-denial`. Its late-application part should be `office_decides`. Remove "There is no written appeal process" from the message, or source it.

### [medium] M3. Conflict-resolution wording is inconsistent, and "stricter" is asserted where it is not guaranteed
Where: rules/funding.json:74 ("uses whichever deadline comes first"), 125 ("applies the guidelines' 9 weeks (the stricter)"), 140 ("Greenlight applies the guidelines and shows both"), 141 ("Apply by {due_date}, the earlier of the deadlines"), 1184
Problem: The vendor-deadline pair says "earliest date wins". The travel pair says "the guidelines win". The FAQ rule's message and fix_template contradict each other. 9 weeks before the *initial payment due date* is not always earlier than 8 weeks before the *event date*. When a payment falls due after the event, the FAQ date is earlier.
Why it matters: The officer is told two different policies. If the engine follows "apply the guidelines", it can show a later date than one cited source. That breaks the stricter-rule principle.
Suggested fix: One policy for every USG deadline conflict: compute every conflicting date and show the earliest, citing all. Make messages, fix templates and notes say exactly that. Drop "(the stricter)" from l.125.

### [medium] M4. "Does not process applications during breaks" is not encoded
Where: rules/funding.json:209-240 (`usg-no-funding-breaks`, source_text l.218); also FAQ l.20
Problem: The sentence covers two things: USG "does not process applications **or** provide funding for events during University holidays, breaks, study days, or finals". The rule encodes only events. Nothing stops a computed submission deadline from landing on a Wednesday in Thanksgiving week, finals, or winter recess (e.g. 2026-11-25, 2026-12-09, 2027-01-06). The hand-transcribed table skips exactly those Wednesdays (deadlines jump from 2026-11-18 to 2027-01-13).
Why it matters: A deadline calculator built from the rule table, not the table snapshot, would give dates on which USG takes no applications.
Suggested fix: Record the application half: a param such as `"applies_to_submission": true`, or a second rule. Cite the table rows that show the skipped Wednesdays.

### [medium] M5. Module and recognition eligibility shown as `info`
Where: rules/funding.json:320-340 (`usg-funding-modules`, severity l.332); source rules/sources/usg-funding-faq.txt:11-12
Problem: FAQ #2: only organizations that "have gone through the re-recognition process … and have completed the Funding Guidelines module are eligible … Organizations that have not gone through this process will not receive funding." The rule quotes only the guidelines' softer "make sure to complete" and is `info`, so it can never fail. Nothing encodes the eligibility requirement.
Why it matters: An unrecognised club, or one whose officers skipped the module, gets no warning. The FAQ says it will receive nothing.
Suggested fix: Add a FAQ #2 eligibility rule (red, or yellow until it can be checked against the readiness tracker), and link it to the recognition rules.

### [medium] M6. Venue and personnel cap: "per event" and "total cost" are not in the source
Where: rules/funding.json:650-679 (`usg-venue-personnel-cap`; message l.663, applies_to l.665, check l.666)
Problem: Source (guidelines l.79, under "Maximum Funding per Academic Year"): "will provide funding for up to $4,000 of the total cost associated with on-campus venue rentals and personnel." It does not say per event. The message adds "for an event". The check `sum(venue_rental + personnel) <= 4000` compares the *total cost* with the cap. The source limits what USG *pays*: a club may spend more on the venue and cover the rest itself.
Why it matters: A red would fire on an event whose venue costs $5,000 even when the club asks USG for only $4,000. Whether the cap is per event or per year is an interpretation shown as certain.
Suggested fix: Check the USG-requested amount for these categories. Note the per-event reading in `notes`, and either mark it for confirmation or show it yellow until USG confirms.

### [medium] M7. `usg-ineligible-alcohol` fires on events where alcohol is merely present
Where: rules/funding.json:1262-1286 (triggers l.1279-1281); rules/vocabulary.json:11 (event attribute "Alcohol present or served") and :50 (line category)
Problem: The source makes "Alcoholic beverages" ineligible as an expense. `alcohol` is both an event attribute and a budget category, so the rule also fires on an event where a venue or cash bar serves alcohol that USG is not asked to pay for. The `applies_to` text ("A budget line or event that is: Alcoholic beverages") hides the difference. The iteration 2 year-plan key now expects this at event level (yp-02).
Why it matters: A red "USG does not fund alcoholic drinks" on an event with no alcohol line is a false flag, and the rule applies to more than its source says.
Suggested fix: Restrict the rule to the line category (a separate line-level trigger name, or `trigger_mode: all` with `usg_funding` plus a line category). For event-level alcohol, show at most an info note.

### [medium] M8. Vocabulary treats a chartered coach as eligible though the guidelines list "Buses" as ineligible
Where: rules/vocabulary.json:65-66; rules/funding.json:92-126 (triggers include `ground_transport`), 1387-1411 (`usg-ineligible-rideshare`); sources: guidelines l.38 ("transportation (airfare or ground)") and l.131 ("Rideshare costs (Uber, Lyft, Buses, Vans, Amtrak cabins, Car rentals, etc.)"); usg-vendor-list-other.txt:80-81 ("Buses", "Fast Deer Bus Charter")
Problem: The sources disagree. Ground transport is a travel expense with a 9-week deadline, but buses are ineligible, and USG's vendor list has a "Buses" section. The vocabulary settles this by defining `ground_transport` as "such as a chartered coach" (eligible), and no rule records the disagreement.
Why it matters: A charter bus would get a travel deadline and no ineligibility finding. That is a fundability verdict the source does not support.
Suggested fix: Remove the "chartered coach" example, or route bus/coach lines to yellow "ask USG". Record the conflict between `usg-deadline-travel`'s "ground" and the rideshare item in notes or `conflicts_with`.

### [low] L1. Messages state things their quoted text does not
Where: rules/funding.json:42 ("A late application is denied automatically"), 176 ("There is no written appeal process"), 304 ("Late invoices can lead to disciplinary action")
Problem: Each claim comes from a different passage, or from none. l.304 also softens the source's "will result in disciplinary action and potential loss of future funding privileges" (guidelines l.45) to "can lead to".
Why it matters: The citation shown with the finding does not support the sentence.
Suggested fix: Extend `source_text` to the adjacent bullet, or remove the claim. Use the source's "will result in".

### [low] L2. "Money is given first come, first served"
Where: rules/funding.json:197
Problem: The source says applications "will be reviewed on a first come first serve basis until all funds are exhausted". The message suggests earlier applications get money.
Suggested fix: "USG reviews applications first come, first served until funds run out."

### [low] L3. Food-cap fix nudges officers to raise expected attendance
Where: rules/funding.json:1054
Problem: "or plan for at least {min_headcount} people" invites inflating the attendance figure the cap is based on.
Suggested fix: "If you genuinely expect more people, update the expected attendance."

### [low] L4. Hotel price comparison fix asks for less than the source
Where: rules/funding.json:1101
Problem: The source wants "proof of price comparison with other hotels". The fix says "at least one other hotel" and specifies screenshots.
Suggested fix: "Add proof of prices from other hotels."

### [low] L5. Conference log-ins: no promise not to store credentials
Where: rules/funding.json:477-497 (message l.490)
Problem: The rule asks officers to include registration log-in details. Unlike `usg-traveler-information` (l.417), it does not say Greenlight only checks presence and stores nothing. Credentials are more sensitive than traveller details.
Suggested fix: Add the same "Greenlight only checks that these are present and does not store them" wording, and make sure no later intake path keeps them.

### [low] L6. Hospitality food form applied to off-campus events
Where: rules/funding.json:521-541 (triggers l.537-539); guidelines l.62-63
Problem: The requirement is a sub-bullet of "ESRs for on campus events". The trigger `food` applies it everywhere.
Suggested fix: `trigger_mode: all` with `food` and an on-campus venue, or yellow for off-campus events.

### [low] L7. Speakers' fees are classed as payments to talent
Where: rules/vocabulary.json:63; rules/funding.json:1463-1487
Problem: The source says "talent or performers". Treating a guest speaker as talent is an interpretation, though USG's vendor list files speaker agencies under "Agencies/Talent" (usg-vendor-list-other.txt:13,15). It is shown as a certain red.
Suggested fix: Note the reading in `notes`, or show speaker lines as yellow.

### [low] L8. Yearly cap: received versus requested
Where: rules/funding.json:640, 638
Problem: The source limits what an organization "may receive". `sum(usg_funding_this_year)` does not say whether it counts denied or pending requests.
Suggested fix: Define the sum as received plus approved plus this request, and say so in `check`.

### [low] L9. `usg-vendor-list` quotes a passage that does not support its message
Where: rules/funding.json:1186-1211 (source_text l.1195, fix l.1201)
Problem: The quote is a sheet note about vendors whose PO registration is incomplete. The message is about the list being incomplete and changing, which is guidelines l.37. The Other Vendors tab (a separate manifest source) is never cited. The Purchasing phone number comes from the TES FAQ (`usc-approved-caterers`).
Suggested fix: Cite guidelines l.37 for the message, and cite both tabs.

### [low] L10. Academic-week notes merge two kinds of missing deadline
Where: rules/funding.json:27; rules/sources/usg-funding-deadlines.txt:10-18
Problem: The notes say weeks without a deadline "have no USG funding". The first six fall weeks are "N/A" (the deadline would fall before applications open). Winter and spring recess are blank. These are different situations.
Suggested fix: Describe the two cases separately.

### [low] L11. Conflict lists incomplete or outside their definition
Where: rules/funding.json:154-157, 589-591, 620-622
Problem: The FAQ rule's 6-weeks-before-event clause conflicts with `usg-deadline-vendor` exactly as the page does, but is not listed. The two incomplete-application rules come from the same source, while README's `conflicts_with` is defined as "rules from another source".
Suggested fix: Add the FAQ↔vendor-deadline pair. Widen the README definition to cover internal inconsistencies.

### [low] L12. Smaller source items with no rule
Where: rules/sources/usg-funding-faq.txt:18 (opens 8:00 AM), :34 (invoice trouble: tell the Funding Director; silence beyond 3 business days, so future applications are denied), :63 (durable-good definition); guidelines l.92 (research supplies case by case), l.97 (FMS expenses need a past invoice or official estimate), l.103-104 (on/near campus preferred; off-campus travel conditions), l.144-147 (permanent funding ban)
Suggested fix: Add as `info` or `office_decides` rules where they drive a check or a fix. In particular, FAQ :34 gives a concrete fix for late invoices.

### [low] L13. ESR rule leaves out classroom events
Where: rules/funding.json:514-518
Problem: The source says "ESRs for on campus events". Classrooms are on campus, but `venue_classroom` is not a trigger, and `usg-uepa-event-id` (l.559-563) does include it.
Suggested fix: Add `venue_classroom` with a yellow "check whether an ESR exists for this booking", or note why it is left out.

### Tests (no separate severity)
`backend/tests/unit/test_rules_loader.py:91-97` pins only the two Trojan Event Services (TES) conflict pairs. Nothing pins the USG pairs (`usg-deadline-vendor`↔`usg-page-deadline-event-date`, `usg-deadline-travel`↔`usg-faq-deadline-new-vendors-travel`, the incomplete-application pair), the deadline anchors (`initial_payment_due_date` vs `event_date`), or the 6 and 8 offsets. Deleting one of those conflicts, or switching an anchor, keeps all 208 tests green. A table-driven test of (id, anchor, offset, unit, conflicts_with) for every USG deadline rule would close this.
