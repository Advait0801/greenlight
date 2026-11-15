# Backend

FastAPI service. Created in Phase 0.

```
app/
  main.py            app and routes
  api/               one module per feature: plans, recognition, events, money, reviewer, rules
  services/
    intake.py        Claude calls that turn text and files into typed JSON
    drafting.py      Claude calls that write drafts
    rule_engine.py   pure Python: data + rules -> findings with citations
    deadlines.py     pure Python: event date + calendar + rules -> dated obligations
    year_planner.py  pure Python: events + money -> calendar, budget, funding strategy
  models/            database tables
  schemas/           Pydantic types
tests/
  unit/              rule engine, deadlines, planner
  integration/       routes, with recorded AI responses
  adversarial/       written by breaker agents; do not delete
requirements.txt
```

`rule_engine.py`, `deadlines.py` and `year_planner.py` must never import the AI client.
