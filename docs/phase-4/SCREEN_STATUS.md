# Screen status

Phase 4 baseline checked 2026-11-24 against the built dashboard and real backend at `127.0.0.1:8765`. Scope approved at stop point B: real APIs only, read-only backend Settings. Stop point C was subsequently approved. Phase 5 is now paused at the user's request, not complete.

All 12 navigation pages and six detail sections have screenshots at **1366, 820 and 390 px, dark and light**: 108 combinations in `.screens/step10-*.png`. No page errors or horizontal overflow in the final checks. Prompt Studio's mobile overflow was found and fixed, then retested at all six combinations.

| Screen | API mapping | Loading / empty / error | Keyboard / interaction evidence | Status |
|---|---|---|---|---|
| Shell and Overview | health, approvals, agent runs/models, monthly model calls, usage, audit | implemented per data section; offline state | Earlier stop-B navigation/palette/theme checks; final screenshots | Working |
| Projects | none | explicit unavailable state | navigation reachable | Deferred by approved scope, Phase 2 |
| Agents: Runs, Performance, Permissions | `/agents/models`, `/agents/runs`, run detail and SSE, `/settings` | loading/empty/error; stream disconnection visible | Start, Retry, Continue, deep links, arrow/Home/End tabs | Working for the fixed Droid agent; agent registry deferred |
| Tasks | none | explicit unavailable state | navigation reachable | Deferred by approved scope, Phase 2 |
| Prompt Studio | existing Droid models/runs/start APIs | loading/empty/error, missing-variable guard | Editor → variable → strict run → streamed result tested | Basic execution working; save/templates/versions/context/compare deferred |
| Decisions: Approvals | shared `/approvals`, decide API | loading/empty/error, busy action guard | Approve and Deny reflected in History in isolated browser tests; earlier real Droid deny check | Working; raw contents/patches, not a full diff/rollback workflow |
| Decisions: engineering Decisions | none | explicit unavailable state | tab reachable | Deferred by approved scope, Phase 3 |
| Knowledge | none | explicit unavailable state | navigation reachable | Deferred by approved scope, Phase 2 |
| History | `/audit` filters and cursor, `/audit/export` | loading/empty/error with Retry | Search, clear, 25-row pages with no overlap, older/newer; exports covered by API tests | Working for recorded audit events, not all conversation/Git/project history |
| Models | `/models` (Ollama tags/ps/show, Droid choices) | loading/empty/error; unreachable sources labelled | API failure and Retry recovery tested; expandable metadata | Read-only catalog working; unknown cloud limits/pricing labelled |
| Infrastructure: Health, Resources, Logs, Setup guides | health, usage, summary, `/system/logs`, existing runbooks | existing resource/guide states retained; log loading/empty/error | All four sections rendered in both themes/three widths; guide execution not repeated | Working read-only probes and existing guided controls; remote resources not provisioned |
| Costs | `/usage/model-calls?since=...`, daily totals | loading/empty/error | Month/all-time selector, separate local/cloud records | Recorded usage working; budgets, dollar billing and project totals deferred |
| Settings | `/settings` and browser theme storage | loading/empty/error with Retry | Search, theme change and persistence, failure/Retry recovery tested | Backend read-only by choice; only Appearance saves |

## Validation evidence

- `npm run build`: passed, lazy page chunks generated.
- `backend/.venv/Scripts/python -m pytest -q`: **78 passed**. One existing FastAPI/Starlette TestClient deprecation warning.
- `backend/.venv/Scripts/python scripts/check-dashboard.py`: **10 browser checks passed**. This starts a temporary backend on port 8766 with the existing fake Droid session. It exercises real HTTP, storage and SSE without paid inference or executing file changes.
- `backend/.venv/Scripts/python scripts/capture-dashboard.py`: real-backend screenshots and axe audit. Optional page arguments retest only affected pages and merge their evidence into `.screens/step10-browser-report.json`.
- axe-core 4.12.1: **0 violations on all 18 pages/sections in both desktop themes**. Models has one incomplete contrast check per theme, not an asserted pass on that element. Other audited sections have no incomplete checks.
- Lighthouse 12.8.2 accessibility: **100** on Overview, Prompt Studio and Settings, exceeding the required 90. Local JSON reports are `.screens/lighthouse-*.json`.
- Export tests cover filters, valid redacted JSON, CSV formula protection and download headers. Settings/log tests cover nested credentials and URL query secrets.
- Screenshots inspected include Prompt Studio dark mobile/light desktop, Agents dark desktop, Models dark desktop and Settings light desktop.

## Not claimed as complete

- No new paid Droid run was used in the final automated suite. Earlier real-Droid approval evidence remains in the stop-B record.
- VS Code ↔ dashboard approval round trip was subsequently exercised during Phase 5; see below.
- Backend Settings save/reset is deliberately absent, not a skipped editable-settings test.
- Notification centre, React diff/rollback, complete product workflows, mobile navigation restriction and the broader responsive pass remain pending in `docs/PENDING.md`. New backend stores and native diff/restore are described below.
- Remote GPU/Docker/AWS operational controls are not asserted to work without a running target. No AWS resources were created. The user requested pushing the pause-point changes.

## Phase 5 evidence and pause

| Surface / feature | API and observed checks | Status |
|---|---|---|
| VS Code Chat | Shared typed client; project/model/profile selection, multiline draft, explicit start confirmation, task queue and SSE result | Exercised in real isolated development host |
| Task continuation | New tracked task attempt using the same strict session | Exercised; backend ownership/cancellation/retry tests pass |
| Changes | Same approval ID; read-only native before/proposed diff, approve once, scoped verified checkpoint restore | Exercised in scratch workspace; unknown post-images cannot be restored |
| Cross-surface approvals | Native approval appears in React History as `user:vscode`; React denial appears in native Chat as interrupted, with Continue guidance | Both directions observed, using test backend |
| Context, prompts and profiles | Persistent APIs and backend tests; native controls implemented | Full interactive pass not completed before pause |
| Native accessibility / light theme / offline recovery | Semantic labels and focus styles implemented | Full pass pending; do not reuse Phase 4 accessibility scores as native evidence |

Backend **111 tests** and shared client **6 tests** passed. Final dashboard build, extension compilation and 0.3.0 packaging passed; the final VSIX measured **25.24 KB**. Native testing used `scripts/serve-vscode-test.py`, `scripts/check-vscode.cjs` and `scripts/vscode-cdp.cjs`, with no paid inference. The CDP helper reaches Electron's nested webview because agent-browser's frame command did not reach that frame; agent-browser handled native snapshots and screenshots.

Native dark screenshots inspected: initial cockpit and native diff; cross-surface outcome was also captured. Local files are under `.screens/phase5-*.png` and are not committed. The complete list of unfinished work and known command/offline-state gaps is in `docs/PENDING.md`.
