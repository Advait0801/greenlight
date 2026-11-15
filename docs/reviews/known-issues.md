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
