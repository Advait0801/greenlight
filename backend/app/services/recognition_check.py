"""Compare a constitution's text with the 2026-27 template, clause by clause. Pure code, no AI.

The clause list, the template wording and every rule a fill-in can break come from rules/recognition.json.
A clause is "present" only when the template's fixed words are in the document, letter for letter
(ignoring case, spacing and punctuation), in the Article, Section and Part where the template puts
them, with every blank filled in. Anything else is missing, changed, in conflict with a rule, or
needs a human look. The AI reader can only add doubt or point at a conflict; it can never make a
clause present.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal

from pydantic import BaseModel

from app.rules import RuleSet, citation_for, finding_for
from app.rules.schema import Rule
from app.schemas.common import PRECHECK_NOTICE, Citation, Verdict

State = Literal["present", "missing", "weak", "contradicts", "needs_look", "not_applicable"]

STATE_LABELS: dict[State, str] = {
    "present": "Present",
    "missing": "Missing",
    "weak": "Wording changed",
    "contradicts": "Conflicts with a rule",
    "needs_look": "Needs a human look",
    "not_applicable": "Not required for your club",
}
# What each state means for the officer. Green only for "present".
STATE_VERDICTS: dict[State, Verdict | None] = {
    "present": Verdict.GREEN,
    "missing": Verdict.RED,
    "weak": Verdict.RED,
    "contradicts": Verdict.RED,
    "needs_look": Verdict.YELLOW,
    "not_applicable": None,
}

BLANK = "{blank}"
BLANK_SHOWN = "________"
CLUB_FLAGS = ("has_parent_organization", "has_school_affiliation", "has_additional_officers", "has_appointed_positions")

ARTICLE_HEADING = re.compile(r"^[ \t]*ARTICLE\s+([IVX]{1,4})\b\s*[.:]?", re.IGNORECASE)
SECTION_HEADING = re.compile(r"^[ \t]*SECTION\s+([A-H])\s*[.:]", re.IGNORECASE)
PART_HEADING = re.compile(r"^[ \t]*PART\s*(\d{1,2})\s*[.:]", re.IGNORECASE)
INLINE_HEADING = re.compile(r"(?<=\S)[ \t]+(?=(?:ARTICLE\s+[IVX]{1,4}\s*[.:]|Section\s+[A-H]\s*[.:]|Part\s*\d{1,2}\s*[.:]))")
APPENDIX = re.compile(r"^[ \t]*APPENDIX\b")
DOT_LEADER = re.compile(r"\.{4,}")
PAGE_NOISE = re.compile(
    r"^(\[page \d+\]|\d{1,3}|page \d+( of \d+)?|constitution template for (recognized )?student organizations"
    r"|university of southern california|\d{4}\s*-\s*\d{2}\s*ay|table of contents)$",
    re.IGNORECASE,
)
YEAR_LABEL = re.compile(r"(20\d{2})\s*[-–/]\s*(\d{2})(?:\d{2})?\s*(?:AY|academic year)", re.IGNORECASE)
INSTRUCTION_TEXT = re.compile(
    r"ignore\s+(all\s+|the\s+|any\s+)?(previous\s+|prior\s+|above\s+)?(rules|instructions)"
    r"|mark\s+(this|it|everything|all|every)\b.{0,40}\b(present|approved|compliant|green|passing)"
    r"|(automated|ai)\s+(reviewer|checker|assistant|system)",
    re.IGNORECASE,
)
PLACEHOLDERS = {"na", "notapplicable", "tbd", "tba", "tobedetermined", "tobedecided", "none", "nil", "blank", "todo",
                "fillin", "insert", "xxx", "xxxx"}
# How to read a fill-in against each rule it could break: the yes/no question put to the AI reader, and
# words that make code doubt a "no". These are reading aids only. The rule's text, its citation and the
# verdict come from the rule table; a "yes" to a question means the rule is broken.
READING_AIDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "open-membership-no-academic-limits": (
        "Does this wording limit membership by major or program of study, class standing or year, GPA, or another "
        "academic requirement?",
        ("gpa", "grade point", "grades", "major", "majors", "minor", "class standing", "freshman", "freshmen", "sophomore",
         "sophomores", "junior", "juniors", "senior", "seniors", "undergraduate", "undergraduates", "graduate", "academic",
         "enrolled in the", "school of"),
    ),
    "open-membership-no-barriers": (
        "Does this wording make membership depend on an interview, an application, an audition, a tryout, a test or "
        "another assessment or selection?",
        ("interview", "interviews", "application", "applications", "apply", "audition", "auditions", "tryout", "tryouts",
         "try out", "assessment", "test", "exam", "selected", "selection", "chosen", "approval", "approved", "invitation",
         "invited", "nominated", "recruitment", "rush", "vote of"),
    ),
    "open-membership-no-other-org": (
        "Does this wording require belonging to another organization, society, team or group?",
        ("member of", "members of", "membership in", "belong", "belonging", "affiliated", "society", "fraternity", "sorority"),
    ),
    "dues-required-banned": (
        "Does this wording say that paying dues, a fee or any money is required, or is a condition of membership?",
        ("dues", "fee", "fees", "pay", "pays", "paying", "paid", "payment", "mandatory", "required", "must"),
    ),
    "voting-members-enrolled-students": (
        "Does this wording name anyone other than currently enrolled USC students (for example alumni, faculty, staff "
        "or people outside USC) as able to become a voting member?",
        ("alumni", "alumnae", "alumnus", "faculty", "staff", "community members", "non students", "anyone", "public",
         "parents", "friends"),
    ),
    "participation-usc-community-only": (
        "Does this wording name people outside USC (people who are not USC students, faculty, staff or alumni) as able "
        "to become members?",
        ("public", "community members", "anyone", "non usc", "other universities", "other schools", "other colleges",
         "high school", "parents", "friends"),
    ),
}
# Rules a fill-in clause names that the wording comparison itself covers (no question needed).
CHECKED_BY_WORDING = {"recognition-five-officers"}

NUMBER_WORDS = {"zero": 0, "no": 0, "none": 0, "never": 0, "one": 1, "once": 1, "two": 2, "twice": 2, "three": 3,
                "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


# ------------------------------------------------------------------------------------------------
# Text helpers


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


def despace(text: str) -> str:
    """Only the letters and digits, lower case. Two wordings are the same when these are equal."""
    return "".join(char for char in _fold(text) if char.isalnum())


def _despace_indexed(text: str) -> tuple[str, list[int]]:
    """despace(text), plus the position in `text` each kept character came from."""
    kept: list[str] = []
    index: list[int] = []
    for position, char in enumerate(text):
        for folded in _fold(char):
            if folded.isalnum():
                kept.append(folded)
                index.append(position)
    return "".join(kept), index


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _fold(text))


def _phrases(tokens: list[str], spans: list[tuple[int, int]]) -> list[str]:
    return [" ".join(tokens[start:end]) for start, end in spans if end > start]


# ------------------------------------------------------------------------------------------------
# The template, from the rule table


@dataclass(frozen=True)
class Clause:
    rule: Rule
    article: str | None  # roman numeral, or None for the cover page
    section: str | None
    part: int | None
    template: str  # wording after the "Part n." marker, blanks marked {blank}

    @property
    def label(self) -> str:
        return self.rule.source_section or self.rule.title

    @property
    def segments(self) -> list[str]:
        return [despace(segment) for segment in self.template.split(BLANK)]

    @property
    def fixed_tokens(self) -> list[str]:
        return _tokens(self.template.replace(BLANK, " "))

    @property
    def shown(self) -> str:
        return " ".join(self.template.replace(BLANK, BLANK_SHOWN).split())


def template_clauses(ruleset: RuleSet) -> list[Clause]:
    clauses = []
    for rule in ruleset:
        if rule.kind != "clause":
            continue
        params = rule.params
        article = re.match(r"Article\s+([IVX]+)", str(params.get("article", "")))
        text = str(params["template_text"])
        if params.get("template_text_continued"):
            text = f"{text} {params['template_text_continued']}"
        part = params.get("part")
        clauses.append(Clause(
            rule=rule,
            article=article.group(1) if article else None,
            section=params.get("section"),
            part=int(part) if part is not None else None,
            template=PART_HEADING.sub("", text, count=1).strip() if article else text,
        ))
    return clauses


def template_year(ruleset: RuleSet) -> str | None:
    """The academic year the template is for ("2026-27"), read from the clause rules' source name."""
    for rule in ruleset:
        if rule.kind == "clause":
            match = re.search(r"20\d{2}-\d{2}", rule.source)
            if match:
                return match.group(0)
    return None


# ------------------------------------------------------------------------------------------------
# The document's structure


@dataclass
class Chunk:
    number: int
    lines: list[str]
    used: bool = False

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


@dataclass
class Structure:
    preamble: list[str] = field(default_factory=list)
    sections: dict[tuple[str, str], list[Chunk]] = field(default_factory=dict)
    articles: set[str] = field(default_factory=set)
    loose: list[tuple[str, str]] = field(default_factory=list)  # (where, text) outside any Part


def parse_structure(text: str) -> Structure:
    """Split the text at its ARTICLE, Section and Part headings. Page headers, page numbers and the table
    of contents are dropped; the appendix is not part of the clause list."""
    text = unicodedata.normalize("NFC", text)
    line_starts = sum(1 for line in text.split("\n") if PART_HEADING.match(line))
    if line_starts < 10 and len(INLINE_HEADING.findall(text)) >= 20:
        # Pasted as one long paragraph: put each heading on its own line.
        text = INLINE_HEADING.sub("\n", text)
    structure = Structure()
    article: str | None = None
    section: str | None = None
    chunk: Chunk | None = None
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or PAGE_NOISE.match(line) or DOT_LEADER.search(line):
            continue
        if APPENDIX.match(line):
            break
        heading = ARTICLE_HEADING.match(line)
        if heading:
            article, section, chunk = heading.group(1).upper(), None, None
            structure.articles.add(article)
            continue
        heading = SECTION_HEADING.match(line)
        if heading and article:
            section, chunk = heading.group(1).upper(), None
            structure.sections.setdefault((article, section), [])
            continue
        heading = PART_HEADING.match(line)
        if heading and article and section:
            chunk = Chunk(number=int(heading.group(1)), lines=[line[heading.end():].strip()])
            structure.sections[(article, section)].append(chunk)
            continue
        if article is None:
            structure.preamble.append(line)
        elif chunk is not None:
            chunk.lines.append(line)
        else:
            structure.loose.append((f"Article {article}" + (f", Section {section}" if section else ""), line))
    return structure


# ------------------------------------------------------------------------------------------------
# Comparing one clause with one piece of the document


@dataclass
class Comparison:
    state: State
    reason: str  # exact, absent, blank_empty, placeholder, says_not_applicable, changed, extra_after
    document_text: str | None = None
    blanks: list[str] = field(default_factory=list)
    empty_blanks: list[int] = field(default_factory=list)
    missing_words: list[str] = field(default_factory=list)
    added_words: list[str] = field(default_factory=list)
    extra_lines: list[str] = field(default_factory=list)


def _says_not_applicable(squeezed: str) -> bool:
    return squeezed in ("na", "none") or squeezed.startswith("notapplicable")


def _is_placeholder(original: str, squeezed: str) -> bool:
    stripped = original.strip().strip(".,;:")
    bracketed = len(stripped) > 1 and stripped[0] in "[<{(" and stripped[-1] in "]>})"
    return squeezed in PLACEHOLDERS or bracketed


def _word_differences(clause: Clause, text: str) -> tuple[list[str], list[str]]:
    template, document = clause.fixed_tokens, _tokens(text)
    matcher = SequenceMatcher(None, template, document, autojunk=False)
    missing, added = [], []
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            missing.append((a0, a1))
        if tag in ("insert", "replace"):
            added.append((b0, b1))
    squeezed = despace(text)
    missing_words = [phrase for phrase in _phrases(template, missing) if despace(phrase) not in squeezed]
    # In a clause with blanks, extra words are the officer's own answer, so only a fixed clause lists them.
    added_words = _phrases(document, added) if BLANK not in clause.template else []
    return missing_words, added_words


def similarity(clause: Clause, text: str) -> float:
    """The share of the template's fixed words found, in order, in the text."""
    template = clause.fixed_tokens
    if not template:
        return 0.0
    matcher = SequenceMatcher(None, template, _tokens(text), autojunk=False)
    return sum(block.size for block in matcher.get_matching_blocks()) / len(template)


def _compare_text(clause: Clause, text: str) -> Comparison:
    squeezed, index = _despace_indexed(text)
    if not squeezed:
        return Comparison("missing", "blank_empty" if BLANK in clause.template else "absent", document_text=text or None)
    if _says_not_applicable(squeezed):
        return Comparison("missing", "says_not_applicable", document_text=text)
    segments = clause.segments

    def changed() -> Comparison:
        missing_words, added_words = _word_differences(clause, text)
        return Comparison("weak", "changed", document_text=text, missing_words=missing_words, added_words=added_words)

    if len(segments) == 1:
        return Comparison("present", "exact", document_text=text) if squeezed == segments[0] else changed()

    blankless = "".join(segments)
    cut_at_first_blank = bool(segments[0]) and blankless.startswith(squeezed) and len(squeezed) >= len(segments[0])
    if squeezed == blankless or cut_at_first_blank:
        return Comparison("missing", "blank_empty", document_text=text, empty_blanks=list(range(1, len(segments))))
    if not squeezed.startswith(segments[0]):
        return changed()
    position = len(segments[0])
    spans: list[tuple[int, int]] = []
    for number, segment in enumerate(segments[1:], start=1):
        if number == len(segments) - 1:
            end = len(squeezed) - len(segment)
            if segment and (not squeezed.endswith(segment) or end < position):
                return changed()
            spans.append((position, end))
        else:
            found = squeezed.find(segment, position)
            if found < 0:
                return changed()
            spans.append((position, found))
            position = found + len(segment)

    blanks: list[str] = []
    empty: list[int] = []
    placeholder = False
    for number, (start, end) in enumerate(spans, start=1):
        # The blank runs from just after the fixed words before it to just before the fixed words after it,
        # punctuation included, so a "[insert name]" keeps its brackets.
        left = index[start - 1] + 1 if start > 0 else 0
        right = index[end] if end < len(index) else len(text)
        value = text[left:right].strip(" \t\n:;,") if end > start else ""
        blanks.append(value)
        if end <= start:
            empty.append(number)
        elif _is_placeholder(value, squeezed[start:end]) and not clause.rule.params.get("none_is_acceptable"):
            empty.append(number)
            placeholder = True
    if empty:
        return Comparison("missing", "placeholder" if placeholder else "blank_empty", document_text=text,
                          blanks=blanks, empty_blanks=empty)
    return Comparison("present", "exact", document_text=text, blanks=blanks)


def compare(clause: Clause, lines: list[str]) -> Comparison:
    """Compare a clause with the lines under its Part heading. Lines after the clause's own wording that
    are not in the template are reported as extra text, never folded into a pass."""
    whole = _compare_text(clause, "\n".join(lines).strip())
    if whole.state == "present" or clause.template.endswith(BLANK):
        return whole
    for count in range(1, len(lines)):
        head = _compare_text(clause, "\n".join(lines[:count]).strip())
        if head.state == "present":
            head.extra_lines = [line for line in lines[count:] if line.strip()]
            return head
    return whole


# ------------------------------------------------------------------------------------------------
# The report


class Conflict(BaseModel):
    """A rule the officer's own wording breaks, or may break."""

    rule_id: str
    certain: bool  # False: needs a human look
    message: str
    fix: str | None
    basis: str  # how it was found: "number", "reader", "terms" or "not_read"
    reason: str  # why this needs a look, or "" when the conflict is certain
    terms: list[str] = []  # words in the officer's answer that made code doubt it
    evidence: str | None
    citation: Citation


class ClauseResult(BaseModel):
    rule_id: str
    label: str
    title: str
    article: str
    state: State
    state_label: str
    verdict: Verdict | None
    message: str
    suggestion: str | None
    template_text: str
    document_text: str | None
    missing_words: list[str]
    added_words: list[str]
    conflicts: list[Conflict]
    citation: Citation


class ReportNote(BaseModel):
    kind: str
    verdict: Verdict | None  # None: information only
    message: str
    detail: list[str] = []
    citation: Citation | None = None


class ConstitutionReport(BaseModel):
    notice: str = PRECHECK_NOTICE
    readable: bool
    message: str
    overall: Verdict | None  # None when the document could not be read
    summary: dict[str, int]
    notes: list[ReportNote]
    clauses: list[ClauseResult]
    document: dict[str, Any] = {}
    reader: dict[str, Any] = {}


@dataclass(frozen=True)
class ReaderAnswer:
    """One answer from the AI reader to a yes/no question about a fill-in (see recognition_intake)."""

    answer: Literal["yes", "no", "unclear"]
    confident: bool
    evidence: str | None


@dataclass(frozen=True)
class ReaderQuestion:
    number: int
    clause_rule_id: str
    banned_rule_id: str
    text: str


def reader_questions(ruleset: RuleSet) -> list[ReaderQuestion]:
    """The questions the AI reader is asked: one per fill-in clause and rule it could break. Built from
    the rule table only, so the request never depends on the uploaded document."""
    questions: list[ReaderQuestion] = []
    for clause in template_clauses(ruleset):
        if BLANK not in clause.template:
            continue
        for rule_id in clause.rule.params.get("contradicted_by_rules", []):
            question = READING_AIDS.get(rule_id, (None, ()))[0]
            if question:
                questions.append(ReaderQuestion(
                    number=len(questions) + 1, clause_rule_id=clause.rule.id, banned_rule_id=rule_id,
                    text=f"In {clause.label} ({clause.rule.title}) the template prints “{clause.shown}” and the officers "
                         f"typed the rest. About the words the officers typed there: {question}",
                ))
    return questions


def _count_in(value: str) -> int | None:
    """A whole number stated in a short answer ("two", "2", "at least 3"), or None when it is not clear."""
    found = {int(token) if token.isdigit() else NUMBER_WORDS[token] for token in _tokens(value)
             if token.isdigit() or token in NUMBER_WORDS}
    return found.pop() if len(found) == 1 else None


def _signal_terms(rule: Rule, text: str) -> list[str]:
    folded = " ".join(_tokens(text))
    return [term for term in READING_AIDS.get(rule.id, (None, ()))[1] if re.search(rf"\b{re.escape(term)}\b", folded)]


def _conflicts(
    ruleset: RuleSet, clause: Clause, comparison: Comparison, answers: dict[tuple[str, str], ReaderAnswer] | None
) -> list[Conflict]:
    """Rules the filled-in wording breaks (certain) or may break (needs a human look)."""
    out: list[Conflict] = []
    filled = " ".join(comparison.blanks)

    def add(rule: Rule, certain: bool, basis: str, reason: str = "", evidence: str | None = None,
            terms: list[str] | None = None) -> None:
        certain = certain and ruleset.display_severity(rule.id) == "red"
        out.append(Conflict(rule_id=rule.id, certain=certain, basis=basis, reason="" if certain else reason, terms=terms or [],
                            message=rule.message, fix=rule.fix_template if "{" not in (rule.fix_template or "") else None,
                            evidence=evidence, citation=citation_for(ruleset, rule.id)))

    for rule_id in clause.rule.params.get("contradicted_by_rules", []):
        rule = ruleset.get(rule_id)
        minimum = rule.params.get("min_meetings_per_semester")
        if minimum is not None:
            count = _count_in(filled)
            if count is None:
                add(rule, False, "number", f"Greenlight could not read a number in “{filled}”.")
            elif count < minimum:
                add(rule, True, "number", evidence=filled)
            continue
        if BLANK not in clause.template or rule_id in CHECKED_BY_WORDING:
            continue
        if rule_id not in READING_AIDS:
            add(rule, False, "not_read", "Greenlight cannot check this answer against every rule that applies to it.")
            continue
        terms = _signal_terms(rule, filled)
        answer = answers.get((clause.rule.id, rule_id)) if answers is not None else None
        if answer is None:
            add(rule, False, "terms" if terms else "not_read",
                "Greenlight's AI reader did not read this answer, so it was not checked against the rules below.", terms=terms)
            continue
        quoted = bool(despace(answer.evidence or "")) and despace(answer.evidence or "") in despace(comparison.document_text or "")
        if answer.answer == "yes":
            add(rule, answer.confident and quoted, "reader", "This answer may break a rule below.",
                evidence=answer.evidence if quoted else None)
        elif answer.answer == "no" and answer.confident:
            if terms:
                add(rule, False, "terms", "Check that this answer does not break a rule below.", terms=terms)
        else:
            add(rule, False, "reader", "Greenlight's AI reader was not sure about this answer.", terms=terms)
    return out


class _Defaults(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _suggestion(clause: Clause, state: State, comparison: Comparison, conflicts: list[Conflict]) -> str | None:
    if state == "present" or state == "not_applicable":
        return None
    if state == "contradicts":
        return next((conflict.fix for conflict in conflicts if conflict.certain and conflict.fix), None)
    if state == "needs_look":
        return None
    if comparison.reason == "extra_after":
        return "Remove the extra words, or move them to your bylaws."
    if BLANK not in clause.template or comparison.reason in ("absent", "changed"):
        return f"Use the template's wording exactly: “{clause.shown}”"
    filled = (clause.rule.fix_template or "").format_map(_Defaults(
        label=clause.label, what_to_add=clause.rule.title[:1].lower() + clause.rule.title[1:], template_text=clause.shown))
    return filled if filled and "{" not in filled else f"Fill in the blank: “{clause.shown}”"


def _message(clause: Clause, state: State, comparison: Comparison, conflicts: list[Conflict], required_reason: str | None) -> str:
    label = clause.label
    if state == "not_applicable":
        return f"{label} applies only if {required_reason}. You said that is not the case, so it is not checked."
    if state == "present":
        return f"{label} matches the template" + (", and the blank is filled in." if comparison.blanks else ".")
    if state == "contradicts":
        return f"{label}: " + " ".join(dict.fromkeys(conflict.message for conflict in conflicts if conflict.certain))
    if state == "needs_look" and conflicts:
        reasons = " ".join(dict.fromkeys(conflict.reason for conflict in conflicts if conflict.reason))
        terms = list(dict.fromkeys(term for conflict in conflicts for term in conflict.terms))
        if terms:
            reasons += f" Your wording mentions {', '.join(f'“{term}”' for term in terms)}."
        rules = " ".join(dict.fromkeys(conflict.message for conflict in conflicts))
        return f"{label} is filled in. {reasons} Check it against: {rules}"
    why = f" It is required because {required_reason} (or you did not say)." if required_reason else ""
    reason = comparison.reason
    if reason == "absent":
        return f"{label} ({clause.rule.title}) was not found in your document.{why}"
    if reason == "says_not_applicable":
        return f"{label} says it does not apply, but the template requires it.{why}"
    if reason in ("blank_empty", "placeholder"):
        count = len(clause.segments) - 1
        which = "The blank is" if count == 1 else f"{len(comparison.empty_blanks)} of the {count} blanks are"
        filler = " (a placeholder such as “N/A” or “TBD” does not count)" if reason == "placeholder" else ""
        return f"{label} ({clause.rule.title}): {which} not filled in{filler}.{why}"
    if reason == "extra_after":
        return f"{label} has the template's wording, but extra words follow it. Extra words can change what the clause means."
    parts = [f"{label} ({clause.rule.title}): the wording differs from the template."]
    if comparison.missing_words:
        parts.append("Missing: " + "; ".join(f"“{words}”" for words in comparison.missing_words[:6]) + ".")
    if comparison.added_words:
        parts.append("Added: " + "; ".join(f"“{words}”" for words in comparison.added_words[:6]) + ".")
    return " ".join(parts)


def _assign(clauses: list[Clause], chunks: list[Chunk]) -> dict[str, Chunk | None]:
    """Give each clause of one section its piece of the document: its own Part number when the wording
    fits, another Part when the officer renumbered, otherwise whatever sits under its number."""
    assigned: dict[str, Chunk | None] = {}

    def take(clause: Clause, chunk: Chunk) -> None:
        chunk.used = True
        assigned[clause.rule.id] = chunk

    for clause in clauses:
        for chunk in chunks:
            if not chunk.used and chunk.number == clause.part and similarity(clause, chunk.text) >= 0.8:
                take(clause, chunk)
                break
    for clause in clauses:
        if clause.rule.id in assigned:
            continue
        lead = clause.segments[0][:20]
        candidates = [(similarity(clause, chunk.text), chunk) for chunk in chunks
                      if not chunk.used and (not lead or despace(chunk.text).startswith(lead))]
        best = max(candidates, key=lambda pair: pair[0], default=None)
        if best and best[0] >= 0.9:
            take(clause, best[1])
    for clause in clauses:
        if clause.rule.id in assigned:
            continue
        same = next((chunk for chunk in chunks if not chunk.used and chunk.number == clause.part), None)
        if same is not None:
            take(clause, same)
        else:
            assigned[clause.rule.id] = None
    return assigned


def _preamble(clause: Clause, lines: list[str], fixed_starts: list[str]) -> Comparison:
    """Cover-page clauses have no Part heading; they are looked for in the text before Article I."""
    if BLANK in clause.template:
        lead = clause.segments[0]
        for position, line in enumerate(lines):
            squeezed, index = _despace_indexed(line)
            if lead and squeezed.startswith(lead):
                rest = line[index[len(lead) - 1] + 1:].strip(" \t:_-.")
                following = lines[position + 1] if position + 1 < len(lines) else ""
                if not rest and despace(following) and not any(despace(following).startswith(start) for start in fixed_starts):
                    # In the fillable PDF the typed name sits on the line under its label.
                    line, rest = f"{line} {following}", following.strip(" \t:_-.")
                if not rest:
                    return Comparison("missing", "blank_empty", document_text=line, empty_blanks=[1])
                if _is_placeholder(rest, despace(rest)):
                    return Comparison("missing", "placeholder", document_text=line, empty_blanks=[1])
                return Comparison("present", "exact", document_text=line, blanks=[rest])
        return Comparison("missing", "absent")
    region = " ".join(lines)
    if clause.segments[0] and clause.segments[0] in despace(region):
        return Comparison("present", "exact", document_text=clause.template)
    if similarity(clause, region) >= 0.6:
        missing_words, _ = _word_differences(clause, region)
        return Comparison("weak", "changed", missing_words=missing_words)
    return Comparison("missing", "absent")


def check_constitution(
    text: str,
    ruleset: RuleSet,
    club: dict[str, bool | None] | None = None,
    *,
    answers: dict[tuple[str, str], ReaderAnswer] | None = None,
    transcribed: bool = False,
    form_layout: bool = False,
) -> ConstitutionReport:
    """Check a constitution's text against the template.

    club          the four yes/no facts that decide whether a conditional clause is required; a fact that
                  is missing or None counts as yes, so leaving a clause out can never make it not required.
    answers       the AI reader's answers, keyed by (clause rule id, rule id); None when the reader did not run.
    transcribed   the text was typed out from a scan by the AI reader, which code cannot double-check, so
                  nothing read from it is shown as present.
    form_layout   the text comes from a fillable PDF, where typed answers are placed by position; a
                  mismatch around a blank is then a doubt about the reading, not a changed clause.
    """
    club = club or {}
    structure = parse_structure(text)
    clauses = template_clauses(ruleset)
    by_section: dict[tuple[str, str], list[Clause]] = {}
    for clause in clauses:
        if clause.article and clause.section:
            by_section.setdefault((clause.article, clause.section), []).append(clause)
    assigned: dict[str, Chunk | None] = {}
    for key, section_clauses in by_section.items():
        assigned.update(_assign(section_clauses, structure.sections.get(key, [])))

    fixed_starts = [clause.segments[0][:15] for clause in clauses if clause.article is None and BLANK not in clause.template]
    results: list[ClauseResult] = []
    extra: list[str] = []
    for clause in clauses:
        rule = clause.rule
        flag = rule.params.get("required_if_flag")
        required_reason = rule.params.get("required_if") if flag else None
        if clause.article is None:
            comparison = _preamble(clause, structure.preamble, fixed_starts)
        else:
            chunk = assigned.get(rule.id)
            comparison = compare(clause, chunk.lines) if chunk is not None else Comparison("missing", "absent")
        state: State = comparison.state
        conflicts: list[Conflict] = []
        if flag and club.get(flag) is False:
            state = "not_applicable"
        elif state == "present":
            conflicts = _conflicts(ruleset, clause, comparison, answers)
            if any(conflict.certain for conflict in conflicts):
                state = "contradicts"
                conflicts = [conflict for conflict in conflicts if conflict.certain or conflict.basis != "not_read"]
            elif conflicts or transcribed:
                state = "needs_look"
        elif state == "weak" and form_layout and BLANK in clause.template:
            state = "needs_look"
        if comparison.extra_lines and state != "not_applicable":
            extra.extend(f"After {clause.label}: {line}" for line in comparison.extra_lines)

        message = _message(clause, state, comparison, conflicts, required_reason)
        if state == "needs_look" and not conflicts:
            message = (
                f"{clause.label}: Greenlight read this from a scanned file and cannot double-check the reading. "
                "Compare it with the template yourself." if transcribed else
                f"{clause.label}: Greenlight could not line up your typed answer with the template's words in this PDF. "
                "Check that the blank is filled in."
            )
        verdict = STATE_VERDICTS[state]
        if verdict is not None:
            try:
                verdict = finding_for(ruleset, rule.id, verdict, message).verdict
            except ValueError:
                # The rule table does not allow a certain verdict on this rule (unverified, or sources disagree).
                verdict = Verdict.YELLOW
                if state == "present":
                    state = "needs_look"
                    other = ruleset.less_strict_side(rule.id)
                    why = (f"Official sources disagree about it: {rule.notes or ruleset.get(other).message} Ask "
                           f"{rule.owner_office} which applies." if other else
                           " ".join(ruleset.uncertain_reasons(rule.id)) or "This rule has not been confirmed yet.")
                    message = f"{clause.label} matches the template. {why}"
        results.append(ClauseResult(
            rule_id=rule.id, label=clause.label, title=rule.title, article=str(rule.params.get("article", "")),
            state=state, state_label=STATE_LABELS[state], verdict=verdict, message=message,
            suggestion=_suggestion(clause, state, comparison, conflicts),
            template_text=clause.shown, document_text=comparison.document_text,
            missing_words=comparison.missing_words, added_words=comparison.added_words,
            conflicts=conflicts, citation=citation_for(ruleset, rule.id),
        ))

    for chunks in structure.sections.values():
        extra.extend(f"Part {chunk.number}: {chunk.text}" for chunk in chunks if not chunk.used and despace(chunk.text))
    extra.extend(f"{where}: {line}" for where, line in structure.loose)

    notes = _notes(text, ruleset, structure, results, extra, transcribed)
    summary = {state: sum(1 for result in results if result.state == state) for state in STATE_LABELS}
    summary["total"] = len(results)
    summary["extra_text"] = len(extra)
    reds = summary["missing"] + summary["weak"] + summary["contradicts"]
    yellows = summary["needs_look"] + sum(1 for note in notes if note.verdict is Verdict.YELLOW)
    overall = Verdict.RED if reds else Verdict.YELLOW if yellows else Verdict.GREEN
    if reds:
        message = f"{reds} of {len(results)} clauses need fixing before you submit."
    elif yellows:
        message = "No clause is missing or changed, but some items need a human look before you submit."
    else:
        message = "Every required clause is present and filled in. Campus Activities makes the decision."
    return ConstitutionReport(readable=True, message=message, overall=overall, summary=summary, notes=notes, clauses=results)


def _notes(text: str, ruleset: RuleSet, structure: Structure, results: list[ClauseResult], extra: list[str],
           transcribed: bool) -> list[ReportNote]:
    notes: list[ReportNote] = []
    template_rule = "recognition-constitution-template"
    citation = citation_for(ruleset, template_rule) if template_rule in ruleset else None
    expected_year = template_year(ruleset)
    years = {f"{start}-{end}" for start, end in YEAR_LABEL.findall(text)}
    other_years = sorted(years - {expected_year}) if expected_year else []
    if other_years:
        notes.append(ReportNote(
            kind="other_year", verdict=Verdict.YELLOW, citation=citation,
            message=f"This document names the {', '.join(other_years)} academic year. Campus Activities accepts only the "
                    f"{expected_year} template, and its required wording changes from year to year.",
        ))
    found = sum(1 for result in results if result.state in ("present", "weak", "contradicts", "needs_look"))
    if not structure.articles or found < len(results) // 4:
        notes.append(ReportNote(
            kind="not_the_template", verdict=Verdict.YELLOW, citation=citation,
            message=f"This does not look like the {expected_year or 'current'} constitution template: Greenlight found few of "
                    "its articles, sections and parts. Clauses it could not find are listed as missing. If this is only part "
                    "of your constitution, upload the whole document.",
        ))
    if extra:
        notes.append(ReportNote(
            kind="extra_text", verdict=Verdict.YELLOW,
            message="Your document has text that is not in the template. Greenlight did not check it and did not act on it. "
                    "Read it yourself: extra wording can change what a clause means.",
            detail=extra[:40],
        ))
    if INSTRUCTION_TEXT.search(text):
        notes.append(ReportNote(
            kind="instruction_text", verdict=None,
            message="This document contains text written as an instruction to a reviewer. Greenlight treats everything in "
                    "an uploaded file as content to check, never as an instruction, and checked the document as usual.",
        ))
    if transcribed:
        notes.append(ReportNote(
            kind="transcribed", verdict=Verdict.YELLOW,
            message="This file had no text layer (a scan or a photo), so Greenlight's AI reader typed it out. Code cannot "
                    "double-check that reading, so no clause from it is shown as present.",
        ))
    return notes


def unreadable_report(message: str) -> ConstitutionReport:
    """The result for a file that could not be read: a clear message and no verdict, never a pass."""
    return ConstitutionReport(
        readable=False, message=message, overall=None, summary={}, notes=[], clauses=[],
    )
