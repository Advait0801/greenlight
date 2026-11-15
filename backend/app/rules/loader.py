"""Load and check the rule table in rules/*.json.

Loading is all or nothing. If any rule is malformed, has no source, or (when marked "read")
does not match its snapshot, nothing loads and RuleLoadError lists every problem. A rule
table with one rule silently dropped would hide an obligation, which is worse than refusing
to start the checks.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.jsonutil import StrictJSONError, loads_strict

from app.rules.schema import REQUIRED_FIELDS, Domain, Rule, RuleFile, Severity
from app.rules.snapshots import (
    ManifestError,
    Source,
    canonical_url,
    load_manifest,
    normalize,
    snapshot_text,
    text_in_snapshot,
)

RULE_FILES: dict[str, Domain] = {
    "funding.json": "funding",
    "events.json": "events",
    "outside_money.json": "outside_money",
    "recognition.json": "recognition",
}


class RuleLoadError(Exception):
    """The rule table could not be loaded. `problems` holds one plain-language line per problem."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        lines = "\n".join(f"  - {problem}" for problem in problems)
        super().__init__(f"{len(problems)} problem(s) in the rule table; no rules were loaded:\n{lines}")


@dataclass(frozen=True)
class RuleSet:
    rules: dict[str, Rule]
    sources: dict[str, Source]
    files: dict[str, str] = field(default_factory=dict)  # rule id -> file name
    vocabulary: dict[str, dict[str, str]] = field(default_factory=dict)  # group -> name -> description

    def __iter__(self) -> Iterator[Rule]:
        return iter(self.rules.values())

    def __len__(self) -> int:
        return len(self.rules)

    def __contains__(self, rule_id: object) -> bool:
        return rule_id in self.rules

    def get(self, rule_id: str) -> Rule:
        try:
            return self.rules[rule_id]
        except KeyError:
            raise KeyError(f"no rule with id '{rule_id}'") from None

    def by_domain(self, domain: Domain) -> list[Rule]:
        return [rule for rule in self.rules.values() if rule.domain == domain]

    def source_for(self, rule: Rule) -> Source:
        return self.sources[canonical_url(rule.source_url)]

    def is_certain(self, rule_id: str) -> bool:
        """True only if the rule and everything it depends on is marked 'read'."""
        rule = self.get(rule_id)
        return rule.verified == "read" and all(self.is_certain(dep) for dep in rule.depends_on)

    def display_severity(self, rule_id: str) -> Severity:
        """What the officer sees. A rule that is not certain is always shown yellow."""
        rule = self.get(rule_id)
        if not self.is_certain(rule_id):
            return "yellow"
        return rule.severity

    def uncertain_reasons(self, rule_id: str) -> list[str]:
        """Plain-language reasons a rule is shown yellow, including those inherited from dependencies."""
        rule = self.get(rule_id)
        reasons: list[str] = []
        if rule.verified != "read" and rule.verification_note:
            reasons.append(rule.verification_note)
        for dep in rule.depends_on:
            for reason in self.uncertain_reasons(dep):
                if reason not in reasons:
                    reasons.append(reason)
        return reasons


def _format_validation_error(where: str, exc: ValidationError) -> list[str]:
    problems = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "rule"
        problems.append(f"{where}: {location}: {error['msg']}")
    return problems


def _read_json(path: Path, problems: list[str]) -> Any:
    try:
        return loads_strict(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"{path.name}: file not found in {path.parent}")
    except json.JSONDecodeError as exc:
        problems.append(f"{path.name}: not valid JSON (line {exc.lineno}, column {exc.colno}: {exc.msg})")
    except StrictJSONError as exc:
        problems.append(f"{path.name}: {exc}")
    except UnicodeDecodeError as exc:
        problems.append(f"{path.name}: not UTF-8 text ({exc.reason})")
    except IsADirectoryError:
        problems.append(f"{path.name}: is a folder, not a file")
    return None


def _load_vocabulary(rules_dir: Path, problems: list[str]) -> dict[str, dict[str, str]]:
    raw = _read_json(rules_dir / "vocabulary.json", problems)
    if raw is None:
        return {}
    groups = {key: value for key, value in raw.items() if key != "description"} if isinstance(raw, dict) else None
    if not groups or not all(
        isinstance(names, dict) and all(isinstance(k, str) and isinstance(v, str) and v for k, v in names.items())
        for names in groups.values()
    ):
        problems.append("vocabulary.json: expected groups of {name: description} objects")
        return {}
    return groups


# A deadline counted in one of these units rests on a definition no source gives; the rule that
# records that definition must be in depends_on, so the deadline is never shown as certain.
UNIT_DEFINITIONS = {
    "academic_weeks": "usg-academic-week-definition",
    "business_days": "usc-business-days-definition",
}
NUMBER_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
    9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
    16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
}
LIMIT_PREFIXES = ("max_", "min_", "threshold_")


def _number_in_text(number: int | float, text: str) -> bool:
    """True if the number is written in the text, as digits (with or without thousands commas) or
    as an English word, not as part of a longer number."""
    import re

    if isinstance(number, float) and not number.is_integer():
        forms = [repr(number)]
    else:
        value = int(number)
        forms = [str(value), f"{value:,}"]
        if value in NUMBER_WORDS:
            forms.append(NUMBER_WORDS[value])
    for form in forms:
        pattern = rf"(?<![\w.,]){re.escape(form)}(?![\w]|[.,]\d)" if form[0].isdigit() else rf"\b{re.escape(form)}\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def _check_numbers(rule: Rule, where: str, problems: list[str]) -> None:
    """Limits in params must be positive numbers, and for a rule marked 'read' every limit and every
    deadline offset must be a number the quoted source text states."""
    for key, value in rule.params.items():
        if not key.startswith(LIMIT_PREFIXES):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not value > 0:
            problems.append(f"{where}: params.{key} must be a positive number, got {value!r}")
        elif rule.verified == "read" and not _number_in_text(value, rule.source_text):
            problems.append(f"{where}: params.{key} = {value} is not a number the quoted source text states")
    if rule.kind == "deadline" and rule.offset is not None and rule.verified == "read":
        if not _number_in_text(rule.offset, rule.source_text):
            problems.append(f"{where}: offset {rule.offset} is not a number the quoted source text states")
    definition = UNIT_DEFINITIONS.get(rule.unit or "")
    if definition and definition not in rule.depends_on:
        problems.append(
            f"{where}: a deadline in {rule.unit} must depend on '{definition}' (the unit is not defined by any source)"
        )


def _check_params(rule: Rule, where: str, problems: list[str]) -> None:
    for key, value in rule.params.items():
        if key.endswith("_quote"):
            quotes = value if isinstance(value, list) else [value]
            for quote in quotes:
                if not isinstance(quote, str) or normalize(quote) not in normalize(rule.source_text):
                    problems.append(f"{where}: params.{key} {quote!r} is not part of source_text")
        elif key.endswith("_rules"):
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                problems.append(f"{where}: params.{key} must be a list of rule ids")


def _check_source(rule: Rule, where: str, sources: dict[str, Source], sources_dir: Path, problems: list[str]) -> None:
    source = sources.get(canonical_url(rule.source_url))
    if source is None:
        problems.append(f"{where}: source_url {rule.source_url} is not in rules/sources/manifest.json")
        return
    if source.version_date and rule.effective_date.isoformat() != source.version_date:
        problems.append(
            f"{where}: effective_date {rule.effective_date} differs from the source's version date "
            f"{source.version_date} in the manifest"
        )
    if rule.verified == "unverified":
        return
    try:
        snapshot = snapshot_text(sources_dir, source)
    except ManifestError as exc:
        problems.append(f"{where}: marked '{rule.verified}' but {exc}")
        return
    if rule.verified == "read" and not text_in_snapshot(rule.source_text, snapshot):
        excerpt = rule.source_text[:90] + ("…" if len(rule.source_text) > 90 else "")
        problems.append(
            f"{where}: marked 'read' but source_text is not in the snapshot {source.snapshot} "
            f"(exact match after whitespace normalisation): \"{excerpt}\""
        )


def _check_references(rules: dict[str, Rule], files: dict[str, str], problems: list[str]) -> None:
    for rule in rules.values():
        where = f"{files[rule.id]}: rule '{rule.id}'"
        for dep in rule.depends_on:
            if dep not in rules:
                problems.append(f"{where}: depends_on names unknown rule '{dep}'")
        for other in rule.conflicts_with or []:
            if other not in rules:
                problems.append(f"{where}: conflicts_with names unknown rule '{other}'")
            elif rule.id not in (rules[other].conflicts_with or []):
                problems.append(f"{where}: conflicts with '{other}', but '{other}' does not list it back")
        for key, value in rule.params.items():
            if key.endswith("_rules") and isinstance(value, list):
                for other in value:
                    if other not in rules:
                        problems.append(f"{where}: params.{key} names unknown rule '{other}'")

    # depends_on must not loop, or certainty could never be decided.
    state: dict[str, int] = {}

    def visit(rule_id: str, path: list[str]) -> None:
        if state.get(rule_id) == 2 or rule_id not in rules:
            return
        if state.get(rule_id) == 1:
            problems.append(f"depends_on forms a loop: {' -> '.join([*path, rule_id])}")
            return
        state[rule_id] = 1
        for dep in rules[rule_id].depends_on:
            visit(dep, [*path, rule_id])
        state[rule_id] = 2

    for rule_id in rules:
        visit(rule_id, [])


def load_rules(rules_dir: Path) -> RuleSet:
    """Load every rule file. Raises RuleLoadError listing all problems found."""
    problems: list[str] = []
    sources_dir = rules_dir / "sources"
    try:
        sources = load_manifest(sources_dir)
    except ManifestError as exc:
        raise RuleLoadError([str(exc)]) from exc

    vocabulary = _load_vocabulary(rules_dir, problems)
    known_triggers = {name for names in vocabulary.values() for name in names}

    rules: dict[str, Rule] = {}
    files: dict[str, str] = {}
    for file_name, domain in RULE_FILES.items():
        raw_file = _read_json(rules_dir / file_name, problems)
        if raw_file is None:
            continue
        try:
            rule_file = RuleFile.model_validate(raw_file)
        except ValidationError as exc:
            problems.extend(_format_validation_error(file_name, exc))
            continue
        if rule_file.domain != domain:
            problems.append(f"{file_name}: domain is '{rule_file.domain}', expected '{domain}'")
            continue
        if not rule_file.rules:
            problems.append(f"{file_name}: has no rules; an empty domain would let every check in it pass")
            continue

        for index, raw_rule in enumerate(rule_file.rules):
            label = raw_rule.get("id") if isinstance(raw_rule, dict) else None
            where = f"{file_name}: rule '{label}'" if isinstance(label, str) else f"{file_name}: rules[{index}]"
            if not isinstance(raw_rule, dict):
                problems.append(f"{where}: expected a JSON object")
                continue
            missing = [name for name in REQUIRED_FIELDS if raw_rule.get(name) in (None, "")]
            if missing:
                problems.append(f"{where}: missing {', '.join(missing)}; a rule without these does not load")
                continue
            try:
                rule = Rule.model_validate(raw_rule)
            except ValidationError as exc:
                problems.extend(_format_validation_error(where, exc))
                continue
            if rule.domain != domain:
                problems.append(f"{where}: domain is '{rule.domain}' but the rule is in {file_name}")
                continue
            if rule.id in rules:
                problems.append(f"{where}: id '{rule.id}' is already used in {files[rule.id]}")
                continue
            if vocabulary:
                unknown = [name for name in rule.triggers if name not in known_triggers]
                if unknown:
                    problems.append(f"{where}: triggers not in vocabulary.json: {', '.join(unknown)}")
            if rule.trigger_mode == "all" and len(rule.triggers) < 2:
                problems.append(f"{where}: trigger_mode 'all' needs at least two triggers")
            _check_params(rule, where, problems)
            _check_numbers(rule, where, problems)
            _check_source(rule, where, sources, sources_dir, problems)
            rules[rule.id] = rule
            files[rule.id] = file_name

    _check_references(rules, files, problems)
    for unit, definition in UNIT_DEFINITIONS.items():
        if any(rule.unit == unit for rule in rules.values()) and definition not in rules:
            problems.append(f"rule '{definition}' (the definition of {unit}) is missing")
    if problems:
        raise RuleLoadError(problems)
    return RuleSet(rules=rules, sources=sources, files=files, vocabulary=vocabulary)
