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

Recorded in the commits after this file; summary at the end of the pass.
