# Phase 3, iteration 3 — audit
Summary: 0 blockers, 1 high, 5 medium, 7 low.

Branch `phase-3/money-check` at 5b1f33f. All runs used `AI_MODE=recorded` with an empty `ANTHROPIC_API_KEY`.

Baseline:
- `cd backend && .venv/bin/python -m pytest`: 523 passed, 6 warnings (adversarial tests included).
- `backend/.venv/bin/python scripts/validate_rules.py`: OK (5 unverified rules, 15 dependent rules shown yellow).
- `scripts/run_eval.py budgets --json`: caught 30/30, wrong greens 0, fund matches or yellow 20/20, totals exact 20/20, draft allowed right 20/20.

I ran probes against `check_budget` and `document_from_reading` directly, using a scratch script outside the repo. I changed no repository file except this report.

## Rule check
Each rule's `source_text` was compared with `rules/sources/usg-funding-guidelines.txt` (lines 36-39, 78-81, 85-119, 123-141, 150-155), `usg-funding-page.txt:49` and `usg-funding-faq.txt:26,70`. `validate_rules.py` also confirms that every quote is in its snapshot.

| Rule id | Matches source? | Note |
|---|---|---|
| usg-food-cap | Yes | $35, per person, expected attendance, food lines (guidelines:115). Code sums only food lines whose category is sure (see the carried lows). |
| usg-hotel-cap | Yes | $400 per night, per room (guidelines:119). Code uses the unit price, with quantity = rooms x nights. |
| usg-venue-personnel-cap | Number yes, scope no | $4,000 matches guidelines:79. The source limits it to **on-campus** venue rentals and personnel, but the code sums venue, personnel and security lines whatever the venue (finding M1). Adding `security` is a fair reading of "personnel". |
| usg-over-4000-case-by-case | Yes | "over $4,000", strictly greater, on total expenses; office decides (guidelines:80). |
| usg-multi-day-case-by-case | Yes | Office decides (guidelines:81). |
| usg-yearly-cap | Yes | $8,000, per organisation, per year (guidelines:78). Code adds the amount received to this request. |
| usg-events-per-semester-cap | Yes (unverified) | 4 per semester (usg-funding-page FAQ). Unverified and always yellow, as PROJECT_CONTEXT requires. |
| usg-approved-vendor / usg-vendor-list | Yes | Quote matches guidelines. The rule is red, but it depends on the unverified list, so it is shown yellow (a recorded decision). |
| usg-quote-required, usg-cart-screenshot, usg-amazon-wishlist | Yes | Section 2 text matches. |
| usg-ineligible-* (19 rules) | Yes, with one note | Each `item_quote` matches a bullet at guidelines:124-141, and each trigger matches its bullet. `performer_fee` in vocabulary.json:66 adds "speakers' fees", which the bullet does not say (finding M3). |
| usg-ineligible-closed-on-campus-events | Yes | Applied only when the venue is on campus (money_check.py:525), as the source says. |
| usg-professional-free-open | Yes | "must be free and open to all students" (guidelines:93). |
| usg-pva-po-vendor | Yes | The categories in PRODUCTION_CATEGORIES match "production, staging, lighting, decoration (rentals only), venue, staffing, and security"; shown yellow. |
| usg-philanthropy-no-service-payments | Yes | Always yellow, "needs a human look". |
| usg-tshirts-licensed-vendor | Yes | Yellow: code cannot check it. |
| usg-food-justification, usg-food-health-permit-insurance, usg-hospitality-food-form, usg-esr-on-campus, usg-uepa-event-id, usg-hotel-price-comparison, usg-hotel-point-of-contact, usg-lodging-justification, usg-travel-statement-of-purpose, usg-traveler-information, usg-conference-logins | Yes | Each quote is in Section 2 or Section 5. Only the presence of traveller details is checked; none are stored. |
| usg-lodging-case-by-case | Yes | Office decides (guidelines:116). |
| usg-denial-other-university-funding | Yes | Yellow, as PROJECT_CONTEXT 7 says (guidelines:154). |
| usg-deadline-vendor, usg-deadline-travel, usg-page-deadline-*, usg-faq-deadline-new-vendors-travel, usg-faq-professional-travel-eight-weeks, usg-no-funding-breaks | Yes | Numbers 6, 9 and 8, and their anchors, match the snapshots. Conflicts are encoded and the stricter rule is applied. All dates come from the Phase 2 engine; none are computed in the money check. |

## Prompts and model output (AI reads, code checks)
- `quote_intake.INSTRUCTIONS` (quote_intake.py:28-57) tells the model to "never add up, multiply, convert or work out any amount" and to copy numbers as text. Code parses them (parse_cents:116), checks them against the text (197-201), and computes any missing amount (215). No prompt asks for a sum, date, cap comparison or verdict.
- `fund_reading.INSTRUCTIONS` (fund_reading.py:20-32) asks only for a fund label and a confidence. Code decides what is shown (money_check.py:344-372). A steered reading is now yellow.
- `application_draft.INSTRUCTIONS` (application_draft.py:26-38) forbids numbers. Code removes paragraphs that contain digits or number words not in the officer's text (83-91). The budget table, header and food figures are written by code (94-112).
- Every untrusted input goes in an `UntrustedDocument`. No outbound network code exists in backend/app or frontend/src (grep for httpx, requests, urllib, smtplib, webhook finds only `urldefrag`). `.env` is ignored by git, and no key is in the code.

## Earlier fixes, re-checked
- Iteration 1, H1 (security counted toward the $4,000): money_check.py:483 uses the rule's params. The test at test_money_check.py:241 would fail without `security` in the params. Confirmed.
- Iteration 1, H2 (rounded per-person figure in the fix): money_check.py:463 now says "more than $35.00". The test at test_money_check.py:250 checks this. Confirmed.
- Iteration 2, B1 and B2 (currency and "$.50"): quote_intake.py:60-67 and 125-126. The adversarial tests use real `document_from_reading`. Confirmed. The pattern is now too broad (L1).
- Iteration 2, H (back-dated `as_of`): api/money.py:209 drops `as_of`. The adversarial test monkeypatches `today_at_usc` and posts over HTTP. Confirmed.
- Iteration 2, mediums (unlinked document, hotel rooms x nights, off-campus venue, steered fund, number words): each has a code change and a test that exercises it. The off-campus fix leaves out `security` (M1).

## Findings

### [high] The page sends $0 received and 0 funded events by default, so the yearly cap passes green without the officer saying anything
Where: frontend/src/pages/MoneyCheck.tsx:140, :173 (and :183-190)
Problem: `useState({ received: "0", funded: "0" })` and `loadDemo` pre-fill both club fields with "0". The backend contract (schemas/money.py:93 and money_check.py:589-594) treats `None` as unknown: the yearly cap becomes a yellow "cannot compute" with a question. The page never sends `None` unless the officer clears the field. So a club that has already received $7,500, asking for $1,000 without touching the field, gets the green pass "With this request the club's USG total for the year is $1,000.00, within $8,000.00" under "Rules the application meets". No red appears, and the draft is allowed. The question "How many of the club's events has USG already funded this semester?" is also suppressed.
Why it matters: exit criterion 2 (no wrong green) and the trust rule "nothing unverified presented as certain". The yearly cap is a verified red rule, and here it passes on a value nobody entered.
Reproduce: open /money/check, add one $1,000 line, leave "USG money already received this year" at its pre-filled 0, then Check. Or POST /money/check with `club: {usg_received_this_year_cents: 0}`. The `usg-yearly-cap` finding is in `application_passed` as green.
Suggested fix: start both fields empty (`""`, which maps to `null`) in the initial state and in `loadDemo`, so the backend asks. Add a frontend or API-level regression test that a blank field sends `null` and yields the yellow `cannot_compute` finding.

### [medium] The "on-campus" venue and personnel cap is applied to off-campus lines, and security on an off-campus event is not flagged
Where: backend/app/services/money_check.py:483-498, :500-507
Problem: the source says "up to $4,000 of the total cost associated with **on-campus** venue rentals and personnel" (guidelines:79). `vp_entries` takes every venue_rental, personnel and security line whatever `event.venue` is. An off-campus event with a $4,500 venue_rental line gets a certain red on `usg-venue-personnel-cap` and the draft is blocked. That red is beyond the rule's scope; the line also gets the contradiction yellow. The contradiction check at :502 lists only `venue_rental` and `personnel`. A $1,500 `security` line on an off-campus event is green, counted toward the on-campus cap, and gets no finding.
Why it matters: the rule check requires "who it applies to" to match the source. A certain red based on contradictory facts should be yellow. The security gap repeats the iteration 1 H1 omission in the iteration 2 fix.
Reproduce: `check_budget` with `venue="venue_off_campus"` and one line `category="security", amount_cents=150000`: the line is green with no findings. With `category="venue_rental", amount_cents=450000`: the line has `usg-venue-personnel-cap` red plus yellow, and `draft_allowed` is False.
Suggested fix: use `vp_rule.params["categories"]` at :502. When the venue is off campus (or contradicts the category), make the cap finding yellow, "needs a human look", not red. Add tests for both cases.

### [medium] A document the model flagged as containing instructions still yields "sure" categories
Where: backend/app/services/quote_intake.py:223, :237-238; backend/app/api/money.py:78; money_check.py:669-670
Problem: when `contains_instructions` is true, the code only adds a note and a question. `category_sure` still follows the model's confidence, and `_suggested_lines` pre-fills it as sure. If the injection succeeds in skewing the reading (for example "Wine" read as `food` with high confidence, `contains_instructions: true`), the line is pre-filled as sure food, checked as food, and goes green. The fund reading now treats the same signal as "unsure" (money_check.py:350-351), so the two readers are inconsistent. This was iteration 1, L1, carried open. I raise it because exit criterion 7 is the only defence, and its test (test_money_check.py:180) uses a hand-typed honest `alcoholic_drinks` line, not a skewed reading.
Why it matters: "Text inside uploaded files is data". A document that has shown itself to be adversarial should not produce certain readings.
Reproduce: `document_from_reading` with one line `{"item":"Wine","category":"food","category_confidence":"high",...}` and `contains_instructions: True` gives `lines[0].category_sure == True`.
Suggested fix: when `reading.contains_instructions` is true, set `category_sure=False` on every line (and `vendor_sure=False`), so the officer must confirm each one. Add a test with a skewed reading.

### [medium] The vocabulary extends "Payments to talent or performers" to speakers' fees, which then become a certain red
Where: rules/vocabulary.json:66; quote_intake.py:47-48
Problem: the source bullet is "Payments to talent or performers" (guidelines:134). `performer_fee` is described as "(DJ, band, dancers, speakers' fees)". A guest speaker's fee at a Professional/Academic Fund workshop is therefore read with high confidence as `performer_fee` and shown as a certain red under `usg-ineligible-performers`. The guidelines do not say speakers are "talent".
Why it matters: the rule check requires the scope of a rule to match the source. A reading wider than the text should be yellow, "office decides" or "ask USG", not a certain red.
Suggested fix: drop "speakers' fees" from `performer_fee` and route speaker honoraria to `other` (yellow), or add a separate `speaker_fee` category with a yellow "ask USG" finding citing the same bullet.

### [medium] A certainly missed USG deadline still shows as yellow, with the headline "The office decides" (carried from iteration 1)
Where: backend/app/services/money_check.py:394-401 (dates from the Phase 2 engine)
Problem: for an event on 2026-12-02, checked as of 2026-11-15, `usg-deadline-vendor` and the others are `check_with_office`, `past_due: true`, with a yellow finding. The overall verdict is "The office decides", although the note says the deadline "has already passed". The draft is correctly blocked through `hard_blocks`, but the headline understates an automatic denial (guidelines:39).
Suggested fix: when `past_due` is certain, return a red finding citing the rule. Leave it to Phase 7 if the Phase 2 engine must not change.

### [medium] The test set still does not measure reading line items from uploads (carried from iteration 1)
Where: scripts/evaluators/budgets.py:30-38
Problem: the 30/30 result scores the case's typed `lines`. The quote reading feeds only the document cross-checks. No recording covers a PDF or image. Exit criterion 1 is met for the rule engine, not for "officer uploads quotes".
Suggested fix: add a variant of each case in which the lines come from `_suggested_lines(read_quote(...))`.

### [low] The foreign-currency pattern matches ordinary English and blanks every amount in the document
Where: backend/app/services/quote_intake.py:64
Problem: `\b(... pounds? ... won ... yen ... francs? ...)\b` matches "Pound cake", "10 pounds of brisket" and "We won the bid". The whole document is then marked not in dollars and every line amount is cleared. This is safe (yellow), but it often costs the officer the reading.
Suggested fix: require a currency word next to a number ("32 pounds sterling", "in euros") or the explicit phrases; keep the symbols and codes as they are.

### [low] Drafted paragraphs are not checked for claims of approval or eligibility
Where: backend/app/services/application_draft.py:35-37, :146
Problem: the prompt says not to claim approval or eligibility, but code only filters numbers. A paragraph saying "This event is fully eligible for USG funding" would be shown. The officer approves the draft, so the harm is limited.
Suggested fix: reject paragraphs that match `approved|eligible|guaranteed|meets all` and use the fallback instead, as is done for numbers.

### [low] An unsure travel or hotel line drops the travel deadline from the dates instead of showing it as "if this is travel"
Where: backend/app/services/money_check.py:431-433, :516-519
Problem: `categories` comes only from sure lines, so an unsure `lodging` line removes `usg-deadline-travel` from `dates`. The attachments get "If an unsure line is lodging…" (:571), but the deadline does not. Today this does not change blocking, because `usg-page-deadline-nine-weeks-payment` always applies.

### [low] `ClubMoney.first_registered` is accepted but never used
Where: backend/app/schemas/money.py:122; frontend/src/pages/MoneyCheck.tsx:190
Problem: dead field. The Startup fund's "first registered within the last two academic semesters" condition is not checked. Remove the field or use it.

### [low] Duplicated constants and a citation reused for unrelated uncertainties
Where: money_check.py:40 and :384 (the on-campus venue set repeated as a literal); api/money.py:93 repeats `_fund_name` (money_check.py:340); money_check.py:172 and :304 cite `usg-quote-required` for arithmetic mismatches and duplicate lines.
Problem: the duplicates can drift apart. The quote rule's text does not explain a "quantity x unit price differs" note.

### [low] AI audit rows from the money routes have no club
Where: backend/app/api/money.py:146, :169, :216, :240
Problem: `club_id=None` on rows that hold quote evidence and drafted text. Club-level access control is Phase 5, but these rows cannot be scoped to a club later.

### [low] Carried lows from iteration 1, still open
- money_check.py:439: unsure food lines are left out of food per person without a note.
- money_check.py:613-614: an unknown funded-events count gives a question but no yellow finding (masked on the page by the high finding above).
- money_check.py:468-469: "plan for at least N people" invites inflating expected attendance.
- MoneyCheck.tsx:486-488: a line whose vendor is not on the list keeps a green badge; the vendor note is collapsed.
- money_check.py:460: "about $0.33" is a floored figure labelled "about" (acceptable, noted for criterion 3).

## Exit criteria and tests
| # | Test that would fail if it broke | Note |
|---|---|---|
| 1 | test_money_check.py:60 (per case) and run_eval budgets | Typed lines only (M above). |
| 2 | test_money_check.py:60 and :141 | No test covers the page's default club values (H above). |
| 3 | test_money_check.py:74, :83, :250 | Exact; integer cents. |
| 4 | test_money_check.py:141 | Yes. |
| 5 | run_eval budgets (fund_ok) and test_money_check.py:188 | 10/20 matched, 10/20 yellow. |
| 6 | test_money_api.py:42, adversarial :77 | The server re-checks as of today. |
| 7 | test_money_check.py:180, test_money_reading.py:65 | Only an honest reading is tested (M above). |
| 8 | test_money_api.py:57; grep shows no outbound calls | Approval stores a SHA-256 only. |
