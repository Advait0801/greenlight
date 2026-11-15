# UI pass (portal rework) — review

Scope: the running build at http://localhost:8840, which is commit 00df745 (`frontend/dist` built 09:56, the same time as the commit). File:line references are to HEAD (00df745). **Someone edited the working tree while this review ran:** 15 frontend files were modified (`App.tsx`, `ui.tsx`, `index.css`, most pages) and `components/Icon.tsx` was added. I did not review those uncommitted edits. Check each finding again against them.

Method: headless Chromium (Playwright) at 1440x900 and 390x844 in a fresh browser context, following README "Try the demo (3 minutes)" step by step. I also checked keyboard use, computed contrast (WCAG formula, with background pixels sampled from screenshots where a background is blended), and ran DOM checks for citations and overflow. axe-core was not run because it is not installed. Scripts and screenshots are in `/private/tmp/claude-501/-Users-dalvi-Downloads-Projects-greenlight/6a43bec7-2cd7-4e23-872f-d3728cf60118/scratchpad/review/`.

Side effects on the running copy: my runs sent several red Culture Night applications for "Lantern Cultural Society" to the USG queue. They also drafted one denial reason, which was not approved, and approved one gap email locally.

Summary: The demo walk-through works at both sizes. Blockers: 0. High: 4. Medium: 3. Low: 6.

## 1. README walk-through

| Step | 1440x900 | 390x844 | Notes |
|---|---|---|---|
| 1 Recognition → sample → Check my constitution → Findings | PASS | PASS | The Findings step opens. GPA and transition texts are present. Focus moves to the report heading. |
| 2 Year plan → Load the demo club → Overview/Calendar/Budget and funding/Each event | PASS | PASS (page pans sideways, H4) | "Load the demo club" is also on Home. |
| 3 Each event → Culture night → Open event packet → Build the packet | PASS | PASS | "disagree" and "office decides" are present. On a phone, the detail shows under the five-event list and does not scroll into view (L6). |
| 4 Money check → load → Check the budget → Findings → send from Draft and send → back to Event and budget → line 1 35/5250, remove line 2, tickets No → check again | PASS | PASS | After the recheck, the result is "Overall: The office decides" with no "Breaks the rule". "Draft the application" is offered. Focus is lost after Check (M2). |
| 5 Each event → Culture night → Close the gap → Show the options → Draft an outreach email tab → Fill in example → Draft the email → approve | PASS | PASS | The button reads "Close the $1,170.00 gap", not "$1,170" as the README says (L1). The approval text reads "Greenlight has not sent anything." |
| 6 USG screen → passcode → Open → tick → Draft a reason → approve button | PASS | PASS | The queue items all read "Open" (L2). |
| 7 Accuracy: caught/missed/wrongly flagged | PASS | PASS | |

No console errors, page errors or HTTP ≥400 responses in any run. The /nope URL renders the Not found page.

## 2. Nothing lost
- The number of `<SourceLink>` uses per page is the same as before the rework (`4bfecb8^`); Dashboard adds 2.
- Event packet: 28 of 28 obligations carry their rule text. All 7 timeline anchors (`#ob-…`) resolve to visible targets.
- Year plan Overview, Calendar, and Budget and funding: every finding and deadline has its rule text.
- Verdict wording is unchanged. The `StatusBadge` labels are the same; only styling changed. "Check with USG" and "Check with the office" are the same as before.
- Exceptions: two new deadline lists have no rule text or source (H3). The money-check count tiles are mislabelled (M1).

## 3. Accessibility
- Tabs: arrow keys, Home and End work. Tab moves from the tablist into the panel.
- Master–detail list: items are buttons with `aria-pressed` and Enter selects. Every visible input, select and textarea has a label (checked on all 10 pages).
- Wizard steps are buttons with `aria-current="step"` and sr-only state text.
- Contrast, computed:

| Pair | Ratio |
|---|---|
| Gold on cardinal | 5.90 |
| White on cardinal | 8.92 |
| White/70 on cardinal (group titles) | 4.79 |
| Gold on the white/10 cards in the hero | about 4.5–5.1 |
| Stone-950 on gold | 13.07 |
| Cardinal on cardinal-50 | 8.11 |

- No text is gold on white. Gold on white would be 1.51:1, but gold is used only for fills and borders on white.
- Failures: the sidebar focus ring is invisible (H1), the phone menu does not take focus (H2), wizard focus is lost (M2), the hero eyebrow on a phone is 4.2:1 (M3), and some headings skip a level (L3).

## 4. Layout
- 1440 px: no overflow. The sticky header and sticky tab bar do not overlap (header bottom at 69 px, tab bar top at 86 px).
- 390 px: the document scrolls horizontally on every wizard page (H4).

## Findings

### [high] H1 Keyboard focus is invisible in the sidebar and the phone menu
Expected: visible focus on every control.
Actual: the global `:focus-visible` outline is 3px cardinal (`index.css:42`). The sidebar and drawer background is also cardinal, so focus on the Brand link and on every inactive nav link cannot be seen. Screenshots `kb2-brand-focus.png` and `kb2-rec-focus.png` show Recognition focused with no ring. The computed `outline-color` is rgb(153,0,0) on a background of rgb(153,0,0), which is 1:1.
Where: `App.tsx:19-55` (SideNav), `App.tsx:66-76` (Brand), `App.tsx:98,112`; `index.css:42`.
Smallest fix: in `index.css`, add `aside :focus-visible, [role="dialog"] :focus-visible { outline-color: #fff; }`. Alternatively, add `focus-visible:outline-white` to the NavLink, Brand and Close classes.
Reproduce: open / at 1440x900 and press Tab 2–4 times.

### [high] H2 The phone menu dialog does not take or keep focus, and Escape does not close it
Expected: a modal (`role="dialog" aria-modal="true"`) moves focus inside when it opens, keeps it there, closes on Escape, and returns focus to Menu.
Actual (390x844, keyboard only):
- Enter on "Menu" opens the drawer, but focus stays on Menu.
- The next Tabs go to "Load the demo club", "Check a constitution" and so on, which sit behind the overlay.
- Escape does nothing.
- Reaching the menu links takes about 16 Tabs through the hidden page.
- After a link is chosen, focus falls to `<body>`.
Where: `App.tsx:107-121`.
Smallest fix: autofocus the drawer's Close button when it opens. Add an `onKeyDown` Escape handler that calls `setMenuOpen(false)`, and return focus to the Menu button through a ref. For the background, either make it `inert` while the menu is open or trap Tab inside the drawer.
Reproduce: the `menu.js` script in the scratchpad.

### [high] H3 Two new deadline lists show dates without the rule text or source
Expected (PROJECT_CONTEXT §9): every deadline shows the rule text and its source link.
Actual:
- Home dashboard, "Upcoming deadlines": 6 dated items with title and event name only. No `SourceLink` and no badge.
- Year plan, *Each event* step, detail panel, "Its deadlines (n)": a date, a title and a badge per item, but no rule text or source. Culture night has 8 or more items, and 0 quotes in that step.

Both lists are new in this rework. The same items carry citations on the Calendar step.
Where: `pages/Dashboard.tsx:145-157`, `pages/YearPlanResults.tsx:333-344`.
Smallest fix: under each item, render `<details><summary>Rule text and source</summary><SourceLink citation={item.citation} /></details>`, as the Calendar step does. Alternatively, link each item to its Calendar entry and state that the source is shown there. The first option is preferred.

### [high] H4 Every wizard page scrolls sideways at 390 px
Expected: no horizontal overflow on a phone.
Actual: `documentElement.scrollWidth` is larger than 390 on:

| Page | scrollWidth |
|---|---|
| Year plan | 798–961 |
| Money check | 531 |
| Event packet | 408 |
| Gap helper | 407 |

`scrollTo(300,0)` works and shows blank space (`ov-plan-scrolled.png`). The cause: the `sr-only` state spans ("(current step)", "(before this step)") inside the horizontally scrolling step bar have no positioned ancestor. Their absolute positioning escapes the `overflow-x-auto` clip and widens the document.
Where: `components/ui.tsx:218` (Wizard `<ol>`), `ui.tsx:243`; also `ui.tsx:133` and `ui.tsx:147` (Steps).
Smallest fix: add `relative` to both `<ol>` elements (`className="relative flex gap-1 overflow-x-auto"`). As a backstop, add `overflow-x: clip` on `body`.

### [medium] M1 Money check count tiles count lines but read as finding counts
Expected: counts that match what is shown.
Actual: the tiles read "Breaks a rule 2, Needs a human look 0, The office decides 0, Lines 4". However, line 1 itself shows a "The office decides" finding (USG food review) and a "Needs a human look" vendor check. The values are `report.counts`, which the backend counts by line verdict (`money_check.py:750`), but the labels do not say "lines". A reader sees "The office decides: 0" beside an office-decides item.
Where: `pages/MoneyCheck.tsx:358-361`.
Smallest fix: relabel the tiles "Lines that break a rule", "Lines that need a human look" and "Lines the office decides", or add `hint: "lines"` to each.

### [medium] M2 Changing wizard step drops keyboard focus to the page body
Expected: focus lands on the new step.
Actual:
- Money check: after Enter on "Check the budget", `document.activeElement` is `BODY`.
- Any wizard: after Enter on "Next: …", focus is on `BODY` and the page scrolls to the top. A keyboard user must Tab again from "Skip to content".
- Recognition handles this correctly: focus moves to the report heading.
Where: `components/ui.tsx:209-212` (`go`); MoneyCheck's check handler (`MoneyCheck.tsx` around line 618).
Smallest fix: in `Wizard`, put a `tabIndex={-1}` ref on the step content wrapper and call `.focus()` after the step changes (in a `useEffect` on `step`).

### [medium] M3 The gold club-name eyebrow on the Home hero falls below AA on phones
Actual: at 390 px, the decorative `bg-gold/25 blur-3xl` blob lies behind "LANTERN CULTURAL SOCIETY" (12 px semibold). The lightest sampled background is rgb(177,49,0), which gives gold text a ratio of 4.20:1. At 1440 px the ratio is 5.90:1. The three hero cards on a phone are 4.64–4.80:1, which passes but only just.
Where: `pages/Dashboard.tsx:81` (blob), `:85` (eyebrow).
Smallest fix: add `hidden sm:block` to the blob, or set the eyebrow to `text-white`.

### [low] L1 README button name does not match the UI
The README says **Close the $1,170 gap**; the button reads "Close the $1,170.00 gap" (`YearPlanResults.tsx:328`). Fix: change the README text to "$1,170.00".

### [low] L2 USG queue buttons all have the accessible name "Open"
`UsgScreen.tsx:175`. A screen-reader user hears "Open, Open, Open". Fix: `aria-label={`Open ${a.event_name} from ${a.club_name}, ${a.reference}`}` (or `aria-describedby` pointing to the item title).

### [low] L3 Headings skip from h1 to h3
This happens on /money/check, /usg and /handover. On the USG screen, "Queue" is an h3 directly under the page h1. Fix: make the first section headings h2.

### [low] L4 The club name is not shown in the top bar on phones
The club chip is `hidden … sm:flex` (`App.tsx:139`), so below 640 px the top bar has no club name. Fix: show a compact chip (initial only) or the name under the page title.

### [low] L5 Some visual states rely on colour
- Wizard step bar: done steps show a check mark, but the current and upcoming steps both show a number and differ only by colour. Screen readers do get sr-only text.
- Master–detail selection is shown only by border and ring colour (`aria-pressed` is set).

These are not verdicts, but CLAUDE.md says state is never shown by colour alone. Fix: add a visible "Current" or "Selected" word, or a check mark and icon, to the active item (`ui.tsx:221-241`, `ui.tsx:286-296`).

### [low] L6 On a phone, picking an event does not bring its detail into view
In the year plan's *Each event* step at 390 px, the detail (with **Open event packet** and **Close the gap**) renders below all five events. After picking Culture night, the "Close the $1,170.00 gap" button was at y=989 in an 844 px viewport. The steps work, but the next button in README steps 3 and 5 is off-screen. Fix: in `MasterDetail`, call `detailRef.current.scrollIntoView()` on select when the layout is stacked (below lg).
