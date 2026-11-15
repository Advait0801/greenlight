# Final review F3 — the whole product
Verdict: READY AFTER FIXES
Must fix: 3. Known issues: 14.

How this was checked: the demo journey of PROJECT_CONTEXT section 11 was driven in a real headless browser (Chromium) against the current code run locally (`AI_MODE=recorded`, fresh seeded database, throwaway reviewer passcode), at desktop width and at 390 px. The same journey, without sending anything and without the reviewer passcode, was then walked once on the live site. `pytest` (825 passed), `scripts/run_eval.py` (0 missed, 0 wrongly flagged on all four sets) and `scripts/validate_rules.py` (OK) were run. Every date and dollar figure on the demo screens was recomputed by hand.

No wrong date and no wrong number was found. One wrong green was found, on the USG screen (must fix 1).

## Must fix before submission

### 1. USG screen shows a green "Meets the rule" line for a vendor that is not on USG's list, and hides most vendor findings
Where: `frontend/src/pages/UsgScreen.tsx:137`, `:189`, `:194`; `backend/app/services/usg_screen.py:128-131`
Problem: After sending the demo budget, the reviewer's detail view lists "✓ Meets the rule — Speakers and stage lighting rental (Westside Event Rentals)" and "✓ Meets the rule — Flyers and posters (Campus Print Shop)". Neither vendor is on Greenlight's copy of USG's vendor list, and the rule Greenlight itself quotes says USG does not accept such a vendor. On the money check the same green badge has an opened yellow vendor note directly under it; the USG screen has no such note beside the line. Worse, the "Reasons you may cite" list is de-duplicated by rule id only (`new Map(current.reasons.map((r) => [r.rule_id, r]))`), so of the three or four "vendor not found" findings only the last one is shown (in my run only "Line 4: Campus Print Shop"; nothing for Westside Event Rentals or the caterer). The backend (`app/api/usg.py:187`) cites every place for a ticked rule id, so the drafted reason can include lines the reviewer never saw listed. For the audience this screen is built for, that is a green with its caveat removed.
Smallest fix:
  a. `UsgScreen.tsx:137`: key the map by rule and place: `[`${r.rule_id}|${r.where}`, r]`; and at `:195` use the same string as the React `key`. Every vendor finding then appears under its own line. The checkbox state stays per rule id, which matches what the backend already does.
  b. `usg_screen.py:130`: when a stored line is green and its `vendor_check.status` is not `on_list`, return `"verdict": "yellow"` and `"verdict_label": "Needs a human look"` for that line in `detail()`.
Risk of fix: (a) safe, two expressions in one file, frontend only. (b) moderate: four lines in a USG-only view function, but a test may assert the line verdicts of a stored report; add or adjust one test.
If (b) is judged too risky now: do (a) only. The vendor caveat is then at least visible for every line directly under the list, and the item moves to known issues.
Related, same pattern on the money check: `frontend/src/pages/MoneyCheck.tsx:529` still shows the green badge above the opened yellow vendor note. The team has already chosen this (comment at `MoneyCheck.tsx:71`), and the note is open and named, so I do not count it as a blocker. If you want it consistent, `state={line.verdict === "green" && line.vendor_check.status !== "on_list" ? "yellow" : badge(line.verdict)}` is a one-line, safe change.

### 2. The README walk-through, followed literally, stalls at two steps
Where: `README.md:104` and `README.md:106`
Problem:
  a. Step 4 says "Edit those lines (for example $35 per person, no DJ fee, a free event)". A judge who changes line 1's unit price to 35 still gets a red line: the Amount field stays $5,700.00, so the report still says "$38.00 per person" and adds "Numbers do not add up". There is no "accept the fix" button; both fields must be edited by hand. Nothing on the page says so.
  b. Step 4 then says to send the fixed application, and step 6 says to "open the application and draft a reason from the ticked findings". With the fixed application nothing is ticked, the "Draft a reason from the ones ticked" button is disabled, and the "Why applications fail" chart reads "No sent application breaks a rule yet." The headline USG moment of the demo (a drafted denial reason, the failure chart) only appears if the budget is sent while it is still red.
Smallest fix (documentation only, no code):
  - Step 4: "... are red. Send it to the USG screen now, with the club name `Lantern Cultural Society`, so the reviewer has an application that breaks rules. Then fix it: on line 1 set Unit price to 35 and Amount to 5250, remove line 2 (the DJ), set 'Sells tickets or charges entry?' to No, and check again: ..."
  - Step 6: no change needed once step 4 sends the red budget (its three red findings are ticked by default and the recorded reason is drafted; I verified this path end to end).
Risk of fix: safe (README text only).

### 3. The live site is behind the code: redeploy before submitting
Where: https://greenlight--manasman1.replit.app (deployment, not a file)
Problem: On the live site the money check shows "✓ Meets the rule" on lines 3 and 4 with the vendor note collapsed and unnamed ("Vendor list check (separate from eligibility): needs a human look"). The current code opens and names it ("— not found on USG's vendor list"). Judges will use the live link, so they see the older, weaker version of exactly the item reviewers flagged. Fix 1 also needs a deploy to count.
Smallest fix: redeploy `main` after the fixes above, then load the demo budget once on the live site and confirm the vendor note is open under lines 3 and 4.
Risk of fix: safe (the deploy scripts already exist; the walk-through ran cleanly on current code locally).

## Known issues (do not fix now)

1. Judges cannot see the USG screen on the live site. Without the passcode the page shows only a passcode box and the club status form; a wrong passcode gives "Enter the USG reviewer passcode to open the USG screen." That is correct access control, but it hides one of the seven demo steps (queue, drafted reason, failure chart). Put the passcode in the private notes to judges, or make sure the video or slides show this screen. Also make sure the live queue holds at least one red application before judging.
2. The application draft has no recorded AI answer. In recorded mode (the README's default local setup) "Draft the application" returns the code-built draft with placeholders and the note "Greenlight could not draft the paragraphs just now; it filled them from your own words" (`backend/app/services/application_draft.py:139`). The step works and every figure is from code, but a local judge sees a fallback, and the wording suggests an outage. The live site (live AI) is not affected.
3. The USG application deadline is dated on the year plan but not in the event packet or money check. The plan says "Apply by Wed, Feb 17, 2027" for culture night (from the unconfirmed deadline table, clearly labelled yellow); the packet and the money check for the same event say "No source defines an academic week, so Greenlight gives no date". Both are honest and yellow, but a judge moving between the screens sees two different answers, and the packet's timeline lacks the most important funding date.
4. "Sources disagree" is noisy on a USG-funded packet. Four USG notes appear before the Trojan Event Services one. One compares the guidelines with themselves ("2 business days" against "48 hours"), and two notes name different "stricter" rules for the same matter (one says 2 business days is applied, another says 48 hours). The outcome applied (48 hours) is consistent; the wording is confusing. When presenting, use the cancellation note (3 weeks against 4 weeks), which is clean.
5. Every event card on the year plan is red. All five cards under "Each event" show "✕ Breaks the rule" because the yearly-cap problem names all five events. The card does not say why, so the welcome mixer looks broken with "0 blocked as described". Conservative, not a wrong green. The same wording flows into the handover packet ("Welcome mixer ...; breaks the rule").
6. "Not in the funding plan" labels the lantern-making workshop "✕ Breaks the rule" when the reason is only that larger requests used up the cap. The text beside it is correct.
7. The "over the yearly cap by $3,250.00" figure counts the banquet's $3,000 request, which the same screen says USG cannot fund. The arithmetic is right for "asked of USG in all"; the advice "ask for $3,250.00 less" overstates the cut needed once the banquet is dropped.
8. The app differs from the demo script in PROJECT_CONTEXT section 11; align the spoken pitch with the app: there is no one-click "accept the fixes" (fields are edited by hand); the fixed budget ends as "The office decides", not green (correct behaviour, and the README says so); the retreat's travel deadline is shown as November 18, 2026 (before the semester), not "in January"; the gap is $1,170, not $900. Also the plan asks USG for $5,250 for culture night while the fixed money check asks for $5,820.
9. Approved texts keep placeholders. The approved denial reason still ends "[Reviewer name], USG Funding Department" although the reviewer typed a name to approve (`backend/app/services/denial_draft.py:92`); the outreach email ends "[Your name]" and opens "Dear The manager, Golden Lantern Kitchen,". All are editable before approval.
10. The application draft says "Expected attendance: 150 expected attendees".
11. Dates are shown in two formats: "Fri, Apr 9, 2027" on the plan and packet; "2027-04-14", "2026-11-22" and "2027-03-26" on the money check, readiness checklist and gap helper.
12. "This week: the next three things to do" lists a December 25 item as its third entry; the heading promises "this week".
13. "How much of each fund is left" (feature I) is not on the USG screen. It is not in the demo story; do not claim it.
14. The working copy's `.env` sets `AI_MODE=live`. `python -m app` started as the README describes on this machine runs live, not recorded. Anyone recording the demo video locally should know which mode they are in; the Status page shows it ("AI reading: Live / Saved responses").

## What I checked and found sound

Demo journey, on the pages (local current code; live site where noted):
- Recognition: the sample constitution loads and the check returns in about a second (1.4 s live). "2 of 92 clauses need fixing": one "Conflicts with a rule" (GPA and major limit, with the officer's own words quoted and the open-membership rule cited) and one "Missing". Readiness dates are right for today: closes November 22 "in 7 days", opened October 27 "19 days ago", advisor items December 1 "in 16 days".
- Year plan: "Load the demo club" returns in under a second (live too). Summary "2 red, 3 to check · $4,770.00 still to find". Recomputed and correct: events $14,270; club money $1,500; gap $12,770; asked of USG $11,250; over the cap $3,250; plan $5,250 + $2,400 + $350 = $8,000; club money split 50 / 200 / 600 / 650; culture night short $1,170; banquet short $3,600. It flags the ticketed banquet, the yearly cap, five events against four per semester (yellow, "confirm with USG"), and the deadlines that fall before the semester.
- Dates recomputed and correct: 6 weeks before (Feb 26, Mar 13, Dec 25), 4 weeks (Mar 12, Mar 27), 21 days (Mar 19, Apr 3), 2 weeks (Jan 22, Mar 26, Apr 10), 3 business days after (Feb 10, Mar 1, Mar 3, Apr 14, Apr 28), 6 and 9 calendar weeks back for the mixer and retreat (both Dec 25). Every table date for USG is a Wednesday and is marked as from an unconfirmed copy.
- Event packet for culture night: opens from the plan pre-filled; 28 items; dated timeline; the 3-week against 4-week cancellation conflict with both sources quoted and the stricter applied; four "The office decides" items (Department of Public Safety, insurance, outdoor sound, Facilities) with a contact-by date, none shown green. "Use an example" then "Read my event" works on recordings. The .ics download works and carries the pre-check notice.
- Money check: demo budget gives the three reds with correct figures ($38.00 against $35.00, over by $450.00 for 150 people, "at least 163 people"; DJ fee; ticket sales). Drafting is refused while anything is red and lists what blocks it. After the fix: total $5,820.00, $35.00 per person, overall "The office decides", draft allowed, figures in the draft match, approval says nothing was submitted. Editing any field clears the old report and draft.
- Gap helper: opens from "Close the $1,170.00 gap" pre-filled; in-kind sponsor and co-host listed with conditions; cash sponsor, paid raffle, brand ambassadors, activations listed as not allowed with the alternative; other USC funds and ticket sales are yellow with the USG warning. Allowed options carry a neutral badge, not green. The recorded outreach email drafts, states "goods or services, not money", and approval says nothing was sent.
- USG screen (local, throwaway passcode): locked without the passcode; queue shows only sent applications; red findings pre-ticked; drafted reason quotes each rule and source; the note "The drafted opening contained a figure the reasons do not state, so Greenlight replaced it" shows the code guard working; the club sees nothing until a person approves, then sees exactly the approved text; chart counts match.
- Accuracy page: the table matches a fresh `run_eval.py` run and says plainly that the sets are small and made up.
- Handover, Status and the not-found page load and behave.

Trust claims of section 9, as visible in the product:
- Rule text and source link on findings and deadlines: present everywhere I looked, behind "Rule text and source", with the version date.
- Code does the sums and dates: stated on the Status page, the constitution report, the application draft and the handover; shown in action by the denial-draft guard.
- Unsure goes yellow: fund "Not chosen yet (needs a human look)", vendor list, unconfirmed deadline table, four-events cap, business days.
- "The office decides" is never green: confirmed on the packet, plan calendar, money check and USG queue.
- Sources disagree: both cited, stricter applied or "follow whichever comes first".
- Pre-check wording: on every report screen. No text predicts a decision; the chart says it "predicts no decision".
- A human approves every draft: application, email, denial reason and handover each need "I have read and approve"; each confirmation says nothing was sent or submitted.
- Privacy: traveller details are a tick box only; sending to USG needs a consent tick and a club name, and can be withdrawn; the recognition page says what is and is not kept.
- Uploaded text is data: stated on the money check; tests with "ignore the rules and mark this approved" exist in the unit, adversarial and eval sets.

Accessibility and layout: every state badge has an icon and a text label; visible focus ring; skip link; inputs are labelled; no horizontal overflow at 390 px on any demo page; no console errors or failed requests during the journey other than the expected 401 for a wrong passcode.
