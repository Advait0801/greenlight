# Phase 5, iteration 2 — break
Summary: 0 blockers, 4 high, 2 medium, 1 low. Tests added: backend/tests/adversarial/test_phase5_iter2_break.py (22 failing cases across 9 tests).

## Findings

### [high] Sending to the USG screen drops the club's quote-mismatch finding
Expected: The USG reviewer sees at least the problems the club's own money check found. Section 9 says every finding carries its rule, and the queue is meant to "arrive pre-checked, with findings".
Actual: `POST /usg/send` sets `documents: []` and checks the budget again. Every document finding disappears: a quote total that does not match the budget, an unreadable quote, a non-dollar currency, an unlinked document, and the "contains instructions" note. In the test, the club's check says the quote totals $4,500.00 while the budget lists $1,500.00. On the USG screen the line shows "A quote is attached" and no mismatch reason. The overall verdict did not turn green only because of the date reminders. The reviewer still gets a cleaner picture than the club's own check gave.
Reproduce: `test_sending_to_the_usg_screen_keeps_the_quote_total_mismatch_finding`

### [high] Event name and recipient put banned asks into the outreach email unfiltered (exit criterion 1)
Expected: No drafted outreach email asks for cash, a raffle or brand ambassadors. The "what we would like" line is filtered for this reason.
Actual: `event_name`, `recipient` and `club_name` go into the subject, the greeting, the fallback paragraph and "Could we set up a short call about ..." word for word, with no filter and no note. If the event name is `Red Bull $500 cash sponsorship + raffle night`, both the subject and the body ask for $500 cash and a raffle. If the recipient is `Red Bull brand ambassadors`, the email opens "Dear Red Bull brand ambassadors,". The existing unit test hides this because `_drafted_part` removes the "Dear" line and never looks at the subject.
Reproduce: `test_officer_fields_written_into_the_email_carry_no_banned_ask[event_name-...]`, `[recipient-...]`

### [high] The "what we would like" filter misses banned asks in other languages, look-alike letters and plain synonyms (exit criterion 1)
Expected: PLAN.md asks the breaker to try other languages and odd spellings. A banned ask must not go into the email word for word.
Actual: Each of these is kept as "What we would like: ...": `patrocinio en efectivo`, `premios para una rifa`, `现金赞助`, `сash sponsorship` (Cyrillic с), `a bank transfer`, `bitcoin`, `an honorarium`, `campus representatives for your brand` (brand ambassadors), `a giveaway where buying a drink enters you to win` (a raffle that needs a purchase), and `a table for your company to demo its product to attendees` (a sponsorship activation). The model's paragraph goes through the same English-only word list, so a Spanish paragraph asking for "patrocinio en efectivo y ... una rifa" also gets through (see the medium finding below).
Reproduce: `test_ask_line_with_a_banned_ask_in_other_words_is_left_out[*]` (10 cases)

### [high] The "fundraiser or sales" option leaves out the Bookstore and cash approvals
Expected: Section 7 says a fundraiser or sales needs a "Campus Activities meeting 2 weeks before; item sales need Bookstore approval; cash at an event needs TES and DPS approval". The rules exist (`item-sales-bookstore`, `cash-collection-approval`).
Actual: The option only adds the `fundraising` activity. Its steps and conditions are the meeting, the TES form, office-decides and no-individual-benefit. The Bookstore approval and the cash approval are not listed or flagged. This is a silently missing obligation.
Reproduce: `test_fundraiser_or_sales_option_lists_bookstore_and_cash_approvals`

### [medium] An option whose lead time has passed is still shown as "Allowed"
Expected: For an event on 2026-11-20 checked on 2026-11-15, the fundraiser's 2-week Campus Activities meeting was due 2026-11-06. The option should not say "Allowed, with the conditions below" without an option-level warning.
Actual: `status: "allowed"`, `finding: null`, `lead_time: "Start by 2026-11-06: ..."`. The step does carry `past_due: true`, but the headline tells the officer to start by a date already past. The same happens for donations and ticket sales.
Reproduce: `test_option_whose_lead_time_has_passed_is_not_shown_as_allowed`

### [medium] Post-event reminders are offered as denial reasons; the model's paragraph is filtered by an English-only list
Expected: A denial reason says why an application fails a rule (section 4I: "For an application that breaks a rule, a drafted denial reason citing the guideline").
Actual: `reasons()` treats every yellow date obligation as citable. The reviewer can pick `usg-post-event-evaluation` ("Submit the evaluation within 3 business days after the event") or `usg-final-invoices`, and `denial-draft` writes a denial built on them. These are future duties, not defects. Also, `email_is_clean` lets through a model paragraph in Spanish asking for cash and a raffle, and one asking for "campus representatives ... to sign up students for your brand".
Reproduce: `test_post_event_reminders_are_not_offered_as_denial_reasons[*]`, `test_model_paragraph_asking_for_banned_help_in_other_words_is_replaced[*]`

### [low] Banned ideas in a non-English note are not marked "in your note"
Expected: A note in Spanish or Chinese that asks for a cash sponsor or a raffle is marked under "Not allowed" as mentioned in the note.
Actual: `ideas_in_note` is English-only. The banned list is still shown, so nothing banned is suggested; only the highlight is missing.
Reproduce: `test_banned_idea_in_another_language_is_flagged_in_the_note[*]`

### Questions (spec silent; no test)
- A reviewer can approve any text at `denial-approve`, including reasons that are not among the application's findings. Editing is allowed by design, so it is unclear whether the approved text must still cite only the drafted rule ids. Right now the stored `denial_rule_ids` and the approved text can disagree. Drafting again after an approval also overwrites `denial_rule_ids`, while the club keeps seeing the old approved text.
- The denial opening the model writes is checked only for figures. A paragraph saying "your application is approved and will be funded" would reach the draft. A person approves it, but code does not enforce the prompt's "do not promise funding".
- A club that sends the same application twice gets two queue entries, and the failure chart counts it twice.
- `club_name` on `/usg/send` is not verified. Anyone can send an application in another club's name. There are no logins, so this may be accepted.
- The donations option shows the 2-week fundraiser meeting as its lead time. Section 7 says donations are "arranged via Campus Activities" and gives no lead time.
- The handover route and the club status route handle whitespace differently: handover strips the token, but `/usg/sent/{reference}` does not.

## What I tried that held up
- Option list: the eight options come from a fixed table, so no note, injection text, event name or attribute adds a cash sponsor, a paid raffle, a brand ambassador or an activation. All six banned rules are always listed. Unknown attributes return 422.
- Ask-line filter: catches English money words, digits, "c4sh" (via the figure check) and a zero-width "ra​ffle prizes" (via "prizes").
- Reviewer routes: 401 without the passcode or with a wrong one, 503 when the passcode is unset or under 12 characters.
- Club status, withdraw and handover: all need the reference and the matching token, and all answer 404 the same way for an unknown reference and a wrong token. A lower-cased reference is refused. Another club's application cannot be read into a handover packet.
- Withdrawn applications leave the queue, the detail page, the chart and denial draft/approve (404), but stay visible to their own club.
- `consent` must be literally `true`. Extra fields on `/usg/send` are refused (422). A check alone never reaches the queue. Lines that point at stripped documents do not crash the check.
- The club sees a reviewer message only after `denial-approve`, never the draft. Handover packets include only approved text. `denial-draft` refuses rule ids that are not among the application's own findings (422). `denial-approve` without a draft returns 409.
- The failure chart is aggregate: no club or event name, red findings only, withdrawn applications excluded.
- No route exposes the audit log or the stored application to anyone but the reviewer.
- Handover: an empty plan, an `as_of` of 2028-02-29, and an `as_of` far in the past (422) are all handled. The next-year seed keeps the weekday.
- Editability: the email subject and body, each handover packet and the denial text are editable text areas in the frontend, and each approval route records a person's approval of the edited text and sends nothing.
