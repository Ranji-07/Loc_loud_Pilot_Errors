# Pending work from earlier phases

Last updated: 2026-11-24. **Work paused at your request during Phase 5.** Status codes: **Verified** (specified scope passed checks), **Not started**, **Partial** (some code, gaps listed), **Built, not verified** (code exists, remaining checks listed), **Blocked** (waiting on you or an outside party).

Phase 4 (UI) work that depends on an item here shows that screen as "unavailable" until the item is done. No fake data.

## Phase 0: repository discovery

| Item | Status | Notes |
|---|---|---|
| ARCHITECTURE.md | Partial | Local baseline draft exists; excluded from this push by the current `docs` ignore rule. Later subsystems still need designs |
| DATABASE_SCHEMA.md | Partial | Local draft covers old/new tables but is ignored; committed migrations remain the source of truth |
| SECURITY.md | Partial | Local draft describes guards/consent/checkpoints but is ignored; complete sandbox/remote security remains pending |
| AGENT_PROTOCOL.md | Partial | `docs/DROID_AGENT.md` covers Droid only |
| MODEL_ROUTING.md | Not started | Depends on the Phase 2 router |
| UI_UX_SPECIFICATION.md | Partial | `prompt-ui-ux.md` is the spec; Phase 4 DESIGN_SYSTEM.md will cover it |
| INFRASTRUCTURE.md | Partial | `docs/phase-0/REMOTE_COMPUTE_OPTIONS.md` and `deploy/aws/` |
| DEVELOPMENT_ROADMAP.md | Partial | The "Next phases" table in `docs/phase-1/PHASE_1_STATUS.md` |
| Requirements matrix with LocalPilot coverage | Partial | The matrix still says 0 of 52 implemented; it needs re-scoring against the code built so far |

## Phase 1: foundation

| Item | Status | Notes |
|---|---|---|
| AWS kit against real AWS (launch, user-data, tunnel, remote probes, idle shutdown, stop/start/terminate) | Blocked | You chose to create no AWS resources yet. GPU quota is 0 in all six regions checked; no quota request has been submitted |
| Remote usage path (remote Ollama, GPU metrics) | Blocked | Needs a running remote machine |
| VS Code extension UI driven interactively (status bar, tree views, commands) | Partial | 0.3.0 development host exercised in an isolated profile; Chat, task runs, continuation, native diff/approval/rollback and cross-surface denial verified. Remaining views/commands listed below; user-installed extension remains 0.2.0 |
| LiteLLM install/start scripts | Built, not verified | `deploy/litellm/`; never run |
| Docker features | Not started | Docker engine is stopped on this laptop; only the health check exists |
| Small-model summary: non-numeric claims | Partial | Only invented numbers are rejected |
| Backup and restore of `E:\LocalPilot\data` | Not started | |

## Phase 2: core intelligence

| Item | Status | Notes |
|---|---|---|
| Project registration (multiple isolated projects) | Partial | Persistent registration, allowed-root checks and revision-safe edits tested. Native registration exercised; React project management is still deferred |
| Project memory / knowledge (layered, with source hashes and commit references) | Partial | Project instructions/architecture, file references and memory/decision notes persist with hashes and commit references. Global memory, richer task/agent memory, stale-commit presentation and React Knowledge remain pending |
| Context engine | Partial | Explicit bounded selection, project isolation, stale file hashes and secret redaction tested. Full native attachment/inclusion/editor UI pass, indexing and semantic retrieval remain pending |
| Task management | Partial | Persistent drafts/queue/attempts, project serialization, explicit start consent, cancellation, retry and owned continuation tested. Native run/Continue exercised; native assignment/cancellation/older-history UI and React Tasks still need validation/integration |
| Prompt management (templates, versions, history) | Partial | Project-scoped immutable prompt versions and variable rendering/guards tested. Native Save/Use prompt UI not exercised before pause; React save/templates/context/compare still deferred |
| Model router (cache, then rules, then local, remote, cloud) | Not started | The usage summarizer has its own small fixed route |
| Model registry (context size, VRAM, capabilities, pricing, assignment) | Partial | `/models` reads local/remote Ollama metadata, loaded memory, configured assignments and Droid choices. Cloud limits/prices and automatic routing remain unknown; `config/pricing.yaml` has AWS estimates |
| Budgets (per task, project, month), cost estimate before expensive actions | Partial | Credits, tokens, monthly and daily totals are recorded. Prompt Studio shows a rough prompt token count and a historical credit average, not a cost quote. Budget enforcement, dollar billing and project attribution are not built |
| Response cache / duplicate request detection | Partial | Summarizer cache only |

## Phase 3: agent operations

| Item | Status | Notes |
|---|---|---|
| Agent registry (roles, instructions, enable/disable) | Partial | Named Droid adapter profiles, instructions, model assignment and enable state persist and have backend tests. Native create/edit/toggle/assignment UI not yet exercised; additional adapters and collaboration/handoffs pending |
| OpenHands agent-server integration | Not started | Planned in Phase 0 option C |
| Approval workflow | Partial | Shared approve-once/deny records, native read-only diff and both surface outcomes verified. Explanation/modify/defer, unified runbook approvals and native offline-vs-empty approval presentation remain pending |
| Decisions (architecture, model, dependency, budget) | Partial | Project context can store decision notes; this is not an engineering decision workflow with alternatives, approval state or costs. That workflow and React screen remain unbuilt |
| Git checkpoints, worktrees, rollback before agent writes | Partial | Scoped original-byte checkpoints, dirty/ignored Git target guard, junction retarget guard, successful-tool/post-image verification and safe rollback tested. Native restore exercised in a scratch workspace. No Git history/index reset. Worktrees, arbitrary command rollback, rename/unknown post-image support and full isolation remain pending |
| Agent history | Partial | Runs/events/usage and task attempts persist. Retry uses a fresh run; Continue remains a tracked same-project strict session. Backend reassignment tested; complete native UI/history and React task integration pending |
| Clarifying questions from Droid | Not started | They are cancelled with a note |
| Local agent model that is practical | Blocked | qwen2.5-coder 7B on the CPU took about 25 minutes per turn and wrote tool calls as text. Needs a GPU (AWS) and a model with reliable tool calling |
| Shared typed API client for web and VS Code (`packages/shared-types`, `api-client`) | Verified | Both import shared types/client; six client tests cover loopback URLs, request sharing, retry/errors, health cache, split SSE and preview-bound consent |

## Phase 4: approved dashboard scope

- Steps 5–10 originally used existing APIs and small read-only additions. Phase 5 approval expanded backend scope; Projects, Tasks and Knowledge now have backend foundations but their React management screens are still unavailable.
- Backend Settings is read-only by your choice. Only browser Appearance can be saved.
- History has cursor paging, filters and redacted CSV/JSON exports (newest 10,000 matches). It covers recorded audit events, not a complete conversation/Git/project timeline.
- React diff/rollback controls, explanation requests and notifications remain pending. Native VS Code diff/verified checkpoint restore and the shared client are now implemented.
- Mobile currently supports responsive views of all pages; limiting mobile navigation to the four daily-use pages is still pending.
- Stop point C was approved, followed by Phase 5 and the missing backends. AWS resources remain uncreated. You subsequently requested documenting pending work, pushing current changes, and stopping.

## Phase 5: pause point and next work

Verified before pause:
- Backend: **111 tests passed**, with one existing Starlette TestClient deprecation warning.
- Shared client: **6 tests passed**. Final dashboard build and extension compilation/packaging passed; final 0.3.0 VSIX is **25.24 KB**, kept local by the VSIX ignore rule.
- Real isolated VS Code development host: multiline draft saves without inference; explicit model/location/token confirmation; strict queued run/SSE; tracked Continue; readable native proposed diff; approve once and verified file restore.
- VS Code approve → React History shows `user:vscode`. React Deny → native Chat becomes `interrupted` with Continue guidance; React approval history shows `user:dashboard`. These use a clearly labelled test double, not paid inference.
- Independent backend safety review found six issues. Regression tests now cover unverified post-images, junction retargeting, model-location changes at dispatch, quoted JSON credentials, partial rollback recovery and ignored Git files.

Remaining before declaring Phase 5 complete:
1. Exercise native saved prompt/version selection, context attachments/check boxes/editors, agent create/edit/toggle, task assignment/cancellation/older-history and code-selection review.
2. Fix command-palette entry points that currently assume a tree-item argument. Show an honest offline approval state rather than an empty pending list. The proposed patch for these was interrupted and was **not applied**.
3. Broaden native dark/light/high-contrast, keyboard, accessibility and error/recovery checks. Initial dark screenshots were inspected; a full native light/accessibility pass is pending.
4. Rerun the existing ten dashboard browser regressions after the shared-client/approval changes. Phase 4 screenshots, axe and Lighthouse evidence remain historical, not a new Phase 5 full pass.
5. Update React unavailable explanations and connect the new project/task/context/prompt/profile backends when that dashboard scope resumes.
6. Install the final packaged 0.3.0 extension in the user's regular VS Code profile only when requested; current verification used an isolated development host.
7. Update the extension README/protocol docs and decide whether to publish the currently ignored architecture/schema/security drafts.

Local evidence (not committed): `.screens/phase5-vscode-report.json`, native dark screenshots and `.screens/phase5-cross-surface-dark.png`. The automated native report ends with a pending dashboard decision; that decision was subsequently exercised manually and its observed result is recorded above.

No work should resume automatically after this pause. Starting queued work after a backend restart requires a fresh explicit start.
