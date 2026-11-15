# Greenlight

**Plan your club's whole year, and know every form, deadline and rule before USC tells you no.**

Greenlight is a planning and pre-check tool for student organization officers at the University of Southern California. An officer enters the year's events and money once. Greenlight returns a year plan and, for each event, the forms, deadlines and funding checks, each linked to the official rule behind it.

Built at the AI@USC hackathon (HackSC × USC AI Committee), November 14–15, 2026.

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
uvicorn app.main:app --reload --port ${BACKEND_PORT:-8000}
```

Frontend, in a second terminal:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. The start page shows whether the rule table and calendar loaded.

To run a second copy at the same time, set `BACKEND_PORT` and `FRONTEND_PORT` (for example `8001` and `5174`) in both terminals; the frontend's proxy follows `BACKEND_PORT`. See [CLAUDE.md](CLAUDE.md#ports-and-addresses).

Run the tests (from `backend/`, virtual environment active):

```bash
pytest
```

Check the rule table against its sources, and the test sets against their schemas (from the repository root, same virtual environment):

```bash
python scripts/validate_rules.py
```

```bash
python scripts/run_eval.py
```

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
