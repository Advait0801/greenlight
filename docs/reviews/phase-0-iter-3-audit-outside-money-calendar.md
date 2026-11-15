# Phase 0, iteration 3 — audit (c): outside money, academic calendar, USG deadline table
Summary: 0 blockers, 2 high, 8 medium, 8 low.

Scope: `rules/outside_money.json` (19 rules), `rules/calendar.json`, `rules/sources/usg-funding-deadlines.txt`, the rules that depend on the calendar, business days or academic weeks, and the research notes `docs/research/open_questions.md` and `docs/research/manual_snapshots/usg-funding-deadlines-26-27.csv`. Commit `9c3f500`.

Commands run: `python scripts/validate_rules.py` ran OK (read 254, unverified 5, "Every rule marked 'read' matches its snapshot text exactly"). `pytest` in `backend/`: 208 passed. SHA-256 of `raw/usc-academic-calendar.html`, `raw/student-handbook.pdf`, `raw/rso-accountability.html` and `raw/usg-funding-page.html` match the manifest. I extracted the 2026-27 calendar again from the raw HTML myself, and it matches `usc-academic-calendar.txt` word for word. The body of `usg-funding-deadlines.txt` is byte-identical to `docs/research/manual_snapshots/usg-funding-deadlines-26-27.csv`, and both hash to the manifest's `f2945352…`.

What I checked by hand:
- Every date and weekday in `calendar.json` against the snapshot and the raw HTML, with weekdays recomputed in Python. All match.
- Every row of the deadline table: weekdays, gaps, and week counts against the calendar.
- Every `source_text` in `outside_money.json` against the Handbook pages 88-92 and 77, the RSO Accountability page and the USG page, with the paragraphs around each one.

## Rule check

### outside_money.json

| Rule id | Matches source? | Note |
|---|---|---|
| sponsorship-in-kind | Yes | Handbook p.91 "RSO Co-Sponsorship" bullet, verbatim. Its conditions come through `condition_rules`. |
| sponsorship-cash-banned | Yes | Same bullet. Red is correct ("may not include monetary donations"). Code has no typed fact for "cash vs in kind" (see M5). |
| cosponsor-club-primary | Partly | All 4 quoted bullets are verbatim and the message is accurate. The same list has 2 more conditions it leaves out: the main contact must be present at all meetings, walkthroughs and on the day as primary producer, and the primary audience must be USC students and alumni. The list is introduced with "An RSO hosting an event with an outside organization", but the rule fires for any `co_hosts`, including another RSO (M2). |
| cohost-recognized-club | Partly | The text is verbatim, but the quoted passage is only the section's opening sentence. It does not state the allowance or "all co-hosts must be named". The second claim comes from `cosponsors-named-in-uepa` through `condition_rules` (M4). |
| cohost-unrecognized-banned | Yes | Verbatim, red, "strictly prohibited". Supported further by Handbook item 13 (p.77). |
| no-business-vendors | Text yes; fix no | The text is verbatim. The `fix_template` offers a way round the source's first sentence (M1). |
| donations-through-university | Partly | The text is verbatim, but `source_section` is wrong: it should be "Responsibilities of RSOs, item 14" (L1). The message's "only" and "gift account through University Advancement" are not in `source_text`. The gift-account sentence is under "Event Tickets/Payment for Services" (M4). |
| own-tax-exempt-banned | Yes | Verbatim. Same wrong `source_section` (L1). The fix "Do not file with the IRS" is stricter than the source, which allows filing with prior approval (L1). It has no triggers and nothing references it (L2). |
| fundraising-allowed | Yes, with a gap | Verbatim. The source makes fundraising subject to Campus Activities approval, which is discretionary. The rule shows it as "allowed / info" (M3). Its lead-time rules exist and match their sources. |
| no-individual-benefit | Yes | Verbatim, red. |
| ticket-sales-cover-costs | Yes, with a gap | Verbatim. "if approved" plus "Ticket sales as a fundraising activity may not be approved for every event" is discretionary (M3). The USG ineligibility comes from `usg-ineligible-ticketed-events` through `see_also_rules`. |
| raffle-purchase-banned | Yes | Verbatim, red. A free drawing fires the same trigger, `prize_drawing`, so the violation needs a typed fact (M5). |
| free-drawing-wording | Text yes; kind no | The text is verbatim, but every item is a "must" or "is required", and it is encoded as `kind: allowed`, `severity: info`. It is never listed as an obligation, and the message leaves out items (H2). |
| silent-auction-advancement | Yes | Verbatim. It leaves out the bid-sheet wording and "keep a record of what gifts were donated and the source" (L4). |
| sponsorship-activation-banned | Yes | Verbatim. "Only USG and GSG may" in the message comes from the next sentences, which are not in `source_text` (M4). |
| brand-ambassadors-banned | Yes | Verbatim (Appendix IX, p.126). The only trigger is `sponsorship`, but the source is an advertising rule for every event (L3). |
| dues-voluntary | Yes | Verbatim (RSO Accountability, updated 2025-09-19, which matches the manifest). It has no triggers and nothing references it (L2). |
| dues-required-banned | Yes | Verbatim. Used by 4 recognition rules. |
| other-usc-funds-ask-usg | Yes | Verbatim (USG page FAQ). The yellow and the "ask USG" advice rest on `usg-denial-other-university-funding`, which says the same thing with the same trigger (L2). PROJECT_CONTEXT's examples (facilities cost waiver, GSG) are not named, which is fine. |

PROJECT_CONTEXT "Money from outside" table, row by row:
- Every "Allowed" and "Not allowed" row is covered.
- Co-host naming is covered by `cosponsors-named-in-uepa` in events.json.
- Bookstore approval is covered by `item-sales-bookstore`, cash approval by `cash-collection-approval`, and the 2-week meeting by `fundraising-meeting`.
- Nothing in the table is misstated. The gaps are in what the rules do with it (H2, M1-M5).

### calendar.json and rules that depend on it

| Rule / entry | Matches source? | Note |
|---|---|---|
| calendar `fall-2026` | Yes | Every date and weekday matches the snapshot and the raw HTML. Classes Aug 24 to Dec 4; Labor Day Sep 7; Fall Recess Oct 8-9; Veterans Day Wed Nov 11; Thanksgiving Wed-Sun Nov 25-29; study days Sat-Tue Dec 5-8; exams Wed-Wed Dec 9-16. |
| calendar `spring-2027` | Yes | Classes Jan 11 to Apr 30; MLK Jan 18; President's Day Feb 15; Spring Recess Sun-Sun Mar 14-21; study days Sat-Tue May 1-4; exams Wed-Wed May 5-12; commencement Wed-Sat May 12-15. All weekdays are correct. |
| calendar `summer-2027` | Yes | Classes Wed May 19 to Tue Aug 10; Memorial Day May 31; Juneteenth Fri Jun 18 (the observed date); Independence Day "Mon July 4-5" is encoded 07-04 to 07-05 as the source states, although Jul 4, 2027 is a Sunday. Harmless. |
| calendar `recesses` Winter | Yes | Thu Dec 17, 2026 to Sun Jan 10, 2027. The "*Winter Holiday for Graduate Student Workers: 12/25/26-01/01/27" line is not encoded. That is fine for student dates, but it matters for business days (M7). |
| calendar `business_days` | Unverified (correct) | The note says recess days count as business days "because offices stay open". No snapshot supports that, and the page itself says staff holidays are in a different policy (M7). |
| calendar `academic_weeks` | Unverified (correct) | `definition: null`. Correct. |
| usc-academic-calendar-2026-27 (events.json) | Yes | Spring text verbatim; `read` agrees with the calendar (validator checks this). |
| usc-business-days-definition (events.json:25) | Yes, unverified | Verbatim. The text itself says the holidays are student holidays. |
| usg-academic-week-definition (funding.json:6) | Yes, unverified | Verbatim. Points to the table. |
| usg-deadline-vendor / usg-page-deadline-event-date / usg-deadline-travel / usg-faq-deadline-new-vendors-travel | Yes | Each depends on `usg-academic-week-definition`, so each is shown yellow. Conflicts are listed both ways. |
| usg-no-funding-breaks | Yes | Depends on the calendar. Holidays, breaks, study days and finals are blocked day by day. |
| usg-post-event-evaluation, usg-final-invoices, usg-incomplete-two-business-days, recognition-appeal | Yes | Each depends on `usc-business-days-definition`, so each is shown yellow. |
| usg-incomplete-48-hours | Yes | 48 hours, no calendar needed. |
| social-events-not-study-days-finals | Yes | Depends on the calendar. |
| classroom-requests-week-4 | Yes | "Week 4" is a semester-week count that no source defines. It is shown red and certain (L7). |
| tes-rso-deposits | Yes | "5 business days" is in params without `depends_on: usc-business-days-definition` (L7). |
| `usg-funding-deadlines.txt` (manual) | Mostly consistent | Every deadline is a Wednesday. Every event row runs Monday to Friday, and the rows are consecutive. The blank rows are exactly the study-days, finals and winter-recess span (Dec 7 to Jan 10) and the spring-recess week. The 6-week column counts exactly 6 academic weeks, with breaks skipped, everywhere except the early-spring cut-offs. The 9-week column does not: after spring recess it is 8 academic weeks (H1). |

## Findings

### [high] The 9-week travel column of the transcribed USG deadline table is one week short after spring recess, and some early-spring rows are shorter than the guidelines' count
Where: rules/sources/usg-funding-deadlines.txt:39-44 (rows 2027-03-22 to 2027-04-26, column `deadline_9_week`); also :29-33; docs/research/open_questions.md:56
Problem: I numbered the academic weeks: fall weeks 1-15 run from Aug 24 to Dec 4. Winter (Dec 7 to Jan 10) and spring recess (Mar 15-19) are skipped. On that count:
- The 6-week column gives exactly 6 academic weeks for every row from Oct 5 to Apr 30 except Jan 11 (4) and Jan 18 (5).
- The 9-week column gives exactly 9 for every fall row and for Feb 15 and Feb 22, the rows that cross winter.
- For all six rows after spring recess, the 9-week column gives **8 academic weeks** (9 calendar weeks). Example: event week Mar 22 has a 6-week deadline of Feb 3 and a 9-week deadline of Jan 20. That is only 2 weeks apart; every other row is 3 weeks apart (for example Oct 26: Sep 16 and Aug 26).

So the 9-week column counts the recess week, while the 6-week column, and the 9-week column across winter, skip breaks. Either the transcription is off by one row in that block, or USG's sheet is inconsistent. Code cannot tell which. Separately, the 9-week deadlines for Jan 11 to Feb 8 (Nov 11) give 4 to 8 academic weeks, and the 6-week deadlines for Jan 11 and Jan 18 give 4 and 5. These appear to be USG's own end-of-fall cut-offs, but they are later than the guidelines' "at least 6/9 academic weeks". The research note says the table is "consistent with the rest of the column" and does not notice either point.
Why it matters: For a travel event after spring recess, the table gives a deadline one week later than the guidelines' rule. A missed USG deadline is automatic denial. The dates are yellow today, but a yellow date is still the date the officer acts on. PROJECT_CONTEXT says sources that disagree must apply the stricter rule and show both.
Suggested fix:
- Have a person compare rows 2027-03-22 to 2027-04-26 (9-week column) with the sheet, and note the result in the manifest entry.
- Until then, wherever a computed academic-week count gives an earlier date than the table (for example Jan 13 rather than Jan 20 for Mar 22), show the earlier one and cite both. Do this for the early-spring rows as well.
- Record these rows in `usg-academic-week-definition.notes` as a known disagreement.

### [high] Free-drawing requirements are encoded as an optional "allowed / info" rule, so they never reach the officer as obligations
Where: rules/outside_money.json:288-307 (`free-drawing-wording`: `kind: "allowed"`, `severity: "info"`, message at :300); data/eval/README.md ("Listed: rules … of kind deadline, requirement, cap, banned or blocked_period")
Problem: The source says free drawings are legal only "when rules conforming to the California State Law are followed exactly". Each item is a "must" or "is required":
- in connection with an event or RSO;
- the ticket shows date, time and place, sponsors **and beneficiary**, "not required to be eligible", and "winner need not be present";
- at least one free ticket per person;
- every solicitor knows how to get free tickets;
- the word "drawing" or "free drawing" is required.

`kind: allowed` and `severity: info` turn these into a note. By the eval set's own definition, "allowed" rules are never listed as obligations. A planned drawing therefore gets only `raffle-purchase-banned` as a "condition", and nothing tells the officer what must be printed on the ticket. The message also leaves out the beneficiary, the one-per-person minimum, the solicitor rule and the required word "drawing". `silent-auction-advancement` correctly uses `kind: requirement`, `severity: red` for the same kind of rule.
Why it matters: If the drawing breaks these conditions it is an illegal raffle under the source. The rule changes a legal requirement into an optional note. That is a trust problem in a rule marked `read`.
Suggested fix: Make it `kind: "requirement"` with `severity: "red"` and a fix template that lists every item. Name all six conditions in the message. Add `free-drawing-wording` to the events eval case for a drawing, and add a free-drawing case. The existing raffle case is a paid raffle.

### [medium] `no-business-vendors` fix suggests a way round the rule it cites
Where: rules/outside_money.json:137
Problem: The fix is "Remove the vendor sales, **or** make the business a small part of a real club event." The quoted source begins "RSOs may not bring a business to campus as a vendor", which is absolute. The next sentence only allows a business on campus during a pre-existing event. The Handbook's "Vendors" paragraph (p.92, not encoded) adds that only the Bookstores, Hospitality and Athletics may bring outside vendors, and that vendors need their prior permission. The "or" reads as if vendor sales are fine once the business is a small part of the event.
Why it matters: The officer is told an action the source does not allow.
Suggested fix: Change it to "Remove the vendor sales. A business may attend only an event that exists for its own purpose, and may not sell without approval from the USC Bookstores, Hospitality, Athletics or Trojan Event Services." Encode the "Vendors" paragraph as a `banned` rule for `outside_vendors`.

### [medium] `cosponsor-club-primary` leaves out two conditions from its own list and applies to club-to-club co-hosting without saying so
Where: rules/outside_money.json:53-74
Problem: The Handbook list (p.91) is introduced with "An RSO hosting an event with an outside organization must be aware that:". The rule quotes 4 of its bullets. It leaves out two more conditions in the same list:
- "The main contact from the RSO must be present at all meetings, walkthroughs, and day-of event as the primary producer of the event."
- "The primary target audience for the event must be USC students and alumni."

No other rule encodes either; I searched `rules/*.json`. The rule's triggers include `co_hosts`, which covers co-hosting with another RSO. There, "the money must be paid by the RSO and not the outside agency" is ambiguous: one co-host must pay, and the message says "the club pays all university fees".
Why it matters: An officer gets an incomplete checklist for a sponsored event. For two clubs co-hosting, the rule states a payer requirement the source does not clearly impose.
Suggested fix: Extend `source_text` to cover the two missing bullets, and add them to the message. Either restrict the rule to sponsors and non-RSO co-hosts (add a typed `co_host_is_rso` fact), or word the message as "one host club must be the primary contact and payer".

### [medium] Discretionary approvals are shown as "allowed" rather than "office decides"
Where: rules/outside_money.json:184-215 (`fundraising-allowed`), :240-265 (`ticket-sales-cover-costs`)
Problem: The Handbook says "RSOs will need approval from Campus Activities before conducting any fundraising efforts". Under "Other types", Campus Activities, Trojan Event Services and campus partners "may approve" based on the event details. Ticket sales are "permissible **if approved**", and "Ticket sales as a fundraising activity may not be approved for every event." The approval itself is the office's judgment. Both rules are `kind: allowed`, `severity: info`, with messages such as "Tickets may be sold only to cover that event's own costs." None of the outside_money rules carries `office_decides`.
Why it matters: CLAUDE.md requires "Rules where an office uses judgment are shown as 'the office decides', never as a pass." An "allowed" note next to a planned fundraiser reads as a pass.
Suggested fix: Add an `office_decides` rule for the fundraising and ticket-sale approval, quoting "Ticket sales as a fundraising activity may not be approved for every event." and the "Other types" sentence. Trigger it on `fundraising`, `ticket_sales`, `item_sales` and `cash_collection`. Alternatively, change these two rules to `severity: office_decides`.

### [medium] Messages state facts that are not in the cited `source_text` or in any referenced rule
Where: rules/outside_money.json:157 (`donations-through-university`), :342 (`sponsorship-activation-banned`), :87 (`cohost-recognized-club`)
Problem: The finding shows `source_text` as its citation, but these messages claim more than it says.
- Donations: "only through the university (a gift account through University Advancement)". Item 14 says RSOs "may solicit and receive tax-deductible contributions through the university". The gift-account sentence is on p.89, under "Event Tickets/Payment for Services". The Handbook also lists "Donation collection for a recognized organization" as an approved fundraising type, so "only" is stricter than the source says.
- Activations: "Only USG and GSG may, through Campus Activities." That sentence is in the snapshot but outside the quoted text.
- Co-host: "Co-hosting … is allowed. All co-hosts must be named in the permit application." The quote is only the section's opening sentence. The naming claim comes from a different rule.
Why it matters: "Every finding carries the rule text" means the text shown has to support what the officer reads.
Suggested fix: Extend each `source_text` to the sentences the message uses, or add a second rule, so each claim is quoted. For donations, either quote the gift-account sentence and drop "only", or say "tax-deductible donations only through the university".

### [medium] No typed fact lets code decide several "banned" verdicts
Where: rules/vocabulary.json (event_attributes); rules/outside_money.json rules `sponsorship-cash-banned` (:32), `raffle-purchase-banned` (:267), `cohost-unrecognized-banned` (:103), `brand-ambassadors-banned` (:352), `sponsorship-activation-banned` (:330), `dues-required-banned` (:391), `own-tax-exempt-banned` (:166); data/eval/events/cases.json ev-25 (`sponsorship-cash-banned` "violated": true) and ev-26
Problem: The only attributes are `sponsorship`, `prize_drawing` and `co_hosts`. There is nothing like `sponsor_gives_money`, `drawing_requires_purchase`, `co_host_recognized`, `uses_brand_ambassador`, `is_activation`, `dues_required` or `filing_tax_exempt`. Yet the eval answer key expects `blocked` / `violated: true` for the cash sponsor and the paid raffle. As the table stands, a later engine can reach that verdict in only two ways. It can take it from the model's reading of the sentence, which would be a model-produced verdict. Or it can fire red on every sponsorship and every drawing.
Why it matters: "AI reads, code checks": the model should extract a typed, confidence-scored fact, and code should apply the rule. Fixing this later means changing the vocabulary, the eval schema and the answer keys together.
Suggested fix: Add these facts to `vocabulary.json`, using `trigger_mode: "all"` (for example `sponsorship` + `sponsor_gives_money`) or a `check` naming the fact. Put the facts in the eval cases' `attributes`, so the answer key shows which fact produces each verdict. A low-confidence fact must lead to yellow.

### [medium] The deadline table has Monday-to-Friday rows only, so weekend events and payment dates have no row
Where: rules/sources/usg-funding-deadlines.txt:13-44; rules/funding.json `usg-deadline-vendor` (`anchor: initial_payment_due_date`)
Problem: Every row except winter runs Monday to Friday. A Saturday or Sunday event falls between rows: the hackathon in ev-25 is Saturday Apr 10, 2027; the yp-01 retreat is Feb 26-28; spring study days start Saturday May 1. The table is keyed by event week, but the guidelines' rule counts back from the initial payment due date. Nothing records how a payment date or a weekend date is mapped to a row. The research note's "use the earlier of payment date and event date" is a reasonable reading, but it is not written in any rule.
Why it matters: When a calculator later looks dates up "by event week", it will either find no row, which could wrongly be read as "no USG funding that week", or it will choose a row by an unstated convention.
Suggested fix: State the lookup rule in `usg-academic-week-definition.params` and its notes. The stricter choice is the Monday-to-Sunday week containing the date. Say the payment-due date is looked up in the same way, and that the earlier of the two applies. Add a test with a Saturday event.

### [medium] The business-day assumption gives the lenient date and rests on an unsupported claim
Where: rules/calendar.json:126-130; rules/events.json:25-61 (`usc-business-days-definition`)
Problem: The calendar's note says recess days count as business days "because offices stay open". No snapshot says that. The quoted Registrar sentence says its holidays are "for students, graduate students and graduate student workers", and that staff holidays are in "Calendars and Holidays / Paid University Holidays" policies, which are not snapshotted. The snapshot also lists a graduate-worker winter holiday, 12/25/26 to 01/01/27, that is not encoded.

Skipping student holidays, such as Veterans Day or the Wednesday of Thanksgiving, pushes deadlines that count forward later. For example, an event ending Mon Nov 23, 2026 gives a 3-business-day evaluation deadline of Mon Nov 30. Counting Wed Nov 25 gives Fri Nov 27 (or Thu Nov 26). Counting winter-closure days as open does the opposite. The direction of the error is not chosen deliberately.
Why it matters: The date is yellow, but it is still the date the officer is told. PROJECT_CONTEXT asks for the stricter reading where the rule is unclear.
Suggested fix: Remove "because offices stay open" from the note, or snapshot USC's paid-holiday policy. Until someone confirms the rule, compute business days in the stricter direction. For deadlines that count forward, skip only weekends and show "may be later if the office is closed". Say this in both `calendar.json` and the rule.

### [medium] No test checks the manual deadline table: its hash, Wednesdays, consecutive rows or week counts
Where: backend/tests/unit/test_rules_loader.py:118-129 and :306-323 (raw re-derivation only covers committed raw files); rules/sources/manifest.json `usg-funding-deadlines` entry (`sha256`, `manual: true`)
Problem: The manifest records a SHA-256 for the transcription, but no code checks it. The raw-file test skips manual sources. Nothing asserts that each deadline is a Wednesday, that each row starts on Monday, that rows are consecutive, that blank rows fall only in breaks, study days or finals in `calendar.json`, or that the two columns are consistent. All of these hold today except H1, but a silent edit to a cell would pass every check.
Why it matters: This is the file the deadline calculator is meant to treat as the source of truth (PROJECT_CONTEXT section 7). Exit criteria and CLAUDE.md expect every rule fact to have a test that fails when it breaks.
Suggested fix: Add a unit test that hashes the snapshot body against the manifest and checks the structure listed above against `calendar.json`. Add an xfail or an explicit allow-list for the H1 rows until a person confirms them.

### [low] Wrong `source_section`, and a fix stricter than its source, on the item-14 rules
Where: rules/outside_money.json:151, :172, :179
Problem: Item 14 is under "Responsibilities of RSOs" (Handbook p.77, snapshot line 3397). It is not under "RSO Recognition Requirements", which starts on p.82 (line 3606). The `own-tax-exempt-banned` fix says "Do not file with the IRS", but the source bans filing "without the prior approval of Campus Activities".
Why it matters: A citation that points to the wrong section is harder for a person to check.
Suggested fix: Set `source_section` to "Responsibilities of RSOs, item 14". Change the fix to "Do not file without Campus Activities' prior approval; ask them about a university gift account."

### [low] Unused and duplicate rules
Where: rules/outside_money.json:166 (`own-tax-exempt-banned`), :373 (`dues-voluntary`), :409 (`other-usc-funds-ask-usg`); rules/funding.json:1706 (`usg-denial-other-university-funding`)
Problem: `own-tax-exempt-banned` and `dues-voluntary` have no triggers, and no other rule, eval case or code references them, so nothing can ever show them. `other-usc-funds-ask-usg` and `usg-denial-other-university-funding` both fire yellow on every `usg_funding` event with the same advice. Every USG application gets two identical "ask USG" notes, including those that use no other USC money. Also, `sponsorship-in-kind` and `sponsorship-cash-banned` quote the same sentence, and so do `dues-voluntary` and `dues-required-banned`. That is acceptable, but worth noting.
Suggested fix: Give the two orphan rules a trigger (for example a `nonprofit_filing` fact) or a referencing rule, or remove them. Trigger the other-USC-funds rule on a fact such as `other_usc_funding` rather than on `usg_funding`, and merge the two rules' messages.

### [low] `brand-ambassadors-banned` fires only on sponsorship
Where: rules/outside_money.json:367-369
Problem: The source sentence is in Appendix IX (advertising) and covers all third-party promoters, whether or not anyone sponsors the event.
Suggested fix: Trigger on an advertising or promoter fact, or on `any_event` as a condition.

### [low] Money-related Handbook passages not encoded
Where: rules/sources/student-handbook.txt:3914-3925 (no for-profit or commercial activity, no acting as a front for a business), :4031-4043 (silent-auction bid-sheet wording and record of donated gifts), :4085-4100 ("Vendors", "USC Emblem Products": merchandise for fundraisers must come from a USC-licensed vendor)
Problem: These are not in PROJECT_CONTEXT's table but sit in the same sections. The emblem-products rule matters for the bake-sale and merch-sale cases. Only USG's T-shirt licence rule is encoded (`usg-tshirts-licensed-vendor`), and it does not cover a sale that USG does not fund.
Suggested fix: Add them as requirements, or record them as out of scope in `rules/README.md`.

### [low] Stale statements about the calendar's verification
Where: backend/app/rules/calendar.py:3-4 ("marked unverified until a human confirms it … Anything computed from it must therefore be shown with that caveat"); docs/PROGRESS.md:83 ("still unverified until a person confirms")
Problem: The calendar is now `read` (calendar.json:7, PROGRESS.md:108). The docstring and the table row say the opposite.
Suggested fix: Update both lines.

### [low] Research note claims that the snapshots do not support
Where: docs/research/open_questions.md:7, :56, :65, :67, :69-70
Problem:
- Q1 is marked "**Answered**", but the table is an unconfirmed hand transcription (the manifest note says so).
- :56 calls the 6-week column consistent and does not notice H1.
- :65 says "Events outside Oct 5, 2026 – Apr 30, 2027 are not in the table at all". In fact, Aug 24 to Oct 2 are in the table as N/A rows, and only May onward is absent.
- :67 says to show Nov 11 "as is", but the guidelines say USG "does not process applications … during University holidays", so a deadline on Veterans Day conflicts with the guidelines.
- :69-70 state "have already missed" as fact, though it rests on the unverified table.

The remaining claims check out: every deadline is a Wednesday; the 40-day gaps; Feb 22 → Nov 18 skipping winter; Jan 11 to Feb 19 not matching a simple count; the 48-hour definition is in the guidelines; the FAQ's 8 weeks; the TES "after January 26" text. The SB 145-05 claim cites a Daily Trojan link in `student_org_pain_points.md`, not a snapshot.
Suggested fix: Mark Q1 "transcribed, awaiting human check". Correct :65. Record the Nov 11 conflict as "sources disagree". Phrase :69-70 as "per the unconfirmed table".

### [low] Calendar-dependent rules with week or business-day counts outside the dependency mechanism
Where: rules/events.json:504 (`classroom-requests-week-4`), :293 (`tes-rso-deposits`)
Problem: "Week 4" is a semester-week count that no source defines (the calendar's `academic_weeks.definition` is null). The rule is red and certain, and its params have no date. `tes-rso-deposits` has `due_business_days_after_processing: 5` but no `depends_on: usc-business-days-definition`, so if a date is ever computed from it, it will look certain.
Suggested fix: State the week-4 date for each term in params (Sep 14, 2026; Feb 1, 2027), or depend on a week-count definition. Add the business-day dependency to `tes-rso-deposits`.

### [low] The deadline table's version date is assumed
Where: rules/sources/manifest.json, entry `usg-funding-deadlines` (`version_date: 2026-10-21`, basis "dated as the guidelines that link to it")
Problem: The sheet is titled "EDITED 26-27 Funding Application Deadlines", so it has been edited at some point. Its real version date is unknown, and the rule-change alert has nothing to compare against.
Suggested fix: When a person compares the transcription with the sheet, record the sheet's "last edit" time, or note it as unknown in `version_date_basis`. Do not reuse the guidelines' date.
