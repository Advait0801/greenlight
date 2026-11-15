# Scripts

Run from the repository root with the backend's virtual environment active (`source backend/.venv/bin/activate`).

| Script | What it does |
|---|---|
| `run_eval.py` | Validates the test sets in `data/eval/` and, for each feature that exists, prints caught, missed and wrongly flagged. `python scripts/run_eval.py events --json` for one set as JSON. |
| `seed_demo.py` | Loads the demo club from `data/demo/club.json` into `DATABASE_URL`. Safe to run again; it replaces the demo club only. |
| `fetch_sources.py` | Saves snapshots of the official documents to `rules/sources/` with the fetch date and SHA-256. Maintenance only; the app never calls USC websites. |
| `validate_rules.py` | Checks every rule file has the required fields and matches its snapshot; checks the calendar. Exit code 1 on any problem. |

`evaluators/` holds one module per test set, added by the phase that builds the feature (see its README).
