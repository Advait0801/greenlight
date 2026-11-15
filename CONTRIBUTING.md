# Contributing

## Before you start

Read [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md), [PLAN.md](PLAN.md) and [docs/PROGRESS.md](docs/PROGRESS.md).

## Working rules

- Follow the phases in PLAN.md in order. A phase is done when its gate passes, not when the code is written.
- The model reads and drafts. Code does every date, sum and verdict. See the principle in [CLAUDE.md](CLAUDE.md).
- A rule goes in `rules/*.json` with its source text, link, date and verification mark. A person reviews every rule before it is used.
- Every bug fix comes with a test that failed before the fix.
- Never commit secrets. Keys go in `.env` or Replit secrets.

## Branches and commits

- `main` always runs and passes the tests.
- Short-lived branches named `phase-2/event-packet` or `fix/food-cap-rounding`.
- Commit messages say what changed and why: `phase 3 iter 2: fix per-person cap when headcount is zero`.
- During Phase 7: one finding, one small change, one test, one commit.

## Before you open a pull request

```bash
cd backend && pytest
```

```bash
cd frontend && npm run build
```

Then fill in the pull request template.

## Changing a rule

1. Update the snapshot in `rules/sources/` and its fetch date.
2. Change the rule file, including `source_text` and `effective_date`.
3. Run the tests and `python scripts/run_eval.py`.
4. Ask a second person to compare the rule with the source.
