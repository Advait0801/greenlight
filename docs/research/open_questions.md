# Open questions from PROJECT_CONTEXT section 8 — answers

Researched 2026-11-14 in Chrome (signed in with a USC Google account) and by public fetch. No USG officer was available, so every answer below comes from USG's own published documents. A person still has to review each rule before it goes live (CLAUDE.md).

| # | Question | Status |
|---|---|---|
| 1 | USG "Funding Application Deadlines" table; academic weeks across winter break | **Answered.** Table found and transcribed below |
| 2 | Spring 2027 academic calendar | **Answered.** Official USC calendar |
| 3 | Approved vendor and caterer lists | **Mostly answered.** USG Vendor List found (two tabs). The Purchasing approved-caterer list is still not public |
| 4 | Is the cap four funded events per semester? | **Answered, with a caveat.** Stated on the USG Funding page FAQ, not in the guidelines |

---

## 1. USG Funding Application Deadlines (2026-27)

- Source: "EDITED 26-27 Funding Application Deadlines", linked as "Funding Application Deadlines" in Section 1 of the [USG 26-27 Funding Department Guidelines](https://docs.google.com/document/d/1noJFJ4SxrFGD1Zm-6EqUHpXSIOUuFIL-gIobWXcXCt0/edit).
- URL: https://docs.google.com/spreadsheets/d/1M8FHvuw6f7ErnHnrQIR_ijjVmaKVXZp5-5fxrrJ7e68/edit
- **Access: requires a Google sign-in.** An anonymous request returns a login page, so `scripts/fetch_sources.py` cannot fetch it. The snapshot is `docs/research/manual_snapshots/usg-funding-deadlines-26-27.csv`, transcribed by hand from the sheet on 2026-11-14. Move or copy it into `rules/sources/` and mark it as a manual snapshot.
- The sheet is keyed by **event week**. It gives a "6 Week Deadline" (approved vendors) and a "9 Week Deadline" (travel). Each deadline is a Wednesday, the weekly application day.

| Event week | 6-week deadline | 9-week deadline |
|---|---|---|
| Aug 24 – Aug 28, 2026 | N/A | N/A |
| Aug 31 – Sep 4, 2026 | N/A | N/A |
| Sep 7 – Sep 11, 2026 | N/A | N/A |
| Sep 14 – Sep 18, 2026 | N/A | N/A |
| Sep 21 – Sep 25, 2026 | N/A | N/A |
| Sep 28 – Oct 2, 2026 | N/A | N/A |
| Oct 5 – Oct 9, 2026 | Aug 26, 2026 | — |
| Oct 12 – Oct 16, 2026 | Sep 2, 2026 | — |
| Oct 19 – Oct 23, 2026 | Sep 9, 2026 | — |
| Oct 26 – Oct 30, 2026 | Sep 16, 2026 | Aug 26, 2026 |
| Nov 2 – Nov 6, 2026 | Sep 23, 2026 | Sep 2, 2026 |
| Nov 9 – Nov 13, 2026 | Sep 30, 2026 | Sep 9, 2026 |
| Nov 16 – Nov 20, 2026 | Oct 7, 2026 | Sep 16, 2026 |
| Nov 23 – Nov 27, 2026 | Oct 14, 2026 | Sep 23, 2026 |
| Nov 30 – Dec 4, 2026 | Oct 21, 2026 | Sep 30, 2026 |
| Dec 7, 2026 – Jan 10, 2027 (sheet says "January 10, 2026", a typo) | — | — |
| Jan 11 – Jan 15, 2027 | Nov 11, 2026 | Nov 11, 2026 |
| Jan 18 – Jan 22, 2027 | Nov 11, 2026 | Nov 11, 2026 |
| Jan 25 – Jan 29, 2027 | Nov 11, 2026 | Nov 11, 2026 |
| Feb 1 – Feb 5, 2027 | Nov 18, 2026 | Nov 11, 2026 |
| Feb 8 – Feb 12, 2027 | Nov 18, 2026 | Nov 11, 2026 |
| Feb 15 – Feb 19, 2027 | Nov 18, 2026 | Nov 11, 2026 |
| Feb 22 – Feb 26, 2027 | Jan 13, 2027 | Nov 18, 2026 |
| Mar 1 – Mar 5, 2027 | Jan 20, 2027 | Nov 18, 2026 |
| Mar 8 – Mar 12, 2027 | Jan 27, 2027 | Nov 18, 2026 |
| Mar 15 – Mar 19, 2027 | — | — |
| Mar 22 – Mar 26, 2027 | Feb 3, 2027 | Jan 20, 2027 |
| Mar 29 – Apr 2, 2027 | Feb 10, 2027 | Jan 27, 2027 |
| Apr 5 – Apr 9, 2027 | Feb 17, 2027 | Feb 3, 2027 |
| Apr 12 – Apr 16, 2027 | Feb 24, 2027 | Feb 10, 2027 |
| Apr 19 – Apr 23, 2027 | Mar 3, 2027 | Feb 17, 2027 |
| Apr 26 – Apr 30, 2027 | Mar 10, 2027 | Feb 24, 2027 |

Rows with a single date (Oct 5 – Oct 23) are in the 6-week column. Each is 40 days before the event week, which is consistent with the rest of the column.

**What this means for the deadline calculator**

1. **Look deadlines up in this table. Do not compute them.** The table does not follow a simple "count N academic weeks back" rule:
   - Feb 22 → Nov 18 for the 9-week deadline does count 9 weeks if Dec 7 – Jan 10 is skipped.
   - But Jan 11 – Jan 29 events all map to Nov 11, and Feb 1 – Feb 19 events all map to Nov 18 for the 6-week deadline. Counting would give different dates.

   PROJECT_CONTEXT already says to treat the table as the source of truth. This confirms it.
2. **No deadline means no USG funding that week.** The blank rows are study days, exams and winter recess (Dec 7 – Jan 10), and spring recess (Mar 15 – 19). The "N/A" rows are the first six weeks of fall. Events outside Oct 5, 2026 – Apr 30, 2027 are not in the table at all.
3. Thanksgiving week (Nov 23 – 27) has deadlines, but Wed–Sun Nov 25 – 29 is a university holiday, and the guidelines bar funding for events during holidays. Block at the level of days, not weeks.
4. Nov 11, 2026 is both a deadline and the Veterans Day holiday. Show it as is.
5. **Planning spring from today (Nov 14, 2026):**
   - Events Jan 11 – Jan 29 have already missed both deadlines.
   - Events Feb 1 – Feb 19 have already missed the travel deadline. Their 6-week deadline is **Wednesday Nov 18, 2026**.
   - Events Feb 22 – Mar 12 have a travel deadline of **Nov 18, 2026**.

   This is the strongest "only this tool knows" moment for the year plan. PROJECT_CONTEXT section 11 says the retreat's deadline "lands in January". Per this table it lands in **November**, in the previous semester, so the demo script should say that.

**Sources disagree (show both, apply the stricter one)**

| Point | Guidelines (current as of Oct 21, 2026) | USG FAQ doc ([link](https://docs.google.com/document/d/11IYBlPhAzE_Exvim3Fm1Cr_nI6q6mdurzKACldOj9jU/)) | Deadline table |
|---|---|---|---|
| What the deadline counts back from | Initial **payment due date** | **Event date** | Event week |
| Travel lead time | **9** academic weeks | **8** academic weeks (stale; USG moved 8 → 9 in SB 145-05, Sep 2025) | 9-week column |
| Vendor not on the list | Not accepted | Allowed at 8 weeks as a "new vendor" | — |

Stricter reading to apply: use the deadline for the **earlier** of the payment due date and the event date, use 9 weeks for travel, and treat a vendor not on the list as red.

Other guideline details noticed:
- "2 business days" for fixing an incomplete application is defined in the guidelines as 48 hours from the notification.
- A fund at 50% use before the end of fall may be closed until the start of the spring review.

---

## 2. USC academic calendar, Spring 2027

Source: https://www.usc.edu/academic-calendar/ (official, public; read 2026-11-14). Status: **read**.

| Item | Date |
|---|---|
| Open registration | Thu–Fri Jan 7 – 8, 2027 |
| Classes begin | Mon Jan 11, 2027 |
| Martin Luther King Jr. Day holiday | Mon Jan 18, 2027 |
| Presidents' Day holiday | Mon Feb 15, 2027 |
| Spring recess | Sun–Sun Mar 14 – 21, 2027 |
| Classes end | Fri Apr 30, 2027 |
| Study days | Sat–Tue May 1 – 4, 2027 |
| Exams | Wed–Wed May 5 – 12, 2027 |
| Commencement | Wed–Sat May 12 – 15, 2027 |

Fall 2026, for the end-of-fall blocked dates:
- Veterans Day holiday: Wed Nov 11
- Thanksgiving holiday: Wed–Sun Nov 25 – 29
- Classes end: Fri Dec 4
- Study days: Sat–Tue Dec 5 – 8
- Exams: Wed–Wed Dec 9 – 16
- Winter recess: Thu Dec 17 – Sun Jan 10

The same page also lists 2027-28 and 2028-29.

**Check against TES:** `docs/research/club_platform.md` says there are no club events in the first 3 weeks of spring, with events allowed "after 26 Jan 2027" [F]. Three weeks from Jan 11 runs to Jan 31, so the two do not agree. Re-check the TES FAQ snapshot and show a "sources disagree" note if it really says Jan 26.

---

## 3. Approved vendor lists

**USG Vendor List**
- Linked as "Vendor List" in Section 1 of the guidelines: https://docs.google.com/spreadsheets/d/1OVOVukQGP5PsG-MO5IvbC-iYMKWNyNNjQjPbCEgjxtw/edit
- **Public.** It can be fetched without sign-in, one tab at a time:
  - `https://docs.google.com/spreadsheets/d/1OVOVukQGP5PsG-MO5IvbC-iYMKWNyNNjQjPbCEgjxtw/gviz/tq?tqx=out:csv&sheet=Food%20Vendors`
  - `https://docs.google.com/spreadsheets/d/1OVOVukQGP5PsG-MO5IvbC-iYMKWNyNNjQjPbCEgjxtw/gviz/tq?tqx=out:csv&sheet=Other%20Vendors`

**What's in it**
- Two tabs.
  - **Food Vendors** groups vendors by cuisine. Each row has a supplier number, a C/R/T code (catering, restaurant, truck), a website, and a status note.
  - **Other Vendors** covers talent agencies, audio-visual, printing, party rentals, buses, décor, flowers, photo booths, entertainment and more.
- Row statuses include "INACTIVE", "NOT FOUND" and registration states ("NONE", "In Progress", "Invited"). The sheet says vendors in these states "need to be checked" before a purchase order.
- Rule engine behaviour:
  - On the list and active: pass.
  - INACTIVE, NOT FOUND, or a registration problem: **yellow** ("check vendor status with USG").
  - Not on the list: **red**.

**Being on the vendor list does not make an expense eligible**
- The Other Vendors tab lists charter bus companies, balloon vendors, talent agencies and DJs.
- The guidelines list buses, balloons and "payments to talent or performers" as ineligible.
- So run the vendor check and the eligible-expense check separately. A DJ from a listed vendor is still red.

**Both the guidelines and the FAQ say the list is not exhaustive and statuses can change.** The guidelines still say a vendor not on the list will not be accepted. Show the date the list was fetched.

**Still open:**
- The Purchasing Services approved-caterer list is not public. `club_platform.md` says it is checked by phone, so keep that rule `unverified` (yellow).
- USC Trademarks keeps a separate list of licensed merchandise vendors at https://trademarks.usc.edu/authorized-vendors-student-organizations/. The Other Vendors tab points there for promotional items.

---

## 4. Four funded events per semester

- Source: the [USG Funding page](https://usg.usc.edu/branches/funding/), FAQ item "How much funding is available per organization?" (read 2026-11-14 in Chrome). It says each RSO can have up to four events funded per semester, as long as the club stays under $8,000 from USG. Take the exact sentence from the page snapshot.
- The 26-27 guidelines **do not state this cap**. They state only the $8,000 yearly cap (Section 3). The FAQ doc does not mention it either.
- Recommendation:
  - Encode it with `source` = USG Funding page FAQ and `verified: "read"`.
  - Add a note that the binding guidelines are silent on it.
  - Show it as **yellow** with "confirm with usgfunds@usc.edu", never as a silent hard cap. The planner can still warn when a plan asks for a fifth funded event in one semester.
- Also on that page: "up to $356,100" for the year, which conflicts with the Daily Trojan's $388,000. PROJECT_CONTEXT already says not to show a total.

---

## 5. Officers on what got their application sent back

- Reddit (r/USC) is blocked by the browser's safety restrictions, so no first-hand threads could be read.
- A news search found nothing newer than `docs/research/student_org_pain_points.md` (dated 2026-11-13), which already has the documented cases.
- Talking to real officers is still a task for the humans (PLAN.md section 3).
