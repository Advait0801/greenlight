# Greenlight

**Plan your club's whole year, and know every form, deadline and rule before USC tells you no.**

Greenlight is a planning and pre-check tool for student organization officers at the University of Southern California. An officer enters the year's events and money once. Greenlight returns a year plan and, for each event, the forms, deadlines and funding checks, each linked to the official rule behind it.

Built at the AI@USC hackathon (HackSC × USC AI Committee), November 14–15, 2026.

**Live app:** https://greenlight--manasman1.replit.app — no sign-up and no setup. Start with **Load the demo club** on the year plan. Every result is a pre-check, not a decision.

## The problem

Running a USC club means passing checks owned by different offices: yearly recognition, event approvals and student government funding. Each has its own rules and clocks, no single page puts them on one timeline, and a small mistake can cost a club its funding or its recognition. One club was denied recognition over three missing words in its constitution.

## What it does

| Feature | What the officer gets |
|---|---|
| **Year plan** | A calendar and budget for the whole year, a funding strategy within USG's caps, and the problems to fix early |
| **Recognition check** | The club constitution checked clause by clause against the required template |
| **Event packet** | One sentence about an event becomes every form, approval and deadline, dated and sourced |
| **Money check** | Each budget line marked red, yellow or green against the funding rules, with a concrete fix and a draft application |
| **Funding gap helper** | Ways to cover a shortfall that USC actually allows, and why cash sponsors and raffles are not among them |
| **Handover packet** | What ran, what it cost and what was denied, ready for next year's officers |
| **USG screen** | Applications that arrive already checked, with a drafted reason when one must be denied |

## How it works

**AI reads, code checks, a human approves.**

- The model turns sentences, PDFs and screenshots into structured data, and writes drafts.
- Plain code does every date, sum and verdict, using a rule table that a person has reviewed.
- Every finding links to the rule it comes from. Where official sources disagree, both are shown.
- When the model is unsure, the item is marked for a human look.
- Greenlight is a pre-check. It never submits anything and never makes a decision.

## Quick start

Requires Python 3.12 and Node 20.19 or later. A Claude API key is needed only for live AI reading; without one, the app and the tests run on recorded responses (`AI_MODE=recorded`, the default).

```bash
cp .env.example .env    # then add your API key if you have one, and set AI_MODE=live
```

Backend, in a virtual environment:

```bash
cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

```bash
python -m app
```

Frontend, in a second terminal:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. The start page shows whether the rule table and calendar loaded.

To run a second copy at the same time, set `BACKEND_PORT` and `FRONTEND_PORT` (for example `8001` and `5174`) in `.env` or in both terminals; the backend and the frontend's proxy both follow them. See [CLAUDE.md](CLAUDE.md#ports-and-addresses).

Load the demo club (from the repository root, virtual environment active):

```bash
python scripts/seed_demo.py
```

Run the tests (from `backend/`, virtual environment active), including the adversarial tests the review agents add:

```bash
pytest
```

```bash
pytest tests/adversarial
```

Build the frontend the way CI does (from `frontend/`):

```bash
npm run build
```

Check the rule table against its sources, and the test sets against their schemas (from the repository root, same virtual environment):

```bash
python scripts/validate_rules.py
```

```bash
python scripts/run_eval.py
```

## Try the demo (3 minutes)

Everything below uses made-up data, and its AI readings are recorded, so it works even when the AI service is slow or down.

1. **Recognition** → *No file to hand? Try a sample constitution* → *Check my constitution* (the *Findings* step opens). A GPA limit on members is flagged as breaking the open-membership rule, and the blank officer-transition clause as missing.
2. **Year plan** → *Load the demo club* (also on **Home**, which then shows the club's dashboard). Five spring events and $1,200 on hand become a calendar and a budget, with the problems to fix early (USG's yearly cap, a ticketed event, a travel deadline that falls before the semester). Step through *Overview*, *Calendar*, *Budget and funding* and *Each event*.
3. In *Each event*, pick *Culture night* → **Open event packet** → *Build the packet*: every form and deadline, dated and sourced, a "sources disagree" note and items the office decides.
4. **Money check** → *Load the demo club's culture night budget* → *Check the budget* (the *Findings* step opens): catering over the $35 per person cap, a DJ fee and ticket sales are red. To show the USG screen with something to cite, send this red budget now from the *Draft and send* step with the club name `Lantern Cultural Society`. Then go back to *Event and budget* and fix it by hand (there is no one-click fix): on line 1 set Unit price to 35 and Amount to 5250, remove line 2 (the DJ), set *Sells tickets or charges entry?* to No, and check again. The red items clear, items USG judges case by case stay "the office decides" (Greenlight never shows those as a pass), and the application can be drafted.
5. Back on the year plan's *Each event* step, pick *Culture night* → **Close the $1,170.00 gap** → *Show the options USC allows* → the *Draft an outreach email* tab → *Fill in the demo club's example* → *Draft the email*. Edit, then approve; nothing is sent.
6. **USG screen**: reviewers enter the passcode (kept by the team, not public), open the application from the queue and draft a reason from the ticked findings; a person approves it before the club can read it.
7. **Accuracy**: caught, missed and wrongly flagged on the test sets.

## Accuracy

`python scripts/run_eval.py` measures four hand-written test sets with known answers (data/eval/). The figures on the app's Accuracy page come from `data/eval/results.json`, which a test keeps equal to a fresh run. Refresh it after a change with `python scripts/run_eval.py --json > data/eval/results.json`.

## Deploying

The deployed site is one process: `python -m app --site` (from `backend/`) serves the built frontend and the API under `/api` on one address. `scripts/deploy/build.sh` installs the backend into `.venv-deploy/` and builds the frontend; `scripts/deploy/start.sh` seeds the demo club and starts the site on `$PORT` (default 5000). `.replit` runs these two scripts on Replit.

Settings come from the environment (Replit secrets), never from the repository:

| Name | Purpose |
|---|---|
| `DATABASE_URL` | Postgres URL (Replit sets it for its database). Without it the site falls back to a SQLite file that a redeploy erases. |
| `AI_MODE` | `live` reads new input with Claude and replays recorded answers for the demo's inputs; `recorded` never calls the API. |
| `ANTHROPIC_API_KEY` | Needed only for `live`. |
| `MODEL_EXTRACT`, `MODEL_CLASSIFY` | Model names. |
| `USG_REVIEWER_KEY` | Passcode for the USG screen, at least 12 characters. Unset: the USG screen stays closed. |
| `APP_ENV` | `production` when deployed. |

## Repository layout

```
backend/     FastAPI service: rule engine, deadline calculator, year planner, AI intake and drafting
frontend/    React app
rules/       Rule files and snapshots of the official source documents
data/        Test sets with known answers, and demo seed data
scripts/     Evaluation, seeding and source-fetching scripts
docs/        Progress log, review reports, research notes, submission material
```

## Documents

- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — the full product brief and the rules it encodes
- [PLAN.md](PLAN.md) — build phases, verification iterations and exit criteria
- [CLAUDE.md](CLAUDE.md) — instructions for AI coding agents
- [docs/PROGRESS.md](docs/PROGRESS.md) — current status
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to work in this repository

## Limits

- Greenlight gives information from public USC documents. It is not an official USC service and its results are not decisions.
- Rules change. Each rule shows the date it was last checked.
- It does not connect to EngageSC or any USC system.

## Licence

MIT. See [LICENSE](LICENSE).
