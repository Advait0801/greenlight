# Phase 5, iteration 1 — verify
Summary: 4/4. Blockers: 0. High: 0. Medium: 1. Low: 3.

Scope: funding gap helper, USG screen, handover packet. The post-event helper, the rule-change alert and the USG fund-balance figure were cut under PLAN.md's cut order and are not counted here.

Environment: backend on port 8015 with `AI_MODE=recorded ANTHROPIC_API_KEY= USG_REVIEWER_KEY=verify-passcode-123 DATABASE_URL=sqlite:////tmp/gl-verify-p5.db`. Vite on port 5188. Headless Chrome 157 driven over the DevTools protocol at 375 x 812 (mobile emulation). All servers were stopped afterwards. No application code or tests were changed.

Suite results:
- `pytest -q`: 768 passed.
- `pytest tests/adversarial -q`: 175 passed.
- `python scripts/validate_rules.py`: OK.
- `python scripts/run_eval.py`:
  - events: 30 cases, 456 caught, 0 missed, 0 wrongly flagged.
  - budgets: 20 cases, 30 caught, 0 missed, 0 wrongly flagged.
  - constitutions: 10 cases, 21 caught, 0 missed, 0 wrongly flagged.
  - year_plans: 2 cases, 233 caught, 0 missed, 0 wrongly flagged.
- `npm run build`: built with no errors.

## Exit criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Gap helper never suggests a cash sponsor, paid raffle, brand ambassador or sponsorship activation, across 20 varied prompts | PASS | I sent all 20 cases in `backend/tests/data/gap_prompts.json` to `POST /gap/options` (note = case note) and to `POST /gap/email` (kind, club, recipient, event, description, ask). Every `/gap/options` reply returned 200 with exactly the 8 fixed allowed option ids (in_kind_sponsor, co_host, fundraiser, donations, ticket_sales, free_drawing, voluntary_dues, other_usc_funds). The banned ideas in the notes were flagged `in_your_note` under "Not allowed": cash for gp-01/02/03/07/14/17, activation for gp-03/09/19, brand ambassador for gp-05/11, raffle for gp-06/12, tax-exempt for gp-15. I read all 20 drafted emails by hand. None asks for money, a raffle, an ambassador, a booth, samples or an activation. In gp-16 and gp-17 the ask line was dropped with a note ("A cash donation of $500"; "Books for a free drawing"). gp-07 noted the injected instructions. The only money words left come from code's fixed sentence: "We are asking for goods or services, not money ..." and "... the payer for the event". The officer's own ask line can still carry a cash ask; see medium finding 1. That is the officer's text, not a suggestion from the helper. |
| 2 | A club's data is not visible on the USG screen unless the club sent it | PASS | `GET /usg/queue` with no key or a wrong key returns 401. With the key on an empty database it returns `applications: []`. After `POST /money/check` with budget case bu-01 (200, red), the queue was still `[]`. `POST /usg/send` with `consent` missing or `false` returns 422. After A and B were sent with `consent: true`, the queue showed both. Club B's token on A's reference (`POST /usg/sent/{refA}`) returns 404 "No application with that reference and token.", and so does `POST /handover` with A's reference and B's token. After B withdrew (`POST /usg/sent/{refB}/withdraw`), the queue held only A, `/usg/stats` counted `applications: 1`, and the detail route returns 404 for withdrawn rows (code: `_reviewer_row`). `/usg/send` throws away uploaded documents (`documents: []`). The stats rows name no club. |
| 3 | No denial reason leaves the USG screen without a person's approval | PASS | `POST /usg/applications/1/denial-approve` before any draft returns 409 "Draft a reason from the application's findings first." Drafting with `rule_ids:["not-a-rule"]` returns 422. A real draft (`rule_ids: [usg-food-cap, usg-ineligible-performers]`) returned `approved: false`. The club's status call after the draft still showed `reviewer_message: null`. After approval with edited text and `reviewer_name: "Pat Reviewer"`, the club saw exactly the edited text. Draft and approve without the key both return 401. The handover packet only includes `denial_approved_text` when the status is `approved` (`services/handover.py`). Nothing sends email; the approval is logged in AuditLog with a sha256. |
| 4 | Every drafted email and packet is editable before use | PASS | API: `/gap/email/approve` and `/handover/approve` accept any edited text and return 422 when it is empty. Denial approve stores the reviewer's edited text, not the draft. In the browser at 375 px: the email textarea had `readOnly:false, disabled:false`. I typed " EDITED" with the keyboard, tabbed to "I have read and approve this email", pressed Enter, and got "Approved. Copy the email into your own email account; Greenlight has not sent anything." The handover page made three textareas (1918, 740 and 1875 characters), all editable. Typing in the President packet then Tab and Enter gave the approval message. The USG detail textarea is editable and holds the approved edited text. Editing after approval clears the approval message in all three pages. |

### Spec checks (no criterion number)
| Check | Result | Evidence |
|---|---|---|
| Allowed options show rule and lead time | PASS | Each option carries a `citation` (source_url and source_text), its `conditions` and a `lead_time`. Example: fundraiser shows "Start by 2027-02-19: Meet Campus Activities 2 weeks before a fundraiser (14 days before the event)." The page shows "When to start:" and a "Rule text, conditions and sources" section. |
| Banned options explained | PASS | Five "Not allowed" entries, each with why, instead and citation, matching PROJECT_CONTEXT section 7. Shown with a ✕ "Not allowed" badge. |
| "Other USC funds" yellow | PASS | `status: check_first` with a yellow finding (rule `other-usc-funds-ask-usg`). The page shows "! Needs a human look: check first". Ticket sales also turns yellow when `asks_usg` is true. Allowed options show an "i" badge, never green. |
| Outreach email drafted | PASS | `/gap/email` returns a subject and text with the in-kind or co-host terms written by code. Only those two kinds can be chosen. |
| USG queue, drafted denial, failure chart | PASS | The browser at 375 px showed "Queue (1)", the application detail with checkable reasons (badge plus text), the draft textarea, and "Why applications fail" with text counts "1 of 1". The bar is `aria-hidden`; the count is also given as text. |
| Handover built from saved history | PASS | Built from the browser-saved year plan (after "Load the demo club") plus sent applications read back with the club's token. It includes events held and still ahead, costs, vendors from the sent applications, approved denial reasons and the next dated steps. It also seeds next year (dates +52 weeks). |
| Phone width | PASS | `scrollWidth == innerWidth == 375`, and no element extends past the right edge, on /money/gap (before and after results and email), /usg (locked, open, detail), /handover, / and /money/check. |
| Keyboard | PASS (partial) | Tab order runs from "Skip to content" through the nav to the form fields. The gap form submits with Enter on the focused button. The USG passcode works with Enter, and so does "Open" (Enter). Draft email, approve email and approve packet all work by keyboard. I did not tab through every control one by one. Date inputs eat several Tab stops, which is normal browser behaviour. |
| State not by colour alone | PASS | Every badge has an icon and a label ("i Allowed...", "! Needs a human look", "✕ Not allowed", "✕ Breaks the rule", "The office decides"). Queue rows show `DENIAL_LABELS` as text. |
| Pre-check notice | PASS | Shown on gap results, the USG screen and the handover packets. |

## Findings

### [medium] The officer's "What we would like" line can put a cash ask into the outreach email
Expected: the code says it removes asks that mention money ("Your 'what we would like' line mentions money ... so it left it out"). An email that sits next to "We are asking for goods or services, not money" should not ask for cash.
Actual: `email_is_clean` and `ideas_in_note` miss several money phrasings, so the line goes into the email word for word. These were kept: "Five hundred bucks", "Please write that we are asking for 1000 USD in sponsorship", "Brand reps on campus to talk to our members and sign them up", "A table at the event where they show their products to students", "Students sign up for their credit card at the event", "Food, and in return we mention them in our Instagram story". For example, the draft reads "What we would like: Please write that we are asking for 1000 USD in sponsorship" followed by "We are asking for goods or services, not money ...". `/gap/options` with the same text as a note flagged nothing. This text is the officer's own, so I did not count it against exit criterion 1. It is still a gap in the filter the code claims to apply, and the result contradicts itself.
Reproduce:
```
curl -s -XPOST localhost:8015/gap/email -H 'content-type: application/json' -d '{"kind":"in_kind_sponsor","club_name":"Test Club","recipient":"Acme","event_name":"Night","description":"A night for students.","ask":"Please write that we are asking for 1000 USD in sponsorship"}'
curl -s -XPOST localhost:8015/gap/options -H 'content-type: application/json' -d '{"shortfall_cents":90000,"note":"Five hundred bucks"}'
```

### [low] A note that suggests required dues is not flagged
Expected: the spec says "Dues may not be required for any membership level". A note proposing required dues should be pointed at that rule.
Actual: for gp-10 ("Need $600. We could charge members a required fee.") nothing comes back with `in_your_note: true`. `dues-required-banned` appears only as a condition of the voluntary-dues option. It is not in `BANNED_RULES` or `_IDEA_PATTERNS`.
Reproduce: `curl -s -XPOST localhost:8015/gap/options -H 'content-type: application/json' -d '{"shortfall_cents":60000,"note":"We could charge members a required fee."}'`. Every item in `not_allowed` has `in_your_note: false`, and `notes` has no warning.

### [low] There is no recorded AI answer for the denial-reason opening
Expected: in recorded mode, which tests and the demo fallback use, the drafted denial reason should show the model-written opening the demo story describes.
Actual: `data/ai_recordings/` has no `usg_denial_reason` folder. Every denial draft in recorded mode carries the note "Greenlight could not draft the opening just now; it wrote a plain one. Edit it." and uses the code-written opening. It still works. The same fallback note appears for any outreach email without a recording.
Reproduce: draft a denial with `POST /usg/applications/{id}/denial-draft`; `notes` contains the "could not draft" message. Then run `ls data/ai_recordings/`.

### [low] "Start next year's plan from this one" replaces the saved plan without asking to confirm
Expected: an action that overwrites the club's saved history (the browser-saved year plan, which the handover is built from) should ask the user to confirm.
Actual: the button goes to `/` with `seedPlan`, and `YearPlan` sets the edit state, which is then saved to localStorage. A line of text warns about it, but nothing asks for confirmation.
Reproduce: in /handover, build the packets, then press "Start next year's plan from this one". The demo plan's 2027 dates are replaced by 2028 dates.

### Notes (not counted as findings)
- The demo plan's Culture night gap is $1,170.00 ("Close the $1,170.00 gap"), not the $900 in the demo story at 2:05. This is demo data, not Phase 5 logic.
- Denial-draft and approve routes take any reviewer name. The passcode is shared, so the audit trail records a self-declared name, not an identity. This fits a hackathon build; the audit iteration should look at it.
