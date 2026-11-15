# Known issues at submission

Medium and low findings from the three final reviews. Phase 7 fixes blockers and highs only; these are left in the code on purpose. Earlier phases' open findings are in `docs/PROGRESS.md`.

## From final review F1 (correctness)

- **Pitch wording vs the app on the retreat deadline.** PROJECT_CONTEXT section 11 says the retreat's travel deadline "lands in January"; the app shows Wednesday, November 18, 2026, which is what the USG deadline table gives for a February retreat. Fix the pitch, not the code.
- **A deadline can land on a closed day.** The welcome mixer's "request the venue" step falls on December 25 (winter recess) and appears in "This week". It is shown yellow.
- **An "apply by" date can be a Monday.** Taking the earlier of the calendar-week count and the deadline table can give a Monday, though USG deadlines fall on Wednesdays.
- **One USG web-page deadline is never dated.** "Nine academic weeks before the first payment, whichever comes first" does not set the plan's "apply by" date; the rule itself is shown yellow.
- **Tabling blocked days.** `tabling-blocked-days` shows green after checking holidays only; a separate yellow rule covers Welcome Week and football days.
- **Two answer-key differences, both on the safe side.** Events case ev-28: one rule shows "check with the office" where the key expects "rule to keep". Constitution case co-09: one clause is "weak" where the key expects "contradicts".
- **Vendor result and the line badge.** The line's badge covers eligibility only; a vendor not on USG's list is shown in the opened vendor panel, not in the badge (counting it in the badge would turn 19 expected-green test-set lines yellow).

## From final review F2 (security, privacy and robustness)

- **Reviewer passcode (human check, no code).** Review reports in this repository quote the local test passcodes used during development. The deployed `USG_REVIEWER_KEY` must be none of them and should be long and random; a person checks the Replit secret.
- **An AI reading that follows planted text can make one line green.** If the model obeyed text inside a quote and labelled a line with a harmless category, that line could pass; the officer sees and can edit the category, and the overall verdict was yellow in the test. The comment in `backend/app/ai/untrusted.py` claims more than the code guarantees.
- **Anyone can run up the Claude bill.** Live AI mode with no rate limit; one pasted event list can make up to 20 calls. Set a spend limit on the API key, or switch the secret to `AI_MODE=recorded` (the demo still works from recordings).
- **No rate limit or lockout on wrong reviewer passcodes.**
- **API docs are public** at `/api/docs`, `/api/redoc` and `/api/openapi.json`. They hold no secrets.
- **AI readings go into the audit log uncensored.** Names inside an uploaded invoice or constitution would be stored; "traveller details are not stored" is true only for the traveller checkbox.
- **Withdrawn applications stay in the database.**
- **The USG screen shows what the club entered.** Its findings come from budget lines and readings the club sent.
- **No limit on the total size of one upload request;** files are written to disk before the size checks.
- **Some unusual API client errors become plain 500 errors.** Never green.

## From final review F3 (the whole product)

- **USG screen needs the passcode.** Judges without it see only the passcode box; show that step in the video or give the passcode privately, and make sure the live queue holds a red application.
- **Recorded mode has no recording for the application draft;** it returns the code-built draft with a note that the paragraphs could not be drafted. The live site is not affected.
- **The year plan dates the USG application deadline** (Feb 17, 2027, yellow, from the unconfirmed table); the event packet and money check for the same event give no date.
- **"Sources disagree" is noisy on a USG-funded packet** (four USG notes, one comparing the guidelines with themselves). Present the 3-week against 4-week cancellation note in the demo.
- **All five year-plan event cards are red** because of the shared yearly-cap problem, with no reason on the card; the lantern-making workshop is labelled "Breaks the rule" when the cap is used up by larger requests.
- **"Over the cap by $3,250" includes the banquet's $3,000**, which the same screen says USG cannot fund.
- **The app differs from the section 11 script:** no one-click "accept the fixes"; the fixed budget ends as "the office decides", not green; the retreat deadline is Nov 18, 2026; the gap is $1,170, not $900; the plan asks USG for $5,250 while the fixed money check asks for $5,820. Align the spoken pitch.
- **Approved texts keep placeholders** ("[Reviewer name]", "[Your name]", "Dear The manager,").
- **"150 expected attendees" after "Expected attendance:"** in the application draft.
- **Dates appear in two formats** (ISO on the money check, readiness checklist and gap helper).
- **"This week" lists a Dec 25 item.**
- **"How much of each fund is left" is not on the USG screen;** do not claim it.
- **A local `.env` with `AI_MODE=live`** makes a local start run live, not recorded; check it before recording the demo video.
- **The money check's line badge stays green above the opened vendor note** (badge covers eligibility only; the USG screen now shows such lines as needing a look).
