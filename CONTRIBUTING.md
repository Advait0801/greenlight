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

- `main` always runs and passes the tests. One person works on the repository, so phases and fixes are committed directly on `main`: no phase branches and no pull requests.
- Before starting work: `git pull --rebase origin main`.
- At the end of a phase: run the full suite, update `docs/PROGRESS.md`, `git pull --rebase origin main`, rerun the suite, `git push origin main`, and confirm CI passes on `main`. Never force-push.
- Small commits: one per logical piece, and one per finding fixed (code plus its regression test).
- Commit subjects are imperative and say what changed: `Fix per-person cap when headcount is zero`. The body can say why. Do not start a subject with `phase N` or `iter N`; phases and iterations are tracked in `docs/PROGRESS.md`.
- During Phase 7: one finding, one small change, one test, one commit.

## Before you push

```bash
cd backend && pytest
```

```bash
cd frontend && npm run build
```

Then push to `main` and check that CI passes.

## Changing a rule

1. Update the snapshot in `rules/sources/` and its fetch date.
2. Change the rule file, including `source_text` and `effective_date`.
3. Run the tests and `python scripts/run_eval.py`.
4. Ask a second person to compare the rule with the source.
