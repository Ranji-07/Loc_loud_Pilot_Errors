# Screen status

Checked 2026-11-24 in headless Chrome against the real backend (127.0.0.1:8765). Screenshots are kept locally in `.screens/` (not committed).

| Screen | Real API | Loading / empty / error | Dark / light | Keyboard | Status |
|---|---|---|---|---|---|
| Shell (sidebar, palette, themes, status) | `/health`, `/approvals?status=pending` | yes / n/a / offline state | both checked, 1366, 820, 390 px | Tab order, Ctrl+K, arrows, Enter, Esc, skip link | Done (step 2) |
| Overview | health, approvals, agent runs, models, model calls since month start, usage, audit | yes / yes / yes per card | both, 3 widths, no horizontal overflow | links and buttons reachable | Done (step 4) |
| Agents | `/agents/*`, SSE stream | partial (old page) | both (tokens) | yes | Works; redesign in step 6 |
| Decisions → Approvals | `/approvals`, `/approvals/{id}/decide` | yes / yes / yes | dark checked | yes | Works: pending item shown in Overview and the nav badge, denied from Decisions, run ended with the deny note, History shows `approval.denied` |
| Decisions → Decisions | none | empty state explains why | — | — | Unavailable (Phase 3) |
| History | `/audit?limit=200` | partial (old page) | both (tokens) | yes | Works; filters and paging in step 8 |
| Infrastructure (Health, Setup guides) | `/health`, runbooks | yes / n/a / yes | both (tokens) | yes | Works; redesign in step 9 |
| Costs | `/usage`, `/usage/model-calls` | old page | both (tokens) | yes | Works; redesign in step 10 |
| Projects, Tasks, Prompt Studio, Knowledge, Models, Settings | none | Unavailable screen lists what is missing | — | — | Unavailable |

Checks run: axe-core WCAG 2 A/AA, 0 violations (Overview dark and light, Decisions, Agents). No page errors on any route. Backend: 69 tests passed. Not run yet: Lighthouse score, Playwright UI test suite, VS Code ↔ web approval round trip.
