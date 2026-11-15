"""The accuracy page's figures: caught, missed and wrongly flagged on each test set (data/eval/).

The figures are measured by `scripts/run_eval.py --json` and saved in data/eval/results.json; a test checks that
the saved file matches a fresh run, so the page never shows a figure the code did not measure.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.config import REPO_ROOT
from app.jsonutil import loads_strict

router = APIRouter(tags=["accuracy"])
RESULTS = REPO_ROOT / "data" / "eval" / "results.json"

ABOUT = {
    "events": "30 one-sentence event descriptions; each expected form and deadline is one item to find.",
    "budgets": "20 budgets with 30 planted funding-rule violations.",
    "constitutions": "10 constitutions with 21 planted faults (missing, changed or contradicting clauses) and one empty file.",
    "year_plans": "2 year plans; calendar dates, budget totals and problems are items to find.",
}


@router.get("/accuracy")
def accuracy() -> dict[str, Any]:
    try:
        rows = loads_strict(RESULTS.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - a missing or broken file is the same answer to the browser
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={"message": "The accuracy figures are not available."}) from exc
    sets = [{**row, "about": ABOUT.get(row["set"], "")} for row in rows]
    return {
        "sets": sets,
        "method": ("Each test set was written by hand from the official documents, with the right answer for every case, "
                   "before Greenlight's checks existed. The AI's readings of the test files are recorded once and "
                   "replayed, so these figures can be re-measured exactly with `python scripts/run_eval.py`."),
        "limits": ("These are small, made-up test sets. A perfect score here does not mean Greenlight is always right. "
                   "Greenlight is a pre-check, not a decision."),
    }
