# Phase 5, iteration 3 — audit
Summary: 0 blockers, 1 high, 4 medium, 7 low.

What I ran: `pytest -q` (799 passed), `pytest tests/adversarial -q` (197 passed), `python scripts/validate_rules.py` (OK), `python scripts/run_eval.py` (no misses or false flags), `npm run build` (OK). I also ran a server on port 8035 with `AI_MODE=recorded`, the passcode `audit-passcode-123` and `/tmp/gl-audit-p5.db`, probed it, then stopped it. I never called the live API.

## Rule check

The table covers every rule the gap helper offers, cites as a condition, lists as not allowed, or brings in as a step. Each `source_text` is checked word for word against its snapshot in `rules/sources/`, ignoring whitespace and hyphen line breaks.

| Rule id | Matches source? | Note |
|---|---|---|
| sponsorship-in-kind | Yes (student-handbook.txt) | "can only be in-kind donations … may not include monetary donations" matches section 7. |
| sponsorship-cash-banned | Yes (student-handbook.txt) | Same quote as above. |
| cosponsor-club-primary | Yes (student-handbook.txt) | Primary contact, payer and first name on advertising match section 7. |
| cosponsor-primary-audience | Yes (student-handbook.txt) | |
| cohost-recognized-club | Yes (student-handbook.txt) | The quote is general. The ban on unrecognized groups is carried by the condition rule below. |
| cohost-unrecognized-banned | Yes (student-handbook.txt) | |
| cosponsors-named-in-uepa | Yes (student-handbook.txt; a hyphen line break in the snapshot) | Source scope is "events in any campus space". The gap helper cites it whatever the venue (low L6). |
| fundraising-allowed | Yes (student-handbook.txt) | |
| fundraising-meeting | Yes (student-handbook.txt) | "at least two weeks prior", anchor event_date, offset 2 weeks, before. Matches. |
| fundraising-form-tes | Yes (tes-terms.txt) | |
| fundraising-approval-discretionary | Yes (student-handbook.txt) | Severity office_decides. Correct, but see medium M1 for how it is shown. |
| no-individual-benefit | Yes (student-handbook.txt) | |
| item-sales-bookstore | Yes (student-handbook.txt) | Bookstore approval, as in section 7. |
| cash-collection-approval | Yes (tes-terms.txt) | Trojan Event Services (TES) and the Department of Public Safety (DPS), as in section 7. |
| donations-through-university | Yes (student-handbook.txt) | Through the university, with Campus Activities first. Matches. |
| own-tax-exempt-banned | Yes (student-handbook.txt) | "without the prior approval of Campus Activities" is kept in the message. |
| ticket-sales-cover-costs | Yes (student-handbook.txt) | "for that specific event". Matches. |
| usg-ineligible-ticketed-events | Yes (usg-funding-guidelines.txt) | "Events that include ticket sales". Matches. |
| free-drawing-wording | Yes (student-handbook.txt) | |
| raffle-purchase-banned | Yes (student-handbook.txt) | "purchase a ticket or make a donation". Matches. |
| brand-ambassadors-banned | Yes (student-handbook.txt) | |
| sponsorship-activation-banned | Yes (student-handbook.txt) | "USG & GSG" only. Matches. |
| dues-voluntary | Yes (rso-accountability.txt) | |
| dues-required-banned | Yes (rso-accountability.txt) | |
| other-usc-funds-ask-usg | Yes (usg-funding-page.txt) | Severity yellow. The option is shown as "check first" with a yellow badge. |
| usg-denial-other-university-funding | Yes (usg-funding-guidelines.txt) | |

No rule differs from its source.

## Findings

### [high] Officer-typed asks that have a company pay the club's bills still go word for word into the outreach email, and the note scan does not flag them
Where: backend/app/services/gap_email.py:108-115 and 144-145; backend/app/services/gap_helper.py:63-98 (`_IDEA_PATTERNS`, `_EMAIL_BANNED`); backend/app/services/gap_helper.py:290-297 (`_NAME_BANNED`)

Expected: The "what we would like" line, the event name and the recipient are written into the email word for word. None of them should ask a company for money. The handbook's co-sponsorship rule (`cosponsor-club-primary`) says "The money must be paid by the RSO and not the outside agency for any fees owed to the university", and `sponsorship-in-kind` says sponsorship "may not include monetary donations". A company paying the club's bills is cash sponsorship in another form. Exit criterion 1, and the iteration 2 highs on this same filter.

What happened: The filter is a word list. Plain phrasings with no money word get through. With the server running (`POST /gap/email`, kind `in_kind_sponsor`), each of these asks appeared word for word in the email under "What we would like: …":
- "your company to cover our venue fee"
- "to pick up the catering bill"
- "to reimburse our food costs"
- "to cover the cost of the DJ"
- "covering the room rental invoice"

The event names "Night Chipotle covers the bill" and "Free Pizza Night paid for by Dominos" also went into the subject and body. The email then states, in code's own words, that the club "will stay … the payer", which contradicts the line above it.

In `POST /gap/options`, the notes "Could Chipotle cover our venue fee?", "Maybe a company can pay the caterer directly" and "ask Red Bull to reimburse us" flag nothing as "in your note".

Why it matters: The email Greenlight drafts would ask a corporate sponsor to pay the club's costs, which USC forbids. The iteration 2 fix extended the word list, but a word list cannot cover every synonym. Every new phrasing reopens the same high.

Reproduce: Post this to `/gap/email`: `{"kind":"in_kind_sponsor","club_name":"Chess Club","recipient":"Cafe","event_name":"Tournament","ask":"your company to cover our venue fee"}`. The ask appears in `text`.

Suggested fix: Stop copying free text into the ask line. Have the officer pick from a fixed list of in-kind kinds written by code (food, drinks, products, a venue, printing) plus an item name of at most a few words. Or add the ask only when it matches an allowlist of goods and services, not when it escapes a denylist. At least add cover, reimburse, bill, invoice, fee(s), pay for, paid for and pick up the (tab|bill|cost) to the note scan and to the ask and name filters. Add a regression test with the phrasings above.

### [medium] The fundraiser and ticket-sales options are labelled "Allowed" although an office decides whether to approve them
Where: backend/app/services/gap_helper.py:45-50 and 224-247; frontend/src/pages/GapHelper.tsx:134 and 145-148

Expected: Trust rule (CLAUDE.md; PROJECT_CONTEXT section 9): "Rules where an office uses judgment are shown as 'the office decides', never as a pass." The `fundraising-approval-discretionary` rule (severity `office_decides`) says Campus Activities and TES "may approve the fundraising request based on the event details". It also says ticket sales "may not be approved for every event".

What happened: The "A fundraiser or sales" option, and "Ticket sales" when the event does not ask USG, have `status: "allowed"` and the label "Allowed, with the conditions below". The page shows them with a neutral badge. The discretionary rule appears only as a citation inside the collapsed "Rule text, conditions and sources" panel. Nothing on the card says the office decides.

Reproduce: Post `{"event_date":"2027-04-09"}` to `/gap/options`. The `fundraiser` option has `status: "allowed"` and `finding: null`.

Suggested fix: Add a third status, "office_decides", with the label "Allowed only if Campus Activities and Trojan Event Services approve: the office decides". Give it a finding from `fundraising-approval-discretionary` with `Verdict.OFFICE_DECIDES` for any option whose condition rules include an office_decides rule, and show it with the office-decides badge. Add a test that no option whose conditions include an office_decides rule has `status == "allowed"`.

### [medium] Cross-origin calls can never reach the USG screen: CORS does not allow the X-Reviewer-Key header
Where: backend/app/main.py:57-62 (`allow_headers=["Content-Type"]`); frontend/src/api/usg.ts:78

Expected: CLAUDE.md, "Ports and addresses", describes setting `VITE_API_BASE_URL` to the backend's own address so the browser calls it directly, and `FRONTEND_ORIGIN` for a deployed frontend. The reviewer routes are called with the header `X-Reviewer-Key`.

What happened: A preflight with `Origin: http://localhost:5173` and `Access-Control-Request-Headers: x-reviewer-key` gets `400 Disallowed CORS headers`. In direct mode, or with a separately hosted frontend, the reviewer can never open the queue. The page shows only "Could not reach the Greenlight server." Nothing leaks; the screen just fails closed. It matters for Phase 6, where the app is deployed.

Reproduce: `curl -i -X OPTIONS localhost:8035/usg/queue -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: x-reviewer-key"`

Suggested fix: Add `"X-Reviewer-Key"` to `allow_headers`. Add a test that the preflight succeeds for the allowed origin and still fails for any other origin.

### [medium] Anyone can send an application in any club's name and shape the failure chart
Where: backend/app/api/usg.py:60-99 (`SendRequest.club_name` is free text; no rate limit); backend/app/services/usg_screen.py:138-155

Expected: PROJECT_CONTEXT section 9 says "A club's data is private to the club. The USG screen shows only applications a club chose to send." Exit criterion 2 says a club's data is not visible unless the club sent it.

What happened: `/usg/send` needs no identity. `club_name` is whatever the caller types. A third party can put an application in the queue as "Filipino American Student Association" with made-up lines. A reviewer would then draft, and possibly approve, a denial addressed to that club. The same anonymous route can also be called in bulk, filling the queue and steering the "Why applications fail" chart, since every sent application is counted. The club's real data is not exposed, but what the reviewer sees under a club's name is not necessarily what the club sent. PROGRESS.md records that there are no accounts by design.

Reproduce: `POST /usg/send` with `{"club_name":"<any real club>","consent":true,"check":{…}}` returns 200 and the item appears in `/usg/queue` under that name.

Suggested fix: Within the no-accounts design, show the name on the USG screen as "Club name as entered by the sender (not verified)". Tell reviewers to confirm the application against EngageSC before citing a reason. Add a simple per-address limit on `/usg/send`. Record the limitation in PROGRESS.md as open.

### [medium] Re-drafting after approval changes the recorded reasons but leaves the old approved text, still marked approved
Where: backend/app/api/usg.py:177-195 (`row.denial_rule_ids` is overwritten; the status stays "approved")

Expected: The approved text and the rule ids it was approved for stay consistent. A change after approval needs a new approval.

What happened: I sent an application and drafted on `usg-food-cap`, then approved "Approved text A". I then drafted again on `usg-uepa-event-id`. Afterwards the detail shows `denial_status: "approved"`, `denial_rule_ids: ["usg-uepa-event-id"]` and `denial_approved_text: "Approved text A"`. The club still reads the food-cap text. The audit log's approval entry says `rule_ids: ["usg-food-cap"]`. The page (UsgScreen.tsx:113-114) then shows the new draft under a queue label of "Reason approved".

Reproduce: Using the integration-test body, run `/usg/send`, then `denial-draft` on rule A, then `denial-approve`, then `denial-draft` on rule B, then `GET /usg/applications/{id}`.

Suggested fix: Keep the approved rule ids in their own column (`denial_approved_rule_ids`). On a new draft after approval, either set the status to "draft" and leave the approved text visible to the club until a new approval, or refuse with 409 ("withdraw the approved reason first"). Add a regression test.

### [low] The reviewer passcode can be guessed without limit
Where: backend/app/api/usg.py:48-57

The comparison is sound: SHA-256 digests compared with `hmac.compare_digest`, a 12-character minimum, and the screen closed when the passcode is unset. There is no lockout or delay on repeated 401s, and the passcode is shared, so `reviewer_name` in the approval (usg.py:222-224) is self-declared. Suggested fix: add a small in-memory failure counter per address, and in the Phase 6 README note that the passcode must be a random string of at least 20 characters.

### [low] The approval routes take anonymous writes into the audit log
Where: backend/app/api/gap.py:59-67; backend/app/api/handover.py:60-66

Anyone can post any number of approvals of any text. Only a hash, the length and the role are stored, so no content is kept. A loop could still grow `audit_log` without limit. Suggested fix: a size or rate limit, or accept this and record it in PROGRESS.md.

### [low] Withdrawn applications keep their full budget and report forever
Where: backend/app/api/usg.py:128-137; backend/app/models/usg.py:36-39

Withdrawal only flips `status`. The club's lines, vendors and findings stay in the database with nothing to delete them. Section 9 says a club's data is private to the club. Suggested fix: on withdrawal, clear `request`, `report` and the denial fields, keeping only the reference, the token hash and the timestamps. Or record the retention in PROGRESS.md.

### [low] Logic is duplicated across features
Where:
- backend/app/services/usg_screen.py:73-75 (`_money`) repeats `money()` in backend/app/services/money_check.py:64-67.
- backend/app/services/gap_helper.py:268-274 (`figures_ok`, `_DIGITS`) repeats `_numbers_ok`/`DIGITS` in backend/app/services/application_draft.py:40 and 83-91, while backend/app/services/denial_draft.py:16 imports the private `_numbers_ok`.
- backend/app/api/gap.py:14 imports the private `_as_of` from api/money.py, while backend/app/api/handover.py:13 imports a different private `_as_of` from api/plans.py.
- backend/app/api/handover.py:14 imports the private `_club_row` from api/usg.py.

The features do reuse the rule engine (`build_packet`), the money check (`_check`) and the year plan (`plan_year`); these are smaller copies. Suggested fix: one public `money()`, one public figure check, and one `as_of` helper in `app/api/deps.py`.

### [low] The co-host option cites the permit-application rule without its campus-space scope
Where: backend/app/services/gap_helper.py:43-44; rules/events.json (`cosponsors-named-in-uepa`, `applies_to: "A co-hosted event in campus space"`)

The source says "For events in any campus space". The gap helper lists it as a condition of co-hosting whatever the venue, including off-campus. The email terms (gap_email.py:88-89) also state it without the scope. Suggested fix: cite it only when the venue is a campus venue or unknown, or add "for events in campus space" to the email sentence.

### [low] Test gaps
Where: backend/tests/integration/test_usg_api.py:51-55; backend/tests/unit/test_gap_helper.py:56-70
- `test_reviewer_routes_need_the_passcode` does not check `POST /usg/applications/{id}/denial-approve` without the passcode. That is the route that releases text to a club. The code is protected (usg.py:213), but no test would catch it if the dependency were removed.
- `test_options_never_include_a_banned_way` can never fail as written. The options are a fixed tuple, so for the 20 prompts it checks a constant. The real protection for exit criterion 1 is the email and note filters, which the other tests do exercise. Line 63 also contains a leftover `if True`. Suggested fix: add a test that the options are identical for every note, so a note can never change the list.
- There is still no recorded answer for `usg_denial_reason` (the iteration 1 low). In recorded mode the denial opening is always the plain fallback, and the success path runs only against a fake client.

### [low] The model-written denial opening is checked only for figures
Where: backend/app/services/denial_draft.py:80-87

The opening is replaced only if it contains a number the reasons do not state. A paragraph that predicts future decisions or adds reasons not in the list would be kept, which the prompt forbids. A person approves the whole text, so this is defence in depth only. Suggested fix: also replace the opening if it contains words such as "will not", "future", "never", "approved" or "funded" outside the fixed sentences.

## Checks that passed (no finding)
- **AI reads, code checks:** Code writes every option, status, lead time ("N days before the event") and shortfall in gap_helper.py. Neither prompt (gap_email.py:24-37, denial_draft.py:20-30) asks for a date, sum, comparison or verdict. The handover packet calls no model, and its figures come from `plan_year` and stored money-check reports. USG reasons are the stored report's own red, yellow and office-decides findings, so the model never picks a reason.
- **Citations:** Every option carries `citation` and `conditions`, and every banned item, reason and chart row carries a citation. The denial text quotes the rule and the source URL (denial_draft.py:52-63).
- **"Other USC funds":** Always `check_first` with a yellow finding. Ticket sales turn yellow when the event asks USG, and a late step turns an option yellow (iteration 2 fix).
- **Human approval and no sending:** No route sends anything. The club sees a denial reason only when `denial_status == "approved"` (usg.py:121-124), and the approved text is the reviewer's edited text. The email, the denial and the three packets are editable textareas with an explicit approve button. Editing clears an earlier approval on the page.
- **Club access:** The token is 192 bits from `secrets.token_urlsafe(24)` and only its SHA-256 is stored. Comparison is constant-time, and the same 404 is returned for an unknown reference or a wrong token. Reviewer routes return 404 for withdrawn rows. The handover refuses another club's reference (404). Uploaded documents are dropped before storage, but their findings are kept (iteration 2 fix, tested by test_phase5_iter2_break.py:60-71).
- **Untrusted text:** Officer details and reason text go to the model only inside an `UntrustedDocument`, and `contains_instructions` is surfaced as a note.
- **Earlier fixes:** The iteration 2 regression tests really exercise the fixes: the quote mismatch reaches the reviewer, post-event duties are not citable, the Bookstore and cash approvals are listed, a late step turns the option yellow, notes in other languages are flagged, names and the ask are filtered, and model paragraphs in other words are replaced. All pass. The iteration 1 medium (cash in the ask line) is fixed for money words but not for the phrasings in the high finding above.
