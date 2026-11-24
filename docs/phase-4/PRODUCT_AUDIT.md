# Product audit (Phase 4, step 1)

Date: 2026-11-24. "Verified" means exercised against the running backend or by tests, not just present in code. Evidence: 68 backend tests passing; dashboard checked in headless Chrome (Phase 1 pages, and today the Droid agent page with deny, approve and continue on Haiku 4.5); VS Code extension built and installed only.

## Existing components

| Component | Exists? | Actually works? (verified) | Quality | Reuse / change / remove |
|---|---|---|---|---|
| FastAPI backend, local-only guards (host, origin, client header) | Yes | Yes (tests) | Good | Reuse unchanged |
| SQLite + Alembic (0001, 0002) | Yes | Yes (tests, live) | Good | Reuse; add tables only when a screen needs them |
| Health checks `/health` (11 checks, incl. Droid) | Yes | Yes (live) | Good | Reuse for Overview and Infrastructure |
| Runbook engine (approve, modify, stop, skip, verify, SSE) | Yes | Yes (tests, browser) | Good | Reuse; it becomes the "Setup" part of Infrastructure |
| Command policy | Yes | Yes (tests) | Good | Reuse |
| Usage probes `/usage`, summary, `/usage/model-calls` | Yes | Yes (live). `model-calls` omits Factory credits | Fair | Reuse for Costs and Infrastructure; add credits to `model-calls` |
| Audit log `/audit` | Yes | Yes | Fair (no filters, no paging) | Reuse as the first source for History; add filters and paging |
| Droid agent service, `/agents/*`, `/approvals/*` | Yes | Yes (tests, browser with a cloud model). Local model works but is impractical on the CPU | Good | Reuse for Agents, Tasks (runs) and Approvals |
| Dashboard shell (sidebar with 5 flat links, hash routing) | Yes | Yes | Basic: no groups, no themes, no command palette | Change: replace with the grouped shell from the spec |
| Dashboard styling | Tailwind 4, hard-coded slate/sky/emerald/amber/rose classes | Yes | No tokens, dark only | Change: move to CSS variables using your `colour.md`; add a light theme |
| Overview page | Yes (health cards) | Yes | Fair | Change: show only the spec items that have real data |
| Setup guide page | Yes | Yes | Good | Keep; move under Infrastructure |
| Usage page | Yes | Yes | Fair | Split into Infrastructure (machine and GPU) and Costs (model calls, credits, AWS) |
| Audit log page | Yes | Yes | Basic | Becomes History |
| Droid agent page | Yes | Yes (browser) | Fair, minimal | Becomes Agents (run list and detail) plus Approvals |
| VS Code extension 0.2.0 (status bar, health, guides, usage, Ask Droid, pending approvals) | Yes | Built and installed. UI not driven | Fair | Reuse; reshape to Chat, Tasks, Agents, Changes, Context in Phase 5 |
| Shared typed API client | No | n/a | n/a | Add `packages/api-client` (types plus fetch wrapper) used by web and VS Code |
| UI component library | None (custom `ui.tsx` with Badge and ErrorBox) | n/a | n/a | Add shadcn/ui on Radix (spec default); one icon set (lucide) |

## Spec screens against available backend data

| Screen | Backend today | Can be built for real now? |
|---|---|---|
| Overview | health, usage, agent runs, pending approvals, audit | Yes (no monthly spend in rupees yet: only AWS cost-so-far and Factory credits) |
| Projects | none | No. Show as unavailable (needs Phase 2 project registration) |
| Agents | Droid runs, models, events, stop, continue | Partly: one agent (Droid). No registry, retry or reassign |
| Tasks | none (agent runs are the closest) | No. Unavailable, or list agent runs labelled as runs |
| Prompt Studio | none | No. Needs prompt templates and versions (Phase 2) |
| Decisions / Approvals | approvals table (Droid only), runbook step approvals | Approvals tab yes; Decisions tab unavailable |
| Knowledge | none | No |
| History | audit events, agent runs | Yes, from the audit log (filters and paging need small endpoint changes) |
| Models | Droid model list, Ollama tags, small model | Yes, read-only (no routing rules yet) |
| Infrastructure | health, usage, runbooks, AWS state | Yes; actions through the existing runbooks |
| Costs | model calls, credits, AWS cost-so-far, pricing.yaml | Partly: actuals only, no budgets |
| Settings | settings come from env/.env only; no API | Read-only view possible with one new GET endpoint; saving needs a design decision |

Pending backend work behind the "No" rows is listed in [docs/PENDING.md](../PENDING.md).

## Proposed build (after your approval at stop point A)

1. Tokens and themes from your `colour.md` (dark default, light, system) as CSS variables.
2. App shell: grouped sidebar (WORKSPACE, INTELLIGENCE, OPERATIONS, SYSTEM), command palette (Ctrl+K), system status.
3. Shared components with loading, empty and error states.
4. Overview against the real backend. Then **stop point B** with screenshots in both themes.

Screens without a backend appear in the sidebar with an honest "Not available yet: needs …" state, not fake data.

Small backend additions this needs (each with tests): credits in `/usage/model-calls`, filters and paging on `/audit`, and a read-only `/settings` that never returns secrets.
