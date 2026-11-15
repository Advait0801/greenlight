# Phase 6, iteration 1 — verify
Summary: 2/3 exit criteria passed. Blockers: 0. High: 1. (Build-list checks: 4/4 checked items present; accessibility pass not checked.)

Live link: https://greenlight--manasman1.replit.app (checked 2026-11-15, about 16:30 UTC). The live bundle is `assets/index-DSm4cI-M.js`, the same hash as a fresh local `npm run build` of `main` at `ad0baf0`, so the live site runs the current frontend.

## Local runs

| Command | Result |
|---|---|
| `cd backend && source .venv/bin/activate && pytest -q` | `817 passed, 13 warnings in 23.55s` |
| `python scripts/validate_rules.py` | `OK` (5 unverified rules listed, 15 more shown yellow because they depend on them; calendar verified: read) |
| `python scripts/run_eval.py` | events 30 cases 456 caught / 0 missed / 0 wrongly flagged; budgets 20 / 30 / 0 / 0; constitutions 10 / 21 / 0 / 0; year_plans 2 / 233 / 0 / 0 |
| `cd frontend && npm run build` | built in 553ms, `dist/assets/index-DSm4cI-M.js 382.69 kB`, exit 0 |

## Exit criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | The full demo journey of PROJECT_CONTEXT section 11 runs on the live link in under three minutes, three times in a row | **FAIL** | Every step up to and including the gap email and the accuracy table ran three times in a row with HTTP 200, in 25.26 s, 5.95 s and 4.96 s of API time (script below). The 2:25 step (USG screen: pre-checked queue, drafted denial reason, "why applications fail" chart) cannot run on the live link: `GET /api/usg/queue` and `GET /api/usg/stats` answer `503 {"detail":{"message":"The USG screen is not set up on this server (USG_REVIEWER_KEY)."}}` in all three runs, also with an `X-Reviewer-Key` header present. See finding H1. All nine page addresses return the app (below). |
| 2 | A fresh visitor can use it with no setup | PASS | No account, key or file needed: `/api/constitution/demo` supplies a sample constitution, `/api/plans/demo` the demo club, the money check's demo budget is in the page, the gap helper's demo example is in the page. All requests in the script carry no cookies or credentials and return 200. The USG reviewer screen is passcode-protected by design; a visitor who opens `/usg` and enters anything gets "The USG screen is not set up on this server (USG_REVIEWER_KEY)." The club side of `/usg` (status by reference and token) works for a visitor: `POST /api/usg/sent/G-F7FC174C2F` with the token returned by `/api/usg/send` → 200 `status: "sent"`. |
| 3 | No secret in the repository or its history | PASS | Branches scanned: `main`, `phase-2/event-packet`, `origin/main`, `origin/phase-2/event-packet` (188 commits, `git log --all`). `git log --all -p` grepped for `sk-ant-…`, `sk-…`, `ghp_`, `github_pat_`, `AKIA…`, `xox?-`, `AIza…`, `BEGIN … PRIVATE KEY`, and `postgres://user:pass@` / `mysql://user:pass@`: only hit is the test fixture `postgres://u:p@h:5432/db` in a parametrized test. Every file path ever committed (all commits' trees): the only `.env*` file is `.env.example`, whose every historical value is blank or non-secret (`ANTHROPIC_API_KEY=`, `USG_REVIEWER_KEY=`, `DATABASE_URL=sqlite:///./greenlight.db`, model names, ports). No `.db`, `.sqlite`, `.pem`, `.key` file ever committed. Assignments of `*API_KEY/PASSWORD/PASSCODE/TOKEN/SECRET` to 12+ character literals: none outside tests (`"wrong-passcode-123"` in a test, `anthropic_api_key="k"` in an adversarial test). `.gitignore` ignores `.env` and `.env.*` except `.env.example`; `git check-ignore` confirms `.env` and `backend/.env` are ignored. `.replit` holds no secrets. No stashes. |

### Build-list checks (Phase 6 "Build")
| Item | Result | Evidence |
|---|---|---|
| Accuracy page: caught, missed, wrongly flagged | PRESENT | Live `GET /api/accuracy` → 200 with four sets: events 456/0/0, budgets 30/0/0, constitutions 21/0/0, year_plans 233/0/0; same figures as a local `run_eval.py`. Includes `method` and `limits` ("small, made-up test sets … a pre-check, not a decision"). |
| "Pre-check, not a decision" on every report | PRESENT | Every report response carries `notice: "Greenlight is a pre-check, not a decision. The office that owns each rule makes the decision."`: `/health`, `/constitution/check`, `/plans/plan`, `/events/packet`, `/money/check`, `/gap/options`. `PrecheckNotice` is imported and rendered in Accuracy, EventPacket, GapHelper, Handover, Home (status), MoneyCheck, Recognition, RecognitionReport, UsgScreen, YearPlan. The gap email carries its own notice ("Greenlight does not send anything"). |
| README complete | PRESENT | Live link (line 9), problem, features, how it works, quick start, "Try the demo (3 minutes)", accuracy, deploying (secrets table), layout, documents, limits, licence (MIT, `LICENSE` exists). Gap: step 6 cannot be done by a reader (see H1). |
| Recorded AI fallback | PRESENT | `backend/app/ai/client.py` `extract()`: in `live` mode, a saved recording for the exact request is replayed instead of calling the API; 101 recordings are tracked under `data/ai_recordings/`. `application_draft.py` catches `AIError` and fills the draft from the officer's own words. Live `/api/health` reports `ai_mode: "live"`. The demo constitution check (0.25–0.45 s) and gap email (0.2 s) answered at replay speed. |
| Accessibility pass | NOT CHECKED | No browser available; out of scope for this verify run. |

### Demo journey on the live link (three runs)

Script: `/private/tmp/claude-501/-Users-dalvi-Downloads-Projects-greenlight/9c2d8e95-00a3-443d-aa21-1c80fb387087/scratchpad/journey.py` (Python stdlib only). It sends the same requests the pages send, with the same bodies (built from `Recognition.tsx`, `YearPlan.tsx`, `EventPacket.tsx`, `MoneyCheck.tsx` `DEMO_EVENT`/`DEMO_LINES`/`loadDemo`, `GapHelper.tsx` `DEMO_EMAIL`, `UsgScreen.tsx`, `Accuracy.tsx`). Run 1 also sent the demo budget to the USG screen (README step 4); I withdrew that entry afterwards (`POST /api/usg/sent/G-F7FC174C2F/withdraw` → `{"status":"withdrawn"}`).

| Step (section 11) | Requests | Run 1 | Run 2 | Run 3 | What came back (same in all runs) |
|---|---|---|---|---|---|
| 0:00 constitution | `GET /constitution/demo`, `POST /constitution/check` (multipart: `text` + sample answers) | 200 / 200 | 200 / 200 | 200 / 200 | `overall: red`, "2 of 92 clauses need fixing": *Voting membership criteria* = `contradicts` (red), *Officer transition procedure* = `missing` (red); 3 `needs_look` yellow. |
| 0:25 year plan | `GET /events/vocabulary`, `GET /plans/demo`, `POST /plans/plan` | 200×3 | 200×3 | 200×3 | 5 events, $1,200 on hand. Problems: red yearly cap ($11,250 requested, over $8,000 by $3,250); red ticketed Spring banquet; yellow "5 events in Spring 2027 ask USG for money; USG's web page says up to 4"; yellow retreat travel deadline falls before the semester (Dec 25, 2026 by count / Nov 18, 2026 by table). Culture night shortfall $1,170.00. |
| 0:55 event packet | `POST /events/packet` (culture night facts from the plan) | 200 | 200 | 200 | 28 obligations, 7-date timeline (2027-02-26 … 2027-04-14), 5 `source_conflicts` ("Sources disagree…"), 4 `office_decides` incl. "Contact the Department of Public Safety 2 weeks before" (DPS, 2027-03-26); every obligation has a citation. |
| 1:30 money check | `GET /money/vocabulary`, `POST /money/check` (demo budget), `POST /money/check` (fixed by hand), `POST /money/draft` | 200×4 | 200×4 | 200×4 | Demo budget: `verdict red`; red `usg-food-cap` "$38.00 per person; the cap is $35.00 (over by $450.00 for 150 people)", red `usg-ineligible-performers` (DJ $800), red `usg-ineligible-ticketed-events`. After editing (catering $35, DJ removed, not ticketed): `verdict office_decides`, no red; draft 200 with every figure from the check (total $5,820.00). Draft took 23.29 s in run 1 (live call, new purpose text), 3.76 s and 3.75 s after. |
| (README 4) send to USG | `POST /usg/send` | 200 | – | – | reference `G-F7FC174C2F`, token, "This is not an EngageSC submission". |
| 2:05 gap helper | `POST /gap/options`, `POST /gap/email` | 200 / 200 | 200 / 200 | 200 / 200 | Shortfall $1,170.00; allowed: in-kind sponsorship, co-host, donations, free drawing, voluntary dues; office decides: fundraiser; check first: ticket sales, other USC funds. Not allowed: cash from corporate sponsors, raffle requiring purchase, and 4 more, each with `why` and citation. Email draft: subject "In-kind sponsorship for Culture night (Lantern Cultural Society)", `approved: false`, "Greenlight does not send anything". |
| 2:25 USG screen | `GET /usg/queue`, `GET /usg/stats` | **503 / 503** | **503 / 503** | **503 / 503** | "The USG screen is not set up on this server (USG_REVIEWER_KEY)." |
| 2:45 trust | `GET /accuracy` | 200 | 200 | 200 | figures above. |
| | **Total API time** | **25.26 s** | **5.95 s** | **4.96 s** | |

Page addresses (`curl -s -w "%{http_code} %{content_type}"`): `/`, `/recognition`, `/events/packet`, `/money/check`, `/money/gap`, `/handover`, `/usg`, `/accuracy`, `/status` each → `200 text/html; charset=utf-8`, 694 bytes, `<title>Greenlight</title>`, `<div id="root">`, `assets/index-DSm4cI-M.js`. The bundle → 200 (382,692 bytes), the CSS → 200. Handover in passing: `POST /api/handover` with the demo plan → 200 in 0.07 s.

## Findings

### [high] H1. The USG screen step of the demo cannot run on the live link
Expected: section 11 at 2:25 shows the USG screen with the pre-checked queue, a drafted denial reason for a person to approve, and the "why applications fail" chart, on the live link (exit criterion 1). README step 6 tells a reader to do this.
Actual: the live server has no `USG_REVIEWER_KEY`; `/api/usg/queue` and `/api/usg/stats` answer 503 "The USG screen is not set up on this server (USG_REVIEWER_KEY)." The `/usg` page shows that message after any passcode is entered. The queue, the denial draft and the chart cannot be shown. The club-side status lookup on the same page does work. Even after the key is set, a judge following README step 6 cannot open the screen without the passcode ("kept by the team, not public"), so the README walk-through cannot be completed by a visitor on their own; the team must drive that step or provide the passcode to judges another way.
Reproduce:
```
curl -s https://greenlight--manasman1.replit.app/api/usg/queue
curl -s https://greenlight--manasman1.replit.app/api/usg/stats
# both: {"detail":{"message":"The USG screen is not set up on this server (USG_REVIEWER_KEY)."}}  HTTP 503
```

### [medium] M1. "Accept the fixes; it turns green" has no counterpart in the app
Expected: section 11 at 1:30: "Accept the fixes; it turns green and drafts the application."
Actual: the money check shows a "Fix:" sentence per finding but has no control that applies a fix (no accept/apply button in `frontend/src/pages/MoneyCheck.tsx`); the officer must edit the lines by hand (price 38.00 → 35.00, delete the DJ line, set "ticketed" to No). After those edits the overall verdict is `office_decides` ("The office decides"), not green, because `usg-food-case-by-case` and `usg-over-4000-case-by-case` are office-decides rules. That outcome is correct under CLAUDE.md ("office decides, never a pass"), but the demo script promises green and one-step acceptance; whoever presents must say what happens instead. README step 4 does not cover this part (it stops at the red findings and sending to USG).
Reproduce: run `journey.py` (path above) and read `money_fixed.verdict` in the output JSON, or on `/money/check`: *Load the demo club's culture night budget* → *Check the budget*; look for any control that applies a fix.

### [low] L1. Demo story figures differ from what the app shows
Expected (section 11): retreat travel deadline "lands in January"; culture night "Still $900 short"; "Upload the quotes".
Actual: the plan says the travel deadline falls on December 25, 2026 (winter recess) by count, or November 18, 2026 by USG's table, "before the semester of the event"; culture night's shortfall is $1,170.00; the demo budget is loaded from typed lines (`DEMO_LINES`), not from uploaded quotes. README already uses the app's figures ($1,170, "falls before the semester"), so this is a script/spec mismatch, not a calculation error. The presenter's script should match the screen.
Reproduce: `curl -s https://greenlight--manasman1.replit.app/api/plans/demo | curl -s -X POST -H 'Content-Type: application/json' -d @- https://greenlight--manasman1.replit.app/api/plans/plan` and read `problems` and `budget.rows`.

### [low] L2. Adoption material for the 2:45 step does not exist yet
Expected: section 11 at 2:45 shows "adoption (owner, cost, pilot)"; `docs/submission/README.md` line 15 says the adoption slide must state owner, data needed, monthly cost, pilot scope, who verifies the event rules, and the AI tool review.
Actual: `docs/submission/` contains only `README.md`; no slide or page in the app shows owner, cost or pilot. (Not in the Phase 6 build list; may belong to submission material.)
Reproduce: `ls docs/submission; grep -rni pilot frontend/src`.

### [low] L3. First application draft on the live link takes about 23 seconds
Expected: demo steps answer quickly.
Actual: `POST /api/money/draft` with a purpose text not in the recordings took 23.29 s in run 1 (live Claude call); identical later calls took about 3.7 s. Within the three-minute budget, but a presenter typing a new purpose should expect a pause. With the UI's default empty purpose and the hand-edited budget, whether a recording exists depends on the exact lines typed.
Reproduce: run `journey.py`; see the `POST /money/draft` timing in run 1.

Not checked: the accessibility pass (keyboard, contrast, labels, phone layout) — no browser. Rendering of the pages in a browser — checked only that each address serves the current bundle and that each page's API calls succeed.
