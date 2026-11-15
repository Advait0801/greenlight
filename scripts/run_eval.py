"""Run the test sets in data/eval/ and print caught, missed and wrongly flagged.

Usage (from the repository root, backend dependencies installed):

    python scripts/run_eval.py               # every set
    python scripts/run_eval.py events        # one or more named sets
    python scripts/run_eval.py --json        # machine-readable results

Every set is first loaded and validated against its schema. Then, for each set, the evaluator in
scripts/evaluators/<set>.py is run if it exists. Evaluators are added by the phase that builds
the feature (constitutions: Phase 1, events: Phase 2, budgets: Phase 3, year_plans: Phase 4), so
adding one never requires editing this file.

An evaluator module defines `evaluate(data: dict, ruleset) -> dict` returning at least
{"caught": int, "missed": int, "wrongly_flagged": int} and optionally "details" and "notes".
AI calls inside an evaluator must respect AI_MODE (recorded by default), never the live API unasked.

Exit code: 0 when every set is valid (and every evaluator that exists ran), 1 otherwise.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from typing import Any

from _common import use_backend

use_backend()
os.environ.setdefault("AI_MODE", "recorded")

from app.config import get_settings  # noqa: E402
from app.eval_sets import SETS, EvalSetError, load_set  # noqa: E402
from app.rules import RuleLoadError, load_rules  # noqa: E402

PHASE = {"constitutions": 1, "events": 2, "budgets": 3, "year_plans": 4}


def run(names: list[str]) -> tuple[list[dict[str, Any]], bool]:
    ok = True
    try:
        ruleset = load_rules(get_settings().rules_dir)
    except RuleLoadError as exc:
        print(exc, file=sys.stderr)
        return [], False

    results = []
    for name in names:
        row: dict[str, Any] = {"set": name}
        try:
            data = load_set(name, ruleset=ruleset)
        except EvalSetError as exc:
            print(exc, file=sys.stderr)
            row.update(status="invalid", cases=0)
            results.append(row)
            ok = False
            continue
        row["cases"] = len(data["cases"])
        try:
            module = importlib.import_module(f"evaluators.{name}")
        except ModuleNotFoundError as exc:
            if exc.name != f"evaluators.{name}":
                raise
            row["status"] = f"valid; feature not built yet (Phase {PHASE[name]})"
            results.append(row)
            continue
        outcome = module.evaluate(data, ruleset)
        row.update(status="evaluated", **{k: outcome[k] for k in ("caught", "missed", "wrongly_flagged")})
        if "notes" in outcome:
            row["notes"] = outcome["notes"]
        results.append(row)
    return results, ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the accuracy test sets.")
    parser.add_argument("sets", nargs="*", help=f"sets to run (default: all of {', '.join(SETS)})")
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    args = parser.parse_args(argv)

    unknown = [name for name in args.sets if name not in SETS]
    if unknown:
        print(f"Unknown set(s): {', '.join(unknown)}. Known: {', '.join(SETS)}", file=sys.stderr)
        return 2

    results, ok = run(args.sets or list(SETS))
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"{'set':14} {'cases':>5}  {'caught':>6} {'missed':>6} {'wrongly flagged':>15}  status")
        for row in results:
            numbers = [str(row.get(key, "-")) for key in ("caught", "missed", "wrongly_flagged")]
            print(f"{row['set']:14} {row.get('cases', 0):>5}  {numbers[0]:>6} {numbers[1]:>6} {numbers[2]:>15}  {row['status']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
