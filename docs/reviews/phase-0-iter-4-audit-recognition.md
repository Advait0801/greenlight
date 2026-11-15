# Phase 0, iteration 4 — audit (recognition rules, constitution template, constitution test set)
Summary: 1 blockers, 0 high, 2 medium, 7 low.

Scope: `rules/recognition.json` (119 rules: 27 requirement/deadline/banned/info rules and 92 clause rules) against `rules/sources/constitution-template.txt` (and `raw/constitution-template.pdf`, including its form fields), `recognition-process.txt`, `recognition-faq.txt`, `rso-accountability.txt` and `student-handbook.txt`; `dues-required-banned` in `rules/outside_money.json` (linked from five clauses); `data/eval/constitutions/` (cases.json, texts/co-01..10, schema, `backend/app/eval_sets.py` constitution checks); the clause checks in `backend/app/rules/loader.py`; and the iteration 3 recognition audit.

Commit audited: `f65afcc`. Commands run: `python scripts/validate_rules.py` (OK; 280 read and 5 unverified rules in all files; every `read` quote verbatim), `python scripts/run_eval.py` (all four sets valid), `pytest` in backend (266 passed). Raw files match the manifest SHA-256 values, and the key dates and counts appear in `raw/recognition-process.html`. Template PDF ModDate is 2026-11-12, which matches `effective_date`. No file was changed apart from this report.

Method for the clauses: I parsed every "Part n" from the template snapshot (88 Parts) and matched each to a rule (all 88, plus 4 cover-page clauses; none duplicated, none extra). I listed the 81 PDF form-field widgets by page and mapped each one to a `{blank}` in `template_text`. Every field maps to a blank, except two of the three Article III, Section F, Part 1 fields. I checked every quote for template words left between its end and the next Part (only III.F.1 has any, apart from VIII.B.1, which `template_text_continued` covers). I checked every blank position against the whitespace and underscore runs in the snapshot, and the test texts by diffing each one against co-01 and matching each text against every clause's `template_text`.

Overall: every number, date, unit and audience in the requirement rules matches its source. The iteration 3 high finding (fixed words inside `fill_in` clauses) is fixed for 17 of its 18 clauses. The one left over, III.F.1 (term of office), still drops two of its three blanks and the fixed words "from" and "to". The test set now has no unlisted fault. Each of the ten texts differs from the template, or from co-01, only in the clauses that it lists.

| Rule id | Matches source? | Note |
|---|---|---|
| recognition-five-officers | Yes | Verbatim (process page, Membership Requirements). Five named positions match source and template III.A.1. |
| recognition-advisor | Yes | Verbatim. Full-time, not on sabbatical or leave; agrees with Handbook p.82 and template VII.A.2. |
| recognition-five-more-members | Yes | Verbatim; 5 additional members. |
| recognition-ten-students | Yes | Verbatim (Handbook p.82): 10 enrolled incl. 5 officers; FAQ agrees. same_shortfall_rules avoids a double finding. |
| recognition-accept-positions | Yes | Verbatim. Yellow is right (status not checkable). |
| recognition-constitution-template | Yes | Verbatim. Fillable, not printed or flattened. |
| recognition-accountability-document | Yes | Verbatim. |
| recognition-commitment-to-community | Yes | Verbatim; message now supported by the quote. |
| recognition-officer-trainings | Yes | Verbatim; July 1, 2026 to the deadline (completed_by_rules). Training names in message and params are on the page but not in the quote (L). |
| recognition-three-items-per-officer | Yes | Verbatim; 3 items x 5 officers. |
| recognition-application-window | Yes | Verbatim. Oct 27 to Nov 22 11:59 pm, no late applications; -08:00 correct (PST); year inferred from page date and "Spring 2027" heading. |
| recognition-advisor-deadline | Yes | Verbatim; Dec 1. item_rules exclude Clery (no date): correct. |
| recognition-advisor-annual | Yes | Verbatim. |
| recognition-submitting-officer | Yes | Verbatim. Message says "see"; the quote says only "edited" (L). |
| recognition-incomplete-not-considered | Yes | Verbatim (FAQ, 2026-07-24). |
| recognition-appeal | Yes | Verbatim (Handbook p.84). 10 business days after receipt (anchor fixed), 5 pages; depends on business-day rule, so yellow. |
| open-membership-no-academic-limits | Yes | Verbatim (Accountability page). |
| open-membership-no-barriers | Yes | Verbatim. |
| open-membership-no-other-org | Yes | Verbatim. |
| open-membership-criteria-focus | Yes | Verbatim; info is right ("should"). |
| voting-members-enrolled-students | Partly | Quote verbatim (Handbook p.82). Message adds "and others may be non-voting members", which no source says and Handbook p.77 item 4 contradicts (M). |
| advisor-meets-once-a-semester | Yes | Verbatim; min 1 per semester; linked from VII.B.2. |
| advisor-accepts-position | Yes | Verbatim. Message adds the mailer address from the next sentence; Dec 1 deadline is a reading of "advisor requirements" (L). |
| advisor-training-certificate | Yes | Verbatim. "Reach360" comes from the section heading only. |
| advisor-commitment-to-community | Yes | Verbatim. |
| advisor-clery-training | Yes | Verbatim; yellow, no due date: matches "deadline ... will be sent ... soon". |
| recognition-event-accessibility-training | Yes | Verbatim (template III.B.1). Yellow "confirm with Campus Activities"; conflicts_with reciprocated. |
| clause-preamble-name | Yes | Verbatim; fill_in; PDF field "Name of RSO". |
| clause-preamble-responsibility | Yes | Verbatim; fixed; cover-page sentence now encoded. |
| clause-preamble-non-discrimination | Yes | Verbatim; fixed. |
| clause-preamble-bylaws | Yes | Verbatim; fixed; cover-page sentence now encoded. |
| clause-i-a-1 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-i-a-2 | Yes | Verbatim; fixed_and_fill; blank = Acronym field. |
| clause-i-b-1 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-i-b-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-a-1 | Yes | Verbatim; fill_in; contradicted_by 5 rules incl. enrolled-voting and dues. |
| clause-ii-a-2 | Yes | Verbatim; fill_in; contradicted_by 4 rules. No rule for Handbook p.77 item 4 (M). |
| clause-ii-a-3 | Yes | Verbatim; fixed_and_fill; template_text matches template. |
| clause-ii-a-4 | Yes | Verbatim; fixed; dues link. |
| clause-ii-b-1 | Yes | Verbatim; fixed_and_fill, 2 blanks (both RSO Name/Acronym fields). |
| clause-ii-b-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-b-3 | Yes | Verbatim; fixed_and_fill. template_text keeps PDF artefact "w ill" for display (L). |
| clause-ii-c-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-c-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-c-3 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-c-4 | Yes | Verbatim; fixed_and_fill, 2 blanks. |
| clause-ii-c-5 | Yes | Verbatim; fixed_and_fill, 2 blanks; dues link added. |
| clause-ii-c-6 | Yes | Verbatim; fixed; duplicate of II.A.4 in the template, pinned by "Part 6.". |
| clause-ii-d-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-d-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-e-1 | Yes | Verbatim; fixed_and_fill; blank is the RSO Name/Acronym field (decision recorded). |
| clause-ii-e-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-e-3 | Yes | Verbatim; fixed; template_text matches template. |
| clause-ii-e-4 | Yes | Verbatim; fixed_and_fill; quote now starts "Part 4." and is unique. |
| clause-ii-e-5 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-a-1 | Yes | Verbatim; fixed_and_fill, 5 blanks, one per PDF field. No link to recognition-five-officers (L). |
| clause-iii-a-2 | Yes | Verbatim; fixed_and_fill, 2 blanks; required_if has_additional_officers (form says "Write N/A"; decision recorded). |
| clause-iii-b-1 | Yes | Verbatim; fixed; conflicts_with officer-trainings reciprocated. |
| clause-iii-b-2 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-b-3 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-b-4 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-b-5 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-b-6 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-b-7 | Yes | Verbatim; fill_in; required_if has_additional_officers. |
| clause-iii-c-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-c-2 | Yes | Verbatim; fixed_and_fill; blank is RSO Name/Acronym. |
| clause-iii-c-3 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-d-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-d-2 | Yes | Verbatim; fixed; "one month". |
| clause-iii-d-3 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-d-4 | Yes | Verbatim; fixed_and_fill (retyped). |
| clause-iii-d-5 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-d-6 | Yes | Verbatim; fixed_and_fill (retyped). |
| clause-iii-d-7 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-d-8 | Yes | Verbatim; fill_in; required_if has_appointed_positions. |
| clause-iii-d-9 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-e-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-e-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-e-3 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-e-4 | Yes | Verbatim; fixed_and_fill (retyped). |
| clause-iii-e-5 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iii-f-1 | No | Quote is verbatim but stops at "shall be"; the template continues "___ from ___ to ___." (three PDF fields). Typed fill_in with one blank (blocker). |
| clause-iii-f-2 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-f-3 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iii-g-1 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-iv-a-1 | Yes | Verbatim; fixed_and_fill, 2 blanks (first is RSO Name/Acronym). |
| clause-iv-a-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iv-a-3 | Yes | Verbatim; fixed_and_fill, 2 blanks. |
| clause-iv-a-4 | Yes | Verbatim; fixed_and_fill. |
| clause-iv-b-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-iv-b-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-v-a-1 | Yes | Verbatim; fixed_and_fill. |
| clause-v-a-2 | Yes | Verbatim; fixed_and_fill, 2 blanks. |
| clause-v-b-1 | Yes | Verbatim; fill_in; template_text matches template. |
| clause-v-b-2 | Yes | Verbatim; fixed_and_fill; blank is RSO Name/Acronym. |
| clause-vi-a-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-vi-a-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-vi-a-3 | Yes | Verbatim; fixed_and_fill. |
| clause-vi-a-4 | Yes | Verbatim; fixed_and_fill, 2 blanks. |
| clause-vi-a-5 | Yes | Verbatim; fixed; template_text matches template. |
| clause-vi-b-1 | Yes | Verbatim; fixed_and_fill, 2 blanks; required_if has_parent_organization. |
| clause-vi-b-2 | Yes | Verbatim; fixed_and_fill; required_if. Quote equals VI.C.2 except underscore count (L). |
| clause-vi-c-1 | Yes | Verbatim; fixed_and_fill, 2 blanks; required_if has_school_affiliation. |
| clause-vi-c-2 | Yes | Verbatim; fixed_and_fill; required_if. Quote equals VI.B.2 except underscore count (L). |
| clause-vii-a-1 | Yes | Verbatim; fixed_and_fill; blank is RSO Name/Acronym. |
| clause-vii-a-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-vii-a-3 | Yes | Verbatim; fixed; template_text matches template. |
| clause-vii-b-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-vii-b-2 | Yes | Verbatim; fixed_and_fill; linked to advisor-meets-once-a-semester. |
| clause-vii-b-3 | Yes | Verbatim; fixed; template_text matches template. |
| clause-vii-b-4 | Yes | Verbatim; fixed; template_text matches template. |
| clause-vii-b-5 | Yes | Verbatim; fixed_and_fill; blank is RSO Name/Acronym. |
| clause-vii-b-6 | Yes | Verbatim; fixed; template_text matches template. |
| clause-viii-a-1 | Yes | Verbatim; fixed_and_fill, 2 blanks. |
| clause-viii-a-2 | Yes | Verbatim; fixed; template_text matches template. |
| clause-viii-b-1 | Yes | Verbatim; fixed_and_fill; second blank in template_text_continued (page break). Displayed wording is cut (L). |
| clause-viii-b-2 | Yes | Verbatim; fixed_and_fill. |
| clause-viii-c-1 | Yes | Verbatim; fixed; template_text matches template. |
| clause-viii-c-2 | Yes | Verbatim; fixed; required_if has_parent_organization (no form field; decision recorded). |

## Test set check (data/eval/constitutions)
Each text diffed against co-01, and every text matched against every clause's `template_text`:
- co-01: every fixed clause matches the template exactly; blanks consistently filled; III.A.2 now states "an appointed position". Only the five not_applicable clauses do not match.
- co-02: differs from co-01 only in II.B.2 (missing), III.D.4 (weak), VIII.C.2 (missing), plus filled-in VI.B.
- co-03: only II.B.1 (weak) and III.D.2 (weak).
- co-04: only II.A.1 and II.A.2 (contradicts).
- co-05: only II.A.1 (contradicts) and III.G.1 (missing).
- co-06: only II.B.3 (missing), III.A.1 (weak), III.B.6 (missing), plus filled-in VI.C.
- co-07: a single newline, `readable: false`.
- co-08: adds the injected line; removes II.D.1 and IV.A.2.
- co-09: only II.A.1, VII.B.2 and VIII.A.2.
- co-10: only I.B.1, III.F.1, IV.A.1 and IV.A.4.

Nothing unlisted. Every `contradicted_by` is in the clause's `contradicted_by_rules`; not_applicable agrees with the club flags; 21 seeded faults, as data/eval/README.md says.

## Findings

### [blocker] Term of office (III.F.1) encodes one of its three blanks, so a missing start or end of term shows as present
Where: rules/recognition.json:2075-2100 (clause-iii-f-1: `source_text` "Part 1. The term of office shall be", `clause_type` "fill_in", `template_text` "Part 1. The term of office shall be {blank}", `check` "blank filled in"); rules/sources/constitution-template.txt:219-220; raw/constitution-template.pdf page 10 (fields "Length of term of office", "Start of term", "End of term"); backend/tests/unit/test_rules_loader.py:525-536.
Problem: the template reads "Part 1. The term of office shall be ___ from ___ to ___." with three form fields. The quote stops at "shall be", so the fixed words "from" and "to" and two blanks are not encoded, and the `fill_in` check passes as soon as any text follows "shall be". The full sentence is verbatim in the snapshot ("Part 1. The term of office shall be from to ." after whitespace collapsing). The iteration 3 audit listed this clause under its high finding but it was not retyped; the regression test does not name it; the loader's `fill_in` shape check (loader.py:255) cannot catch it because the quote itself was cut short.
Why it matters: "The term of office shall be one academic year." leaves two template blanks empty and drops two fixed words; under data/eval/README.md that is `missing`, but this rule counts it as filled in. That breaks the Phase 1 criterion "Zero cases where a missing required clause is shown as present". co-10 does not catch it (there the whole end is deleted).
Suggested fix: `source_text` "Part 1. The term of office shall be from to .", `clause_type` `fixed_and_fill`, `template_text` "Part 1. The term of office shall be {blank} from {blank} to {blank}."; a loader check that no template words lie between a clause quote's end and the next "Part n" or "Section" heading (`template_text_continued` may cover a page break); a test that a quote cut at "shall be" is rejected; optionally compare each PDF page's form-field count with the `{blank}` markers on that page.

### [medium] Conditional clauses depend on club facts with no defined origin, so a deleted clause can become "not applicable"
Where: rules/recognition.json:1415, :1609, :1908, :2612, :2641, :2670, :2699, :3111 (`required_if_flag`); data/eval/constitutions/cases.json `club` objects (co-06 :177-185 sets `has_appointed_positions: false` from the text itself); backend/app/eval_sets.py:295-302.
Problem: VI.B.1-2, VI.C.1-2, VIII.C.2, III.A.2, III.B.7 and III.D.8 are not applicable whenever the club's flag is false, and may then be absent. Nothing says where the flag comes from. If Phase 1 derives the flags from the uploaded constitution, a national chapter that deletes VI.B and VIII.C.2 reads as "no parent organization", and both clauses become not applicable instead of missing. The fillable form keeps this text for every club and asks for "N/A".
Why it matters: a missing required clause drops out with no finding, reached through the flag instead of the clause check.
Suggested fix: state (rules/README.md or `params.required_if_source`) that these facts come from the officer or the application answers, never from the constitution being checked; treat an unknown fact as applicable or yellow; add a case where a national chapter deletes VI.B and VIII.C.2, both expected `missing`.

### [medium] The enrolled-voting-members message says "others" may be non-voting members, but the Handbook limits who may participate
Where: rules/recognition.json:446 (voting-members-enrolled-students `message`); rules/sources/student-handbook.txt:3420-3421 ("4. Limit participation to students, faculty, staff, and alumni of the university."); rules/recognition.json:832-865 (clause-ii-a-2 `contradicted_by_rules`), :866 (clause-ii-a-3).
Problem: the message says "alumni, staff, faculty and others may be non-voting members". The quote says nothing about non-voting members; "and others" is unsupported and contradicts Handbook p.77 item 4, which no rule encodes, so a general-membership fill-in such as "anyone in the Los Angeles community" (II.A.2) is never contradicted.
Why it matters: an officer fixing a finding is told people outside USC may join, against the Handbook.
Suggested fix: change the message to "USC students, staff, faculty and alumni may be non-voting members" with a citation for it; add a `banned` rule quoting item 4 and link it from II.A.1 and II.A.2.

### [low] co-06 marks a deleted required officer as "weak", and III.A.1 has no link to the five-officer rule
Where: data/eval/constitutions/cases.json:190-194; rules/recognition.json:1364-1390 (clause-iii-a-1), :6-31 (recognition-five-officers).
Problem: co-06 deletes "Programming Chair is an ___ position." (fixed words and one of five blanks); under the README it fits both `weak` and `missing`; in substance it drops a required officer, and nothing links the clause to recognition-five-officers.
Suggested fix: add `contradicted_by_rules: ["recognition-five-officers"]` to clause-iii-a-1; say in the README which state applies when one blank and its words are deleted from a multi-blank clause, and set co-06 to match.

### [low] The template wording shown to officers is still garbled or cut in places
Where: rules/recognition.json:999 (II.B.3 "w ill"); :3004-3030 (VIII.B.1 display ends "...vote of the entire"); every `fixed_and_fill` message ("the blank" for multi-blank clauses); every fix_template printing raw `{blank}` markers.
Suggested fix: "will" in II.B.3's `template_text` (the whitespace-free comparison allows it); join VIII.B.1's halves for display or document it; say "the blanks" when there are several; render `{blank}` as "____".

### [low] The loader does not check where blanks sit, or that the continuation follows its clause
Where: backend/app/rules/loader.py:228-231, :248-249, :282-284.
Problem: markers can sit anywhere ("Part 4. A vote {blank} at a regular ..." passes for III.E.4); the continuation check only asks that the text appears somewhere in the snapshot, and VIII.B.1's continuation appears twice.
Suggested fix: check fragments between markers in order against the snapshot with a gap of at least two spaces or underscores at each marker; require the continuation to start right after the quote (at most a page header between).

### [low] The VI.B.2 and VI.C.2 quotes differ only in the number of underscores
Where: rules/recognition.json:2625, :2683.
Problem: with underscores collapsed they are the same sentence; the uniqueness check passes only because the underscore runs differ in length.
Suggested fix: pin each clause by its section heading, or collapse underscores in the uniqueness check and allow duplicates only in different sections.

### [low] Some messages state facts that are not in the cited passage (carried over from iteration 3)
Where: rules/recognition.json:485 (mailer address), :182 and :186-189 (training names), :308 ("see"), :508 ("Reach360" from the heading only), :489-491 (Dec 1 read from "advisor requirements").
Suggested fix: extend quotes, move facts into `*_quote` params or second rules, or drop the extra words; note the Dec 1 reading on advisor-accepts-position.

### [low] Test-set guards and wording
Where: backend/app/eval_sets.py:265-302; data/eval/constitutions/cases.json:5 (`method`); rules/README.md:53.
Problem: (a) no test checks that each text differs from co-01 only in its listed clauses; (b) nothing checks that a finding's `contradicted_by` is in the clause's `contradicted_by_rules`; (c) the `method` string names only the Accountability page; (d) rules/README.md:53 says ten dependent rules, validate_rules.py reports 14.
Suggested fix: add a test matching each text against every applicable clause's `template_text`, asserting the failures are exactly the listed findings; check `contradicted_by`; update the method string and README count.

## Iteration 3 findings re-checked
| Iteration 3 finding | Status at f65afcc |
|---|---|
| H1 fixed words inside 18 fill_in clauses | Fixed for 17; not for III.F.1 (blocker above) |
| M blank positions and garbled wording | template_text added and validated; positions not validated, "w ill" and cut VIII.B.1 display remain (lows above) |
| M Event Accessibility conflict | Fixed |
| M enrolled voting members | Fixed; message overreaches (medium above) |
| M cover page | Fixed |
| M contradiction links | Fixed; co-09 exercises VII.B.2 |
| M advisor items | Fixed; Clery yellow with no date |
| M form-field instructions, co-01 III.A.2 | co-01 fixed; field instructions still not in the snapshot (decision recorded); conditional-flag risk remains (medium above) |
| M uniform test set, empty file | Fixed |
| L ambiguous quotes | Fixed; VI.B.2/VI.C.2 pinned only by underscores (low above) |
| L club flags vs not_applicable | Fixed |
| L finding states | Fixed in the README; one-blank deletion from a multi-blank clause ambiguous (low above) |
| L messages beyond the quote | Partly fixed (low above) |
| L appeal anchor | Fixed; FAQ office name only in notes |
| L required_if on fixed text | Decision recorded; see medium above |
| L clause params not validated | Fixed |
| L Appendix | Open, recorded for a person |
| L two member-count rules | Fixed |
| L clause message wording | Open, recorded for a person |
| L training window end | Fixed |

(Saved by the orchestrator: the auditor's harness refused its write to docs/reviews/, so it returned the report as text. The rule check table and header are the auditor's own files; the sections above are transcribed from its returned report.)
