# Pending work from earlier phases

Last updated: 2026-11-24. Status codes: **Not started**, **Partial** (some code, gaps listed), **Built, not verified** (code exists, never exercised for real), **Blocked** (waiting on you or an outside party).

Phase 4 (UI) work that depends on an item here shows that screen as "unavailable" until the item is done. No fake data.

## Phase 0: repository discovery

| Item | Status | Notes |
|---|---|---|
| ARCHITECTURE.md | Not started | Required deliverable in prompt.md §13 |
| DATABASE_SCHEMA.md | Not started | Tables exist: runbook_runs, step_runs, audit_events, model_calls, usage_snapshots, agent_runs, agent_events, approvals |
| SECURITY.md | Not started | Rules live in code (`policy.py`, `main.py` guards, `agents/droid.py`) but are not written down |
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
| VS Code extension UI driven interactively (status bar, tree views, commands) | Built, not verified | Installed (0.2.0); only packaging and install were checked |
| LiteLLM install/start scripts | Built, not verified | `deploy/litellm/`; never run |
| Docker features | Not started | Docker engine is stopped on this laptop; only the health check exists |
| Small-model summary: non-numeric claims | Partial | Only invented numbers are rejected |
| Backup and restore of `E:\LocalPilot\data` | Not started | |

## Phase 2: core intelligence

| Item | Status | Notes |
|---|---|---|
| Project registration (multiple isolated projects) | Not started | Only one repo; agent folders come from `LOCALPILOT_AGENT_WORKSPACES` |
| Project memory / knowledge (layered, with source hashes and commit references) | Not started | |
| Context engine | Not started | |
| Task management | Not started | No tasks table or API |
| Prompt management (templates, versions, history) | Not started | Needed by Prompt Studio |
| Model router (cache, then rules, then local, remote, cloud) | Not started | The usage summarizer has its own small fixed route |
| Model registry (context size, VRAM, capabilities, pricing, assignment) | Partial | `/agents/models` lists Droid models (local or cloud); `config/pricing.yaml` has AWS prices |
| Budgets (per task, project, month), cost estimate before expensive actions | Not started | Credits and tokens are recorded per Droid run; `/usage/model-calls` does not return credits yet |
| Response cache / duplicate request detection | Partial | Summarizer cache only |

## Phase 3: agent operations

| Item | Status | Notes |
|---|---|---|
| Agent registry (roles, instructions, enable/disable) | Not started | Droid is the only agent and is fixed in code |
| OpenHands agent-server integration | Not started | Planned in Phase 0 option C |
| Approval workflow | Partial | Droid permission requests and runbook steps are approved. There is no diff view, rollback or "request explanation", and runbook approvals are not in the `approvals` table |
| Decisions (architecture, model, dependency, budget) | Not started | No decisions table |
| Git checkpoints, worktrees, rollback before agent writes | Not started | Droid writes go straight into the folder after approval |
| Agent history | Partial | Runs, events and usage are stored; no retry or reassign |
| Clarifying questions from Droid | Not started | They are cancelled with a note |
| Local agent model that is practical | Blocked | qwen2.5-coder 7B on the CPU took about 25 minutes per turn and wrote tool calls as text. Needs a GPU (AWS) and a model with reliable tool calling |
| Shared typed API client for web and VS Code (`packages/shared-types`, `api-client`) | Not started | Both clients have their own hand-written types today |
