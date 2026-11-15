# Data

```
eval/
  events/          30 event sentences, each with the obligations and dates it should produce
  budgets/         20 funding budgets with known violations
  constitutions/   10 constitutions with known missing or contradictory clauses
  year_plans/      2 full year plans with expected calendar, budget and flagged problems
demo/              the fictional demo club: constitution, events, quotes
```

All of this is made up by the team. Real applications sit behind USC login and are not used.

Each test case states its expected result, so the same files serve as the accuracy test set (`python scripts/run_eval.py`).

Do not put real names, student IDs or real club documents here.
