# README rewrite, iteration 2 — audit

Scope: `README.md` in the working tree (modified, uncommitted) on 2026-11-15, read as a judge, a new contributor and a USC club officer would read it, against the style sample `InterviewForge/README.md`. Report only; nothing fixed.

Summary: 0 blockers, 2 high, 5 medium, 12 low.

## Checks that passed (evidence)

| Claim | Evidence |
|---|---|
| 827 tests, 201 adversarial | `pytest --collect-only -q`: 827; `pytest tests/adversarial --collect-only -q`: 201 |
| 289 rules (71 / 76 / 22 / 120), 284 read, 5 unverified, 15 dependent | `python scripts/validate_rules.py`: exact match, `OK` |
| Eval table (30/456, 20/30, 10/21, 2/233, 0 missed, 0 wrongly flagged; 740 total) | `python scripts/run_eval.py` and `data/eval/results.json`: exact match; notes match lines 104-107 |
| 18 sources, 17 with raw file, SHA-256 and fetch time | `rules/sources/manifest.json`: 18 entries with `sha256`, `fetched_at`; one manual |
| Demo labels in steps 1-5 | every button/step label quoted in lines 329-333 exists in `frontend/src` (`Recognition.tsx`, `Dashboard.tsx`, `YearPlanResults.tsx`, `EventPacket.tsx`, `MoneyCheck.tsx` incl. "Unit price ($)" / "Amount ($)", `GapHelper.tsx`) |
| Demo club: 5 events, $1,200 on hand | `data/demo/club.json`: 5 events, `money_on_hand_cents: 120000` |
| $1,170 gap, fixed budget ends "the office decides" | `docs/reviews/known-issues.md`, F3 |
| Gap helper excludes cash sponsors and raffles | `backend/app/services/gap_helper.py:59` `BANNED_RULES` |
| `AI_MODE=live` replays recorded inputs | `backend/app/ai/client.py:128-134` |
| Linked files exist | `.env.example`, `LICENSE` (MIT), `PROJECT_CONTEXT.md`, `PLAN.md`, `rules/README.md`, `data/eval/README.md`, `CLAUDE.md#ports-and-addresses` |
| Live app and repository reachable | `curl -I`: both HTTP 200 |
| CI badge | `.github/workflows/ci.yml` exists; remote is `Advait0801/greenlight` |
| Mermaid | both blocks: `flowchart LR`, quoted labels, `[(...)]` cylinders, `-- "label" -->` edges, one `subgraph ... end`; no reserved node ids. Valid as far as can be checked without a renderer |
| HTML blocks | blank lines around Markdown inside `<div align="center">`; `<details>`/`<summary>` well formed, same pattern as the sample |
| Image alt text | `after-desktop-plan.png`: 2 break a rule, 3 to check, 5 events / 35 dated deadlines, $4,770 still to find, This week of USG deadlines, Problems found early with spring banquet and the 5-event cap: matches. `readme-screens.png`: recognition 2 of 92, culture night packet with timeline and "Sources disagree", money check with 2 lines that break a rule, USG queue and citable findings, in the caption's order: matches. `readme-phone.png`: Home, year plan, recognition, money check: matches |

## Findings

### 1. [high] Two of the three demo images are still untracked by git
README text: lines 56 and 61, `docs/submission/screenshots/readme-screens.png` and `readme-phone.png`.
Evidence: `git status --short` shows `?? docs/submission/screenshots/readme-phone.png` and `?? docs/submission/screenshots/readme-screens.png` (README itself is ` M`). `after-desktop-plan.png` is tracked. Iteration 1 finding 5, unresolved.
Why it matters: committed without them, the Demo section on GitHub shows two broken images; judges see the repository page.
Suggested fix: `git add` both images in the same commit as the README.

### 2. [high] "An obeyed instruction can't change a ... verdict" contradicts the known issues
README text, line 94: "An obeyed instruction can't change a date, sum or verdict, because code makes those; at worst it mislabels what was read, which the officer sees and can correct".
Evidence: `docs/reviews/known-issues.md`, F2: "An AI reading that follows planted text can make one line green. If the model obeyed text inside a quote and labelled a line with a harmless category, that line could pass". A mislabel is how the verdict changes, so "can't change a verdict" is the overclaim the security review flagged, reworded. Iteration 1 finding 1, only partly resolved.
Suggested fix: "An obeyed instruction can't change a date or a sum, because code makes those. It can mislabel what was read, which can turn one line green; the officer sees the reading and can correct it ([known issues](docs/reviews/known-issues.md))."

### 3. [medium] "289 rules, each quoting ... word for word, checked by a script" overstates the check
README text, line 42: "289 rules, each quoting one of **18 USC documents** word for word, checked by a script on every CI run".
Evidence: `python scripts/validate_rules.py`: "Every rule marked 'read' matches its snapshot text exactly", i.e. 284, not 289. The 5 unverified rules are not checked, and one of the 18 sources is a hand transcription (`manifest.json`, `manual: true`). The README's own rule table (lines 117-118) says 284 / 5, so the headline row disagrees with it.
Suggested fix: "289 rules quoting 18 USC documents; the 284 verified ones are checked word for word against saved copies on every run, the other 5 are shown yellow".

### 4. [medium] Demo step 3 still says "every form and deadline, dated"
README text, line 331: "every form and deadline, dated and sourced".
Evidence: line 152 of the same README says academic-week deadlines are "shown yellow" without a date; `known-issues.md` F1 ("One USG web-page deadline is never dated") and F3. Iteration 1 finding 2 fixed lines 37, 39 and 152, but not the walkthrough.
Suggested fix: "every form and deadline, sourced, and dated where a rule gives a countable period".

### 5. [medium] Year plan and event packet treat the same USG deadline differently, and the README only describes one
README text: line 152 ("a deadline the sources don't let code date (USG's academic-week deadlines) is shown yellow"); the Year plan feature list (lines 136-141) says nothing about USG dates; the hero screenshot shows "Wed, Nov 18, 2026 · Apply to USG ... unconfirmed date: check with usgfunds@usc.edu".
Evidence: `known-issues.md` F3: "The year plan dates the USG application deadline (... yellow, from the unconfirmed table); the event packet and money check for the same event give no date."
Why it matters: a judge who reads line 152 and then sees dated USG deadlines in the first image sees a contradiction.
Suggested fix: add to the Year plan list: "USG application dates taken from an unconfirmed copy of USG's deadline table, shown yellow with whom to ask".

### 6. [medium] Office acronyms used before they are explained, and USG's real name never given
README text: "USG" appears at lines 37, 40, 50 and 54 before line 70 explains it, and line 70 calls it "student government (USG)". "EngageSC" (lines 127, 419) is never explained. "CI" in the user-facing At a glance row (line 42).
Evidence: CLAUDE.md Conventions: "No office acronym without its full name." `PROJECT_CONTEXT.md:19`: "USC Student Government (USG for undergraduates, GSG for graduates)".
Suggested fix: expand at the first use in At a glance: "Undergraduate Student Government (USG)"; "EngageSC, USC's club portal"; in At a glance say "on every automated check run" or "on every push" instead of "CI".

### 7. [medium] "Nothing leaves the app" is not true in live mode
README text, line 127: "**Nothing leaves the app.** No submission, no email, no connection to EngageSC or any USC system."
Evidence: in `AI_MODE=live` (the deployed setting per line 352) uploaded constitutions, quotes and sentences are sent to the Claude API (`backend/app/ai/client.py:265` `_call_live`). `known-issues.md` F2: "AI readings go into the audit log uncensored. Names inside an uploaded invoice or constitution would be stored". Line 128 presents the audit log only as a strength.
Why it matters: a club officer reads "nothing leaves the app" as a privacy promise.
Suggested fix: retitle "Nothing is submitted or sent." and add one line: "In live mode, uploaded text is sent to Claude to be read, and what was read is kept in an audit log."

### 8. [low] Claude badge URL has an unencoded middle dot
README text, line 22: `https://img.shields.io/badge/Claude-Sonnet_5.5_·_Haiku_5.5-D97757`.
Evidence: the sample percent-encodes non-ASCII (`%C3%97` for ×). GitHub usually encodes it, but not guaranteed through camo.
Suggested fix: `Claude-Sonnet_5.5_%C2%B7_Haiku_5.5-D97757`. Note also that the Tests/Rules badges are static and will drift; acceptable for a frozen submission.

### 9. [low] Architecture diagram says "18 source snapshots"
README text, line 195: "289 rules + 18 source snapshots".
Evidence: line 116 and `manifest.json`: 17 snapshots + 1 hand transcription. Iteration 1 finding 6 residual.
Suggested fix: "289 rules + 18 sources (17 snapshots, 1 hand copy)" or just "18 sources".

### 10. [low] "36 review reports" will be wrong once the README reviews are committed
README text, line 129: "**36 review reports** in `docs/reviews/`".
Evidence: `ls docs/reviews` = 39 files: minus `README.md`, `known-issues.md` and `readme-iter-1-verify.md` = 36, which counts `ui-pass.md` (the orchestrator's own list, not a reviewer's report). With this report, `docs/reviews/` holds 38 reports by the same counting.
Suggested fix: "35 reports from reviewer agents on the code" and keep README reviews out of the count, or say "over 35".

### 11. [low] "No figure the model produced is ever shown" is broader than the design
README text, line 90.
Evidence: amounts read from vendor quotes (`quote_reading`) and dates read from event sentences are figures the model produced; they are shown to the officer for confirmation (data flow step 2, line 205).
Suggested fix: "no figure the model calculated is ever shown; figures it read are shown to you to confirm".

### 12. [low] The opening anecdote has no source
README text, line 70: "One club was denied recognition over three missing words in its constitution."
Evidence: sourced in `PROJECT_CONTEXT.md:51` (Daily Trojan, 2024-10-01). Unlinked here, it reads as an assertion in a README whose theme is "measured, not asserted".
Suggested fix: link it: "([Daily Trojan](https://dailytrojan.com/2024/10/01/clubs-persist-despite-setbacks/))".

### 13. [low] Jargon in the results table
README text: line 104 "30/30 conflict lists match on the engine"; line 106 "1 found with a different red state than the key".
Evidence: `known-issues.md` F1 explains the latter: one clause "weak" where the key expects "contradicts". A club officer will not follow "on the engine" or "red state".
Suggested fix: "30/30 'sources disagree' lists match when checked from the test set's details"; "1 clause marked 'wording changed' where the answer key says 'conflicts with a rule' (both are red)".

### 14. [low] "Try the demo" is far down the page
README text: section at line 325, after Getting Started.
Evidence: the sample keeps its walk-through ("How It Works") after setup too, but Greenlight's top call to action (line 25) sends judges to the live app, which is where the walkthrough is needed. A judge scrolling from the images reaches architecture, tech stack and setup first.
Suggested fix: move "Try the demo" directly after the Demo images, or add "then follow [Try the demo](#-try-the-demo-3-minutes)" to line 25 (check the anchor GitHub generates for the emoji heading).

### 15. [low] Setup chains commands while the convention is one command per block
README text: line 259 `cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`; line 269 `cd frontend && npm install && npm run dev`.
Evidence: the task's stated repo convention; the rest of the section uses one command per block.
Suggested fix: acceptable as is if kept deliberate; otherwise split the venv creation, activation and install into separate blocks.

### 16. [low] USG screen image shows three identical applications
Evidence: `readme-screens.png` bottom right: three "Culture Night · Lantern Cultural Society · $7,070.00" rows, "Fund: not chosen". Looks like leftover test data.
Suggested fix: re-capture after clearing the queue to one or two distinct applications. Cosmetic.

### 17. [low] Missing pieces the sample has; boilerplate footer
Evidence: the sample ends with Acknowledgments; Greenlight has none, though it rests on public USC documents, the Daily Trojan story and the hackathon hosts. Footer "Built in 24 hours" (line 429) vs "about 24 hours" (line 362). "⭐ Star this repo if you find it helpful!" is copied from the sample and reads oddly on a hackathon entry.
Suggested fix: add a short Acknowledgments (USC Campus Activities, USG Funding, Trojan Event Services public pages; HackSC and the USC AI Committee); make the footer say "about 24 hours"; drop or keep the star line by choice.

### 18. [low] Phase 0 ran four iterations
README text, line 375: "Phase 0 used extra parallel auditors, one per rule file".
Evidence: `docs/reviews/phase-0-iter-4-*.md` (a fourth break and audit round).
Suggested fix: "Phase 0 ran four iterations, with one auditor per rule file in the last two".

### 19. [low] CONTRIBUTING.md is staged for deletion while docs still say it was updated
Evidence: `git status`: `D  CONTRIBUTING.md`; `docs/PROGRESS.md:479,483,485` say CONTRIBUTING.md was updated. The README does not link it, so nothing breaks there.
Suggested fix: confirm the deletion is intended; if so, leave PROGRESS history as is or note the removal.

## Iteration 1 findings

| # | Finding | Status |
|---|---|---|
| 1 | Instructions in files "never followed" | Partly resolved: wording changed, but line 94 still says an obeyed instruction can't change a verdict (finding 2 here) |
| 2 | "Every deadline dated" | Partly resolved: lines 37, 39, 152 fixed; demo step 3 (line 331) still says "dated" (finding 4) |
| 3 | 38 review reports | Resolved (36), but see finding 10 |
| 4 | Start page shows rule status | Resolved (line 272, System status link) |
| 5 | Images untracked | Not resolved (finding 1) |
| 6 | Not every source is a snapshot | Resolved at line 116; residual at line 195 (finding 9) |
| 7 | Works without the AI service | Resolved (line 126) |
| 8 | "A wrong green can't be built" | Resolved: heading "A green has to be earned", At a glance scoped to the test sets |
| 9 | Missing features | Resolved (paste a list, image upload, club status/withdraw, failure chart, fund reading, per-role handover) |
| 10 | Eval notes omitted | Resolved (lines 104, 106), wording could be plainer (finding 13) |
| 11 | `pytest` vs adversarial | Resolved (line 291) |
| 12 | `app/rules/` | Resolved (line 386) |
| 13 | `seed_demo.py` needed | Resolved (line 274) |
| 14 | Phase 0 reviewers | Mostly resolved; nuance in finding 18 |
| 15 | Open findings location | Resolved (line 375) |
| 16 | Regression tests for UI pass | Resolved ("backend blocker and high") |
| 17 | Draft vs send gating | Resolved (line 161) |

## Style against the sample

Structure follows the sample closely: title, centered tagline pair, CI/metric badges then stack badges, At a glance (6 rows), Demo with captions and a `<details>` phone view, Overview, Measured, Built to be trusted, Features, Architecture with data flow, Tech stack tables, Getting started, Layout, Docs. Tone is plainer than the sample, which suits club officers. Length (434 lines) is reasonable. The principle "AI reads, code checks, a human approves" appears three times (line 7, heading at line 78, quote at line 184); acceptable as a theme, not clumsy. Gaps: Acknowledgments (finding 17) and the demo walkthrough's position (finding 14).

## Counts

| Severity | Count |
|---|---|
| Blocker | 0 |
| High | 2 |
| Medium | 5 |
| Low | 12 |
