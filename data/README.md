# Data

```
eval/
  schemas/         JSON Schema for each test set
  events/          30 event sentences, each with the attributes, obligations and dates it should produce
  budgets/         20 funding budgets with 30 planted violations
  constitutions/   10 constitutions (texts/) with 20 planted missing, weak or contradictory clauses
  year_plans/      2 full year plans with expected calendar, budget totals and flagged problems
demo/              the fictional demo club (club.json), loaded by scripts/seed_demo.py
ai_recordings/     saved AI responses for AI_MODE=recorded (created when something is recorded)
```

All of this is made up by the team. Real applications sit behind USC login and are not used. Do not put real names, student IDs or real club documents here.

Each test case states its expected result, so the same files serve as the accuracy test set (`python scripts/run_eval.py`). See [eval/README.md](eval/README.md) for how the expected results were derived and how they are scored.
