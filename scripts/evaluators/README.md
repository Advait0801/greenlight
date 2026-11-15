# Evaluators

One module per test set, added by the phase that builds the feature. `scripts/run_eval.py` finds them by name; it never needs editing.

| Module | Test set | Added in |
|---|---|---|
| `constitutions.py` | `data/eval/constitutions/` | Phase 1 |
| `events.py` | `data/eval/events/` | Phase 2 |
| `budgets.py` | `data/eval/budgets/` | Phase 3 |
| `year_plans.py` | `data/eval/year_plans/` | Phase 4 |

Each module defines:

```python
def evaluate(data: dict, ruleset) -> dict:
    # data: the validated test set; ruleset: app.rules.RuleSet
    return {"caught": int, "missed": int, "wrongly_flagged": int, "details": [...], "notes": "..."}
```

- **caught**: seeded problems (or expected obligations) the feature found.
- **missed**: seeded problems it did not find.
- **wrongly flagged**: things it flagged that the test set says are fine. A wrong green (a rule broken but shown green) always counts as missed.

Evaluators call the real feature code with `AI_MODE=recorded`, so they run offline and give the same numbers every time.
