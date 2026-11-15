# Backend

FastAPI service. Python 3.12.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port ${BACKEND_PORT:-8000}
pytest
```

```
app/
  main.py            app factory; includes every router in api/ automatically
  config.py          settings from environment variables and the repository's .env
  db.py              engine, sessions, init_db() (no migrations: delete greenlight.db after a schema change)
  api/               one module per feature, each defining `router`
    health.py        GET /health
    rules.py         GET /rules, GET /rules/{id}
    deps.py          require_ruleset / require_calendar (503 with reasons if they did not load)
  ai/                the only code that talks to Claude
    client.py        ClaudeClient.extract(): structured output, live / recorded / record modes
    untrusted.py     UntrustedDocument, the data-not-instructions wrapper and system prompt
    schemas.py       ExtractedField (value, confidence, evidence) and is_confident()
    audit.py         log_ai_output() -> audit_log table
  rules/             pure Python, never imports app.ai
    schema.py        the rule object (strict Pydantic model)
    loader.py        load_rules(): all-or-nothing load, every problem listed
    snapshots.py     source manifest and exact-text matching against snapshots
    calendar.py      the academic calendar (rules/calendar.json)
    citations.py     citation_for(): rule text + source link for any finding
  schemas/common.py  Verdict, Citation, Finding, PRECHECK_NOTICE (shared by all features)
  models/            database tables from PROJECT_CONTEXT section 5
  services/          feature logic; rule_versions.py stores each rule version
  eval_sets.py       loads and validates data/eval/ test sets
tests/
  unit/              rules, calendar, AI client, test sets, architecture
  integration/       routes, database, scripts
  adversarial/       written by breaker agents; do not delete
```

Phases add, in `services/`: `intake.py` and `drafting.py` (may use `app.ai`), and `rule_engine.py`, `deadlines.py`, `year_planner.py` (must never import `app.ai`; `tests/unit/test_architecture.py` enforces it).

## Using the AI client

```python
from app.ai import ClaudeClient, UntrustedDocument, AIError

result = ClaudeClient().extract(
    task="event-attributes",                 # names the recording folder
    instructions="...",                      # written by our code
    request="...",                           # written by our code
    documents=[UntrustedDocument(name="sentence.txt", text=user_text)],  # anything from a user
    output_type=EventAttributes,             # a Pydantic model
)
```

Any `AIError` (no key, outage, refusal, invalid output, missing recording) must become a yellow "could not read this" result, never green. With `AI_MODE=recorded` (the default, and always in tests) a request with no saved response raises `RecordingNotFound`; record one by running the request once with `AI_MODE=record` and an API key. Recordings hold document fingerprints, not document text.
