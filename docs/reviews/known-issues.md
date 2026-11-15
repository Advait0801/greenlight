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
