# UI pass — UX problems found (2026-11-15)

A frontend-only rework requested by the user after the `submission` tag ("the pages are too long and hard to navigate"; "too plain"). `submission` stays at 3c23303 as the fallback; the reworked UI is tagged `submission-v2`. No backend, API, rule, verdict or citation wording changes; information is collapsed, never removed.

Walked every page locally on the demo data (desktop 1280 px and phone 390 px). Before-screenshots: `docs/submission/screenshots/before-*.png`.

## Problems, in priority order

1. **Pages are one very long column.** Year plan with the demo club: 10,288 px on desktop, 14,792 px on a phone (six sections, 60+ calendar rows). Recognition report 8,728 px; money check 7,096 px; event packet 6,333 px. Nothing is summarised at the top, so the verdict is several screens down.
2. **No summary first.** Results open with the first detail, not the verdict and the counts (how many red, yellow, office-decides). A judge cannot see the outcome without scrolling.
3. **Results sit below the form.** On the money check, recognition and event packet the report appears under a long input form; after "Check" the user must scroll to find it.
4. **No in-page navigation.** Long results have no tabs, jump links or step indicator; sections cannot be collapsed.
5. **Navigation is a plain row of nine underlined links.** No active state beyond an underline, wraps to three lines on a phone, and the page order does not follow the demo journey.
6. **No visual hierarchy or identity.** System font everywhere, flat white boxes with the same thin border, headings barely larger than body text; only the header bar says "USC".
7. **Multi-step pages do not look like steps.** Money check (upload → event → lines → documents → fund → check → draft → send) and event packet (sentence → confirm → packet) show numbered headings only.
8. **Forms are dense and plain.** Inputs, selects and file pickers have browser defaults; the file picker is an unstyled "Choose Files"; buttons have no hover state and secondary buttons look like inputs.
9. **Status badges are small and low-contrast against white cards;** a row of them is hard to scan.
10. **Empty, loading and error states are bare text** ("Reading…", a red box) with no structure.
11. **Phone layout:** wide tables and two-column forms squeeze; the header takes a third of the first screen.

## Fixes (what changed)

- **Portal shell:** a cardinal sidebar grouped by task (Your club, Each event, For USG reviewers, Trust) with line icons; a white top bar with the section and the club; a phone menu that takes focus, closes on Escape and makes the page behind inert.
- **Home dashboard** at `/`: summary tiles, a "Coming up" list, "Fix first", the events table and links into each tool. The year plan moved to `/plan`.
- **Wizards with a step bar and Back/Next:** year plan (club and money → events → overview → calendar → budget and funding → each event), recognition (upload → findings → report → readiness), event packet (describe → check the details → the packet), money check (quotes → event and budget → findings → draft and send).
- **Summary first:** tiles with the counts open each result; long lists go into tabs (calendar months, report sections, gap options) or master–detail panes (clauses, budget lines, events, the USG queue).
- **Less text:** one-line page intros, with the rest under "About this page"; explanations, notes and rule text behind "Why?" or "Rule text and source", which opens in a tinted card; rule quotes that list items inline are shown as bullets (same words); the apply-by reasoning as three bullets.
- **Fewer boxes:** plain sections on hairlines, underlined tabs, real tables; cards kept for the summary tiles and the funding steps.
- **Readability:** Fraunces for page titles, Inter for text, 16 px body, 1.5 line height, prose capped near 70 characters.
- **Review (`ui-pass-review.md`):** H1 focus ring visible on the sidebar, H2 phone menu focus, H3 rule text on the two new deadline lists, H4 no sideways scroll at 390 px, M1 money tiles labelled as lines, M2 focus moves to the new step, L2 USG "Open" buttons named, L4 club shown on phones, L6 the selected detail scrolls into view on phones. L3 (heading levels) and L5 (current step also marked by underline and weight, not colour only) left as they are.

After-screenshots: `docs/submission/screenshots/after-*.png` (desktop 1440×900 and phone 390×844).
