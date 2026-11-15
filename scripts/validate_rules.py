"""Check every rule file has the required fields and matches its snapshot.

Usage (from the repository root, backend dependencies installed):

    python scripts/validate_rules.py
    python scripts/validate_rules.py --rules-dir path/to/rules

Exit code 0 when the rule table and calendar load cleanly, 1 otherwise. Uses the same loader as
the app, so a table that passes here is exactly the table the app will load.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from _common import RULES_DIR, use_backend

use_backend()

from app.rules import CalendarLoadError, RuleLoadError, load_calendar, load_rules  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate rules/*.json against the schema and the source snapshots.")
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)
    parser.add_argument("--quiet", action="store_true", help="print only problems and the final line")
    args = parser.parse_args(argv)

    failed = False
    try:
        ruleset = load_rules(args.rules_dir)
    except RuleLoadError as exc:
        print(exc, file=sys.stderr)
        ruleset = None
        failed = True

    try:
        calendar = load_calendar(args.rules_dir)
    except CalendarLoadError as exc:
        print(exc, file=sys.stderr)
        calendar = None
        failed = True

    if ruleset is not None and calendar is not None:
        pointer = ruleset.rules.get(calendar.id)
        if pointer is None:
            print(f"No rule '{calendar.id}' points at the academic calendar.", file=sys.stderr)
            failed = True
        elif pointer.verified != calendar.verified:
            print(
                f"Rule '{calendar.id}' is marked '{pointer.verified}' but rules/calendar.json is marked "
                f"'{calendar.verified}'. They must agree.",
                file=sys.stderr,
            )
            failed = True

    if ruleset is not None and calendar is not None:
        business = ruleset.rules.get("usc-business-days-definition")
        if business is None:
            print("No rule 'usc-business-days-definition' carries the business-day assumption.", file=sys.stderr)
            failed = True
        elif business.verified != calendar.business_days.verified:
            print(
                f"Rule 'usc-business-days-definition' is marked '{business.verified}' but rules/calendar.json "
                f"business_days is marked '{calendar.business_days.verified}'. They must agree.",
                file=sys.stderr,
            )
            failed = True

    if ruleset is not None and not args.quiet:
        print(f"{len(ruleset)} rules loaded.")
        for domain, count in sorted(Counter(rule.domain for rule in ruleset).items()):
            print(f"  {domain:14} {count}")
        marks = Counter(rule.verified for rule in ruleset)
        print("Verification: " + ", ".join(f"{mark} {count}" for mark, count in sorted(marks.items())))
        print("Every rule marked 'read' matches its snapshot text exactly.")
        uncertain = [rule for rule in ruleset if rule.verified != "read"]
        if uncertain:
            print("Not verified (shown yellow until a person confirms them):")
            for rule in uncertain:
                print(f"  - {rule.id}: {rule.verification_note}")
        inherited = [rule.id for rule in ruleset if rule.verified == "read" and not ruleset.is_certain(rule.id)]
        if inherited:
            print(f"{len(inherited)} more rules depend on an unverified rule and are also shown yellow.")
    if calendar is not None and not args.quiet:
        print(f"Academic calendar: {', '.join(term.name for term in calendar.terms)} (verified: {calendar.verified}).")

    print("FAILED" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
