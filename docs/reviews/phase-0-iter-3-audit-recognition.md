# Phase 0, iteration 3 — audit (recognition rules and constitution test set)
Summary: 0 blockers, 1 high, 8 medium, 11 low.

Scope: `rules/recognition.json` (110 rules) against `rules/sources/constitution-template.txt` (and `raw/constitution-template.pdf`, including its 55 form fields), `recognition-process.txt`, `recognition-faq.txt`, `student-handbook.txt` and `rso-accountability.txt`; plus `data/eval/constitutions/` (cases.json, texts/co-01..10, schema).
Commit audited: `9c3f500`. Commands run: `python scripts/validate_rules.py` (OK; 254 read and 5 unverified rules across all files, all `read` source_text verbatim), `python scripts/run_eval.py` (all four sets valid), `pytest` in backend (208 passed). No file was changed apart from this report.

Overall: every `source_text` is in its snapshot, and every number, date, unit and audience matches its source: 5 named officers, 5 more members / 10 students including 5 officers, one full-time advisor not on leave, trainings from July 1, 2026, 3 items per officer, Oct 27 to Nov 22 at 11:59 pm with no late applications, advisor items due Dec 1, 10 business days to appeal with a 5-page limit, one month for off-cycle officers. `effective_date` values match the manifest (template PDF ModDate is 2026-11-12). All 8 articles, every Part (I.A.1 to VIII.C.2, 88 Parts) and the cover-page name and non-discrimination sentence are covered. No blocker was found. The main weaknesses are in how clause types are assigned (the "fixed" wording inside many `fill_in` clauses is never checked), in requirements that the sources state but no rule encodes, and in the test set's baseline constitution.

## Rule check
| Rule id | Matches source? | Note |
|---|---|---|
| recognition-five-officers | Yes | Verbatim (process page, Membership Requirements). Positions match source and template III.A.1. |
| recognition-advisor | Yes | Verbatim. Handbook p.82 and template VII.A.2 agree (full-time). |
| recognition-five-more-members | Yes | Verbatim; 5 additional. Consistent with handbook 10 incl. 5 officers and FAQ 10; overlaps recognition-ten-students (L9). |
| recognition-ten-students | Yes | Verbatim (Handbook p.82). 10 students incl. 5 officers matches PROJECT_CONTEXT s.7. |
| recognition-accept-positions | Yes | Verbatim. Yellow (status not checkable) is reasonable. |
| recognition-constitution-template | Yes | Verbatim. Fillable, not printed or flattened, as spec says. |
| recognition-accountability-document | Yes | Verbatim. |
| recognition-commitment-to-community | Yes | Verbatim. Message adds "by DocuSign" and "2026-27" from other passages (L4). |
| recognition-officer-trainings | Yes | Verbatim; July 1, 2026 correct. conflicts_with clause-iii-b-1 listed both ways, but params omit Event Accessibility despite the note (M2); no end date param (L11). |
| recognition-three-items-per-officer | Yes | Verbatim. 3 items x 5 officers matches source. |
| recognition-application-window | Yes | Verbatim. Oct 27 / Nov 22 11:59 pm, no late applications; -08:00 is correct for PST. Year 2026 inferred from page date and spec. |
| recognition-advisor-deadline | Yes | Verbatim (December 1). Message names items not in the cited passage (L4). |
| recognition-advisor-annual | Yes | Verbatim. Advisor items themselves are not enumerated anywhere (M6). |
| recognition-submitting-officer | Yes | Verbatim. info is right. |
| recognition-incomplete-not-considered | Yes | Verbatim (FAQ). FAQ is older (mentions 2025-26 template) but process page and Handbook agree on incomplete = not recognized. |
| recognition-appeal | Yes | Verbatim (Handbook p.84). 10 business days, 5 pages correct. Anchor says decision_date; source says receipt of decision (L5). depends_on business-day rule (unverified) so shown yellow: correct. |
| open-membership-no-academic-limits | Yes | Verbatim. |
| open-membership-no-barriers | Yes | Verbatim. |
| open-membership-no-other-org | Yes | Verbatim. |
| open-membership-criteria-focus | Yes | Verbatim. info is right ("should"). |
| clause-preamble-name | Yes | Verbatim. fill_in correct (PDF field "Name of RSO"). Other two cover-page paragraphs not encoded (M4). |
| clause-preamble-non-discrimination | Yes | Verbatim. fixed correct. |
| clause-i-a-1 | Yes | Verbatim, right passage. fill_in correct. |
| clause-i-a-2 | Yes | Verbatim. Typed fill_in but has binding fixed wording ("in all publicity materials and correspondence") (H1). |
| clause-i-b-1 | Yes | Verbatim, right passage. fill_in correct. |
| clause-i-b-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-a-1 | Yes | Verbatim. contradicted_by_rules right; lacks the Handbook rule limiting voting members to enrolled students (M3). |
| clause-ii-a-2 | Yes | Verbatim. contradicted_by_rules right. |
| clause-ii-a-3 | Yes | Verbatim. fixed_and_fill correct (field "Open Membership Participation Opportunities"). |
| clause-ii-a-4 | Yes | Verbatim. fixed; contradicted_by dues-required-banned is right. |
| clause-ii-b-1 | Yes | Verbatim (includes the underscores). fixed_and_fill correct. Handbook p.78 item 8 also requires this statement; could be cited as second source. |
| clause-ii-b-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-b-3 | Yes | Verbatim incl. PDF artefact "w ill" (noted). Shown to officers as template wording (M1). |
| clause-ii-c-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-c-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-c-3 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-c-4 | Yes | Verbatim. Typed fill_in; fixed wording "must attend at least" unchecked (H1). |
| clause-ii-c-5 | Yes | Verbatim. Typed fill_in; "may be asked to pay" is unchecked and no contradicted_by dues-required-banned (H1, M5). none_is_acceptable is an inference, not source text. |
| clause-ii-c-6 | Yes | Verbatim. Duplicate of II.A.4 in template; both encoded: correct. |
| clause-ii-d-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-d-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-e-1 | Yes | Verbatim but starts mid-sentence. fixed_and_fill correct; PDF blank is the shared RSO Name/Acronym field (see M7). |
| clause-ii-e-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-e-3 | Yes | Verbatim, right passage. fixed correct. |
| clause-ii-e-4 | Yes | Verbatim but the quote also matches III.E.4 text (ambiguous, L1). Typed fill_in; fixed wording unchecked (H1). |
| clause-ii-e-5 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-a-1 | Yes | Verbatim (blanks collapsed). fixed_and_fill correct; five PDF fields "Appointed or Elected". No machine-readable blank positions (M1). |
| clause-iii-a-2 | Yes | Verbatim. PDF field label says "whether they are elected or appointed. Write N/A if none" (M7, L6). |
| clause-iii-b-1 | Yes | Verbatim. fixed; conflicts_with recognition-officer-trainings reciprocated; Event Accessibility conflict documented. |
| clause-iii-b-2 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-b-3 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-b-4 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-b-5 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-b-6 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-b-7 | Yes | Verbatim. Field label says "Write N/A if none"; required_if plausible. |
| clause-iii-c-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-c-2 | Yes | Verbatim. fixed_and_fill correct. |
| clause-iii-c-3 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-d-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-d-2 | Yes | Verbatim. fixed; "one month" matches. |
| clause-iii-d-3 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-d-4 | Yes | Verbatim, mid-sentence. Typed fill_in although "may nominate any other member, including self nominations" is fixed; same shape as II.E.1 which is fixed_and_fill (H1). |
| clause-iii-d-5 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-d-6 | Yes | Verbatim. Typed fill_in; fixed wording unchecked (H1). |
| clause-iii-d-7 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-d-8 | Yes | Verbatim. required_if appointed positions correct. |
| clause-iii-d-9 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-e-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-e-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-e-3 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-e-4 | Yes | Verbatim (template says "withdraw membership" for officers; that is the template). fill_in; fixed wording unchecked (H1). |
| clause-iii-e-5 | Yes | Verbatim, right passage. fixed correct. |
| clause-iii-f-1 | Yes | Verbatim but stops before "from ___ to ___" (three PDF fields). fill_in (H1). |
| clause-iii-f-2 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-f-3 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iii-g-1 | Yes | Verbatim, right passage. fill_in correct. |
| clause-iv-a-1 | Yes | Verbatim. First blank is the shared RSO Name field (M7). fill_in. |
| clause-iv-a-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-iv-a-3 | Yes | Verbatim. fill_in; "must be communicated to all members" unchecked (H1). |
| clause-iv-a-4 | Yes | Verbatim. fill_in (H1). |
| clause-iv-b-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-iv-b-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-v-a-1 | Yes | Verbatim. fixed_and_fill correct. |
| clause-v-a-2 | Yes | Verbatim. fill_in; fixed wording unchecked; compare V.B.2 typed fixed_and_fill (H1). |
| clause-v-b-1 | Yes | Verbatim, right passage. fill_in correct. |
| clause-v-b-2 | Yes | Verbatim. fixed_and_fill correct; PDF blank is the shared RSO Name field (M7). |
| clause-vi-a-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-vi-a-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-vi-a-3 | Yes | Verbatim, mid-sentence. fixed_and_fill correct. |
| clause-vi-a-4 | Yes | Verbatim, mid-sentence. fixed_and_fill correct. |
| clause-vi-a-5 | Yes | Verbatim, right passage. fixed correct. |
| clause-vi-b-1 | Yes | Verbatim. required_if correct, but the form says "Write N/A if not affiliated" (L6). fill_in has fixed "is the USC chapter of" (H1). |
| clause-vi-b-2 | Yes | Verbatim. fixed_and_fill + required_if; form keeps the fixed text with N/A (L6). |
| clause-vi-c-1 | Yes | Verbatim. As VI.B.1. |
| clause-vi-c-2 | Yes | Verbatim. As VI.B.2. |
| clause-vii-a-1 | Yes | Verbatim, right passage. fixed_and_fill correct. |
| clause-vii-a-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-vii-a-3 | Yes | Verbatim, right passage. fixed correct. |
| clause-vii-b-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-vii-b-2 | Yes | Verbatim. fill_in; recognition page says advisors meet "at least once a semester"; no rule rejects 0 (M5). |
| clause-vii-b-3 | Yes | Verbatim, right passage. fixed correct. |
| clause-vii-b-4 | Yes | Verbatim, right passage. fixed correct. |
| clause-vii-b-5 | Yes | Verbatim. fixed_and_fill correct. |
| clause-vii-b-6 | Yes | Verbatim, right passage. fixed correct. |
| clause-viii-a-1 | Yes | Verbatim. fill_in; "vote of the entire membership at a regular meeting" unchecked (H1). |
| clause-viii-a-2 | Yes | Verbatim, right passage. fixed correct. |
| clause-viii-b-1 | Yes | Verbatim up to page break (noted). fill_in; same as VIII.A.1 (H1). |
| clause-viii-b-2 | Yes | Verbatim. fill_in (H1). |
| clause-viii-c-1 | Yes | Verbatim, right passage. fixed correct. |
| clause-viii-c-2 | Yes | Verbatim. fixed with required_if; template has no field here, so deleting it means the fillable form was edited (L6). |

## Findings

### [high] Fixed template wording inside 18 `fill_in` clauses is never checked
Where: rules/recognition.json:494 (clause-i-a-2), :850 (ii-c-4), :876 (ii-c-5), :1063 (ii-e-4), :1510 (iii-d-4), :1562 (iii-d-6), :1745 (iii-e-4), :1797 (iii-f-1), :1901 (iv-a-1), :1953 (iv-a-3), :1979 (iv-a-4), :2083 (v-a-2), :2291 (vi-b-1), :2345 (vi-c-1), :2503 (vii-b-2), :2633 (viii-a-1), :2685 (viii-b-1), :2712 (viii-b-2)
Problem: these clauses have `clause_type: "fill_in"` and `check: "blank filled in"`, but each has binding fixed wording around the blank. Examples: II.C.5 "Members **may be asked** to pay dues"; III.D.4 "___ may nominate any other member, **including self nominations**"; VIII.A.1 / VIII.B.1 "by a ___ vote **of the entire membership at a regular meeting**"; IV.A.3 "Notice of special meetings **must be communicated to all members** at least ___"; II.C.4 "Voting members **must attend at least** ___". Clauses with the same structure are typed inconsistently: II.E.1 ("___ may remove any member ...") is `fixed_and_fill` while III.D.4 ("___ may nominate any other member ...") is `fill_in`, and V.B.2 is `fixed_and_fill` while V.A.2 is `fill_in`. In the template PDF these are all fixed text with a form field in the middle.
Why it matters: PROJECT_CONTEXT 4B requires detecting "required text missing or altered". With the clause list as written, "Members must pay dues of $10" (II.C.5), "Only officers may nominate" with "including self nominations" deleted (III.D.4), or "amended by a majority vote of the Executive Board" (VIII.B.1) would all count as "blank filled in" and show as present. Phase 1's "zero missing-shown-as-present" criterion would then rest on the model noticing the change, which breaks "code checks".
Suggested fix: retype every clause that has fixed wording outside its blank as `fixed_and_fill` (keep `fill_in` only for clauses that are a lead-in followed by a free-text field: I.A.1, I.B.1, II.A.1–2, III.B.2–7, III.D.3/5/7/8, III.F.2–3, III.G.1, V.B.1). Add a test that every `fill_in` clause's source_text ends at its blank.

### [medium] Blank positions are lost, so code cannot compare "unaltered and filled in", and the "template wording" shown is garbled
Where: rules/recognition.json:1115 (iii-a-1 "The President is an position. Vice President is an position."), :745 (ii-b-3 "w ill"), :985/:1063/:1510/:2213/:2239 (quotes that start mid-sentence without "Part n."), fix_template "Restore the template wording: \"{template_text}\"" on every fixed clause
Problem: `source_text` has to be verbatim after whitespace collapsing, so the blanks disappear. No param records where each blank is, so a deterministic comparison of fixed text around blanks is not possible. The text officers would be shown as "template wording" reads "The President is an position." or "w ill provide".
Why it matters: Phase 1 exit criterion "each finding shows the template wording" would show broken text. Without blank markers, the "unaltered" judgement is likely to be handed to the model.
Suggested fix: add `params.template_text` with explicit blank markers (for example "The President is an {president_elected_or_appointed} position."), and have a validator check that removing the markers and collapsing whitespace gives `source_text`. Use it for display and comparison, and keep `source_text` as the citation.

### [medium] Officer trainings: the Event Accessibility conflict is not applied
Where: rules/recognition.json:166-192 (recognition-officer-trainings `params.trainings`, `notes`), :1168 (clause-iii-b-1)
Problem: the template (III.B.1) names "Hazing Prevention, Event Accessibility, and RSO Officer Training modules"; the recognition page names Hazing Prevention 101 and the RSO Officer Learning Path. The note says "Greenlight lists every training either source names", but `params.trainings` lists only the two from the recognition page. No source mentions an Event Accessibility module anywhere else.
Why it matters: rules/README says the stricter rule applies when sources disagree. A readiness tracker driven by `params` will list two trainings and could show the training row as complete while the template requires a third module.
Suggested fix: add "Event Accessibility" to `params` marked as from the template only, and show it yellow ("confirm with Campus Activities"). Otherwise, change the note so it matches what the rule does.

### [medium] Handbook rule "voting members and officers are currently enrolled USC students" is not encoded
Where: rules/sources/student-handbook.txt:3419-3420 ("5. Limit its voting members and officers to currently enrolled USC students."), :3609 ("Limit its voting membership to currently enrolled USC students."); rules/recognition.json:572-604 (clause-ii-a-1 contradicted_by_rules)
Problem: no rule carries this requirement. II.A.1's `contradicted_by_rules` covers academic limits, barriers, another membership and dues, but not voting rights for alumni, staff or non-students.
Why it matters: a voting-membership fill-in such as "alumni and faculty who attend three meetings" contradicts the Handbook and the template's II.A.3 ("non-voting members"), and would pass.
Suggested fix: add a `banned` rule quoting Handbook p.82 (or p.77 item 5) and add it to II.A.1's `contradicted_by_rules`. Add a test constitution for it.

### [medium] Cover page is only partly covered
Where: rules/sources/constitution-template.txt:14-19; rules/recognition.json:416-467
Problem: the cover page has three fixed passages. Only the name blank and the non-discrimination sentence are encoded. Two are missing: "The responsibility for recognition of student organizations falls within Campus Activities in USC Student Life." and "This constitution outlines the structure, purpose, and operational guidelines ... but the bylaws may not supersede this constitution."
Why it matters: the brief asks for every clause of the template, including the cover page. The bylaws sentence is substantive: co-09's "bylaws take precedence" contradicts it as well as VIII.A.2, and a constitution that edits only the cover paragraph would not be flagged.
Suggested fix: add `clause-preamble-responsibility` and `clause-preamble-bylaws` (fixed).

### [medium] Missing contradiction links that the sources support
Where: rules/recognition.json:876-903 (clause-ii-c-5), :2503-2528 (clause-vii-b-2); rules/sources/recognition-process.txt:241 ("meet with the RSO at least once a semester")
Problem: (a) II.C.5 (dues amount and use) has no `contradicted_by_rules: ["dues-required-banned"]`, although "dues are required for voting members" is the most likely place for a dues requirement. II.A.1, II.A.2, II.A.4 and II.C.6 all carry the link. (b) VII.B.2 "Officers should meet with the advisor ___ times per semester" has no lower bound. The recognition page says advisors agree to "meet with the RSO at least once a semester", so a fill-in of 0 contradicts it.
Why it matters: these are fill-ins that contradict fixed rules, which is exactly what the recognition check is meant to catch.
Suggested fix: add the dues link to II.C.5. Add a `requirement` rule quoting the recognition-page sentence with `params.min_meetings_per_semester: 1`, and list it in VII.B.2's `contradicted_by_rules`.

### [medium] Advisor readiness items are not enumerated in any rule
Where: rules/recognition.json:239-277 (recognition-advisor-deadline, recognition-advisor-annual); rules/sources/recognition-process.txt:232-262
Problem: PROJECT_CONTEXT 4B and PLAN Phase 1 call for a tracker of "advisor items". The sources list four: accept the position on EngageSC, the RSO Advisor Training certificate (Reach360), the DocuSigned Commitment to Community (both by Google Form), and the Clery Act course (confirmed by report, deadline "will be sent ... soon"). No rule names them or carries their source text. The advisor-deadline message lists two of them, but its cited `source_text` is only "December 1: Deadline for advisors to submit their requirements."
Why it matters: Phase 1 would have to hard-code advisor items in Python or show them with a citation that does not support them. The Clery item has no Dec 1 date and should be shown as "office decides / date to come", not as due Dec 1.
Suggested fix: add one rule per advisor item quoting its passage, with `params.items`. Give the Clery item no due date and a yellow severity.

### [medium] The template's form-field instructions are not in the snapshot, and the baseline test constitution breaks one of them
Where: rules/sources/raw/constitution-template.pdf (form fields; for example "Additional Officer positions and whether they are elected or appointed. Write N/A if none.", "Name of Parent Organizaton, Write N/A if not affiliated", Appendix "must follow the structure of the Constitution above (e.g., no copying your entire previous Constitution or national org bylaws)"); rules/sources/constitution-template.txt (text only); data/eval/constitutions/texts/co-01.txt:51, :42, :95, :111
Problem: the fillable PDF's field labels carry instructions that the text snapshot omits, so no rule can quote them. As a result:
- co-01, the "complete and correct" baseline that all ten cases are built from, gives III.A.2 as "Outreach Chair." without saying whether it is elected or appointed, which the field instruction asks for. This fault is in all ten texts and none of them lists it.
- In the PDF, the blanks in II.E.1 ("___ may remove any member"), IV.A.1 ("A meeting of ___") and V.B.2 ("In appointing such committees, ___ members") are the shared "RSO Name/Acronym" field (widgets on pages 6 and 12). co-01 fills them with "The Executive Board", "the general membership" and "Executive Board members". Text produced from the real fillable form cannot read that way.
Why it matters: expected answers should come from the template. A baseline with an unlisted fault either teaches the engine to miss it or counts a correct flag as a false positive.
Suggested fix: have `fetch_sources.py` append the field names and labels (with page numbers) to the template snapshot so rules can quote them. Then either add "state elected or appointed" to clause-iii-a-2 and fix co-01:51 (for example "Outreach Chair, an appointed position"), or record that the test set accepts it. Decide whether shared-name blanks must hold the club's name, and update co-01 and the clause params to match.

### [medium] Test set does not exercise several required behaviours, and cannot hold an empty-file case
Where: data/eval/constitutions/cases.json (all ten `club` objects identical); backend/app/eval_sets.py:258-259
Problem: all ten cases are the same club with no parent organization and no school affiliation, so no case tests VI.B, VI.C or VIII.C.2 when they apply. No case leaves a `fixed_and_fill` blank empty (for example II.B.1's name or II.A.3's opportunities). No case alters the fixed wording of a `fill_in` clause (see the high finding). No case is the wrong-year template. `expected.readable` exists but is always true, and `_check_constitutions` reports an empty text file as a problem, so a `readable: false` case for an empty file cannot be added at all.
Why it matters: Phase 1 exit criteria include "an unreadable or empty file gives a clear message, not a pass" and 95% recall. A set this uniform cannot show either.
Suggested fix: allow empty or whitespace-only files when `readable` is false. Add or replace cases covering a chapter of a national organization (VI.B and VIII.C.2 applicable), an empty fixed_and_fill blank, an altered fill_in wording, and an empty file. If the count must stay at 10, swap in cases that duplicate patterns, such as one of the two "clause removed" cases.

### [low] Ambiguous and mid-sentence source quotes
Where: rules/recognition.json:1063 (clause-ii-e-4 "at a regular or special meeting shall be sufficient to withdraw membership.")
Problem: this quote also matches III.E.4 (constitution-template.txt:216-217), so the verbatim check passes without pinning the passage. II.E.1, III.D.4, VI.A.3 and VI.A.4 also drop their "Part n." prefix.
Why it matters: the citation does not uniquely identify the clause, and the display text loses its section marker.
Suggested fix: begin each quote with "Part n." (after whitespace collapsing, "Part 4. at a regular ..." is still verbatim). Add a validator check that a clause quote occurs exactly once in its snapshot.

### [low] Club flags are not cross-checked against `not_applicable`; co-06 flag is stale
Where: data/eval/constitutions/cases.json:183 (co-06 `has_appointed_positions: true`); backend/app/eval_sets.py:246-270
Problem: co-06 removes the Programming Chair, the only position described as appointed, but keeps `has_appointed_positions: true`. `_check_constitutions` does not check that `not_applicable` holds only clauses with `required_if`, or that the club flags imply them.
Suggested fix: add both checks, and set the co-06 flag from the text.

### [low] Finding states are not defined
Where: data/eval/schemas/constitutions.schema.json (`state` enum); cases.json co-03 (III.D.2 "one month" changed to "one semester": `weak`) compared with co-07 and co-09 (altered fixed clauses: `contradicts`)
Problem: there is no written rule separating `weak` from `contradicts` for a fixed clause that was altered.
Suggested fix: define the states in data/eval/README.md (for example: missing = absent or blank; weak = fixed wording altered without reversing it; contradicts = a fill-in breaks a rule, or the wording says the opposite), and score the state separately from detection.

### [low] Messages state facts that the cited source text does not contain
Where: rules/recognition.json:183 (officer-trainings "Older certificates are not accepted"; from the FAQ), :251 (advisor-deadline "training certificate and Commitment to Community, by Google Form"), :159 (commitment-to-community "by DocuSign")
Problem: each claim is true somewhere in the sources, but not in the passage the finding cites.
Suggested fix: cite the passage that supports each claim (a second rule, or a `params.*_quote` within the rule's source text), or remove the claim from the message.

### [low] Appeal rule: anchor and second source
Where: rules/recognition.json:314-343
Problem: the source counts from "the receipt of the decision", but the anchor is `decision_date`. Counting from the decision date is stricter, so it is safe, but the label is inaccurate. The FAQ names a different office (AVP for Student Culture and Community); this is mentioned only in `notes` and the FAQ is not cited.
Suggested fix: rename the anchor to `decision_received_date`, or label it "from the day you receive the decision". Show both office names with both links.

### [low] `required_if` on fixed template text allows that text to be deleted
Where: rules/recognition.json:2318, :2372 (vi-b-2, vi-c-2), :2764 (viii-c-2); co-01.txt:122-127, :154
Problem: the template keeps this fixed text for every club and instructs "Write N/A" in the name blank. VIII.C.2 has no field at all. Marking these clauses not applicable treats their deletion (co-01 replaces them with "Not applicable.") as correct, although a document on the unmodified fillable form would still contain them.
Suggested fix: decide which behaviour is intended and write it down. If fidelity to the form is the goal, require the fixed text and accept "N/A" in the blank.

### [low] Clause params are not validated
Where: backend/app/rules/schema.py:97 (`params: dict[str, Any]`)
Problem: `clause_type`, `article`, `section`, `part` and `required_if` are not checked. A typo such as `"fixed_and_fil"` would load silently.
Suggested fix: when `kind == "clause"`, validate `params.clause_type` against the three values and require `clause`, `article` and `part`.

### [low] Appendix not encoded
Where: rules/sources/constitution-template.txt:345-346 (page 16 "APPENDIX"); PDF field on page 16
Problem: the Appendix and its instruction (additional procedures must follow the constitution's structure, with no copying of a previous constitution or national bylaws) are not represented.
Suggested fix: add an optional `info` clause once the field text is in the snapshot.

### [low] Two member-count rules give two red findings for one shortfall
Where: rules/recognition.json:51 (recognition-five-more-members), :72 (recognition-ten-students)
Problem: the two sources agree (5 + 5 = 10, including officers), so a single shortfall triggers both rules.
Suggested fix: show one finding with both citations, or list one rule in the other's `depends_on` or `notes` so the readiness check reports one item.

### [low] Clause message wording
Where: rules/recognition.json:420 ("Cover page (Name of the organization (cover page)) must be filled in."); every fill_in clause message
Problem: the parentheses are nested. Fill-in clauses that can be contradicted (II.A.1, II.A.2) say only "must be filled in", which is wrong when the finding is a contradiction.
Suggested fix: write a message for each state, or let the contradicting rule's message lead.

### [low] Training window has no end in params
Where: rules/recognition.json:183-187
Problem: the source says "between July 1, 2026 and the application deadline", but `params` has only `completed_on_or_after`.
Suggested fix: add `completed_by_rule: "recognition-application-window"`, or put the date in params, so a certificate dated after the deadline is caught.
