# Requirements Matrix (Phase 0)

Research date: 2026-11-23. LocalPilot itself has **no code yet**, so LocalPilot implementation coverage is **0 of 52 (0%)**. The columns below measure what each candidate foundation already provides upstream.

## Evidence legend

| Code | Meaning | Weight in coverage |
|---|---|---:|
| V | Verified: matching source files found in the repository tree on 2026-11-23 (paths listed). Existence of files was checked, behaviour was **not** executed. | 1.0 |
| P | Partial: source exists but covers only part of the requirement | 0.5 |
| R | README/docs claim only, not checked in source | 0.5 |
| G | Gap: not found | 0 |

No requirement is marked as tested, because no candidate was installed or run in Phase 0. "Test evidence" therefore stays empty until Phase 1.

## Coverage summary

| Foundation option | Verified only (V) | Weighted (V + 0.5×P/R) |
|---|---:|---:|
| A. Armada (.NET) | 10/52 (19%) | 24.5/52 (47%) |
| B. Cezar (Node/TS) | 12/52 (23%) | 20/52 (38%) |
| C. Python composition: OpenHands Agent SDK + LiteLLM | 15/52 (29%) | 21.5/52 (41%) |

**Finding:** no single repository or realistic combination reaches 95% verified coverage. The 95% target is not achievable through reuse alone; the gaps (GPU lifecycle, decision records, layered memory with staleness checks, prompt versioning, Docker/GPU management, cost estimates) must be built or covered by add-on components (see REPOSITORY_RESEARCH.md §6).

## Matrix

| # | Requirement | A. Armada | B. Cezar | C. OpenHands SDK + LiteLLM | Evidence (paths are relative to each repository) | Test evidence | Remaining work for LocalPilot |
|---:|---|:-:|:-:|:-:|---|---|---|
| 1 | Multiple isolated projects | R | V | G | Cezar: packages/web/src/lib/project-router.tsx; Armada: README "vessels" | none yet | Build in LocalPilot control plane or add-on (option C) |
| 2 | Project memory | P | V | P | Cezar: managers/memory.ts, routes/manager/manager-memory.tsx; Armada: Database/Interfaces/IMemoryMethods.cs; SDK: sdk/context/memory.py | none yet | Verify, then extend (option C) |
| 3 | Layered memory (global/project/task/agent) with source hashes + commit refs | P | G | G | Armada README claims episodic/semantic/procedural memory; hash/commit staleness checks not found anywhere | none yet | Build in LocalPilot control plane or add-on (option C) |
| 4 | Task queue and task management | R | R | G | Both READMEs describe queues; not inspected in source | none yet | Build in LocalPilot control plane or add-on (option C) |
| 5 | Parallel agents with git worktree isolation | R | V | G | Cezar: src/git-worktree.ts, src/worktree-lifecycle/*; Armada README "dock" per mission | none yet | Build in LocalPilot control plane or add-on (option C) |
| 6 | Sequential pipelines and agent handoffs | R | R | G | Armada README Worker->TestEngineer->Judge; Cezar README workflow node graph + child tasks | none yet | Build in LocalPilot control plane or add-on (option C) |
| 7 | Agent cancel / retry / manual reassignment | R | R | G | README claims only | none yet | Build in LocalPilot control plane or add-on (option C) |
| 8 | Agent registry with roles/personas | R | P | P | Armada README personas/captains; SDK: agent_server/agent_profiles_router.py | none yet | Verify, then extend (option C) |
| 9 | Ollama (local and remote) | V | P | V | Armada: Core/Services/OllamaTagModel.cs, OllamaPsModel.cs; LiteLLM: litellm/llms/ollama/; Cezar only via experimental OpenCode/pi backends | none yet | Integrate and test (option C) |
| 10 | Multiple model providers, no lock-in | R | R | V | LiteLLM: 100+ providers (litellm/llms/*); Armada README endpoint list; Cezar docs/reference.md backends | none yet | Integrate and test (option C) |
| 11 | Routing by complexity/cost/latency | P | G | V | LiteLLM: litellm/router_strategy/{complexity_router,lowest_cost.py,lowest_latency.py,budget_limiter.py}; Armada docs/CAPTAIN_ROUTING.md | none yet | Integrate and test (option C) |
| 12 | User override of routing | R | R | R | Model selection per request/task described in docs | none yet | Verify, then extend (option C) |
| 13 | Token accounting (model/agent/task/project) | R | V | P | Cezar: workspace/dashboard-costs.ts, core/claude-session-cost.ts; SDK: llm/utils/metrics.py; per-task attribution needs LocalPilot work | none yet | Verify, then extend (option C) |
| 14 | Budgets (task/project/monthly) | P | R | V | LiteLLM: proxy/management_endpoints/budget_management_endpoints.py; Armada: CaptainSelectionMethods.UsageBudgetReservation.cs | none yet | Integrate and test (option C) |
| 15 | GPU-hour accounting and idle shutdown | G | G | G | Not present in any candidate | none yet | Build in LocalPilot control plane or add-on (option C) |
| 16 | Response cache / duplicate request detection | G | G | R | LiteLLM documents caching; not inspected | none yet | Verify, then extend (option C) |
| 17 | Cost estimate before expensive operations | G | G | G | Not found | none yet | Build in LocalPilot control plane or add-on (option C) |
| 18 | Approval before file writes and commands | V | P | V | Armada: CliPermissionRequestMethods.cs; Cezar: routes/manager/manager-approval.tsx (backend limits: Claude Code prompts cannot be answered, OpenCode/Junie bypass allowedTools); SDK: security/confirmation_policy.py | none yet | Integrate and test (option C) |
| 19 | Diff preview before approval | R | P | P | Cezar: routes/task-git/worktree-files.ts; SDK: git/git_diff.py | none yet | Verify, then extend (option C) |
| 20 | Command allowlist / dangerous command blocks | R | R | V | SDK: security/defense_in_depth/{shell_semantics.py,policy_rails.py}; Cezar bashAllowlist (docs); Armada remembered allow/deny rules (README) | none yet | Integrate and test (option C) |
| 21 | Sandboxed execution (Docker) | G | G | V | SDK: agent_server/docker_runtime/*, workspace/* | none yet | Integrate and test (option C) |
| 22 | Secret protection | R | G | V | SDK: agent_server/_secret_redaction.py; Armada README write-only API keys | none yet | Integrate and test (option C) |
| 23 | Audit log | R | G | G | Armada README Activity timeline | none yet | Build in LocalPilot control plane or add-on (option C) |
| 24 | Prompt-injection protection | G | G | V | SDK: security/llm_analyzer.py, security/grayswan/ | none yet | Integrate and test (option C) |
| 25 | Git status / branches / history | R | V | V | Cezar: workspace/dashboard-forge.ts, routes/task-git/; SDK: sdk/git/{git_changes,git_commits}.py | none yet | Integrate and test (option C) |
| 26 | Checkpoint and rollback | R | R | G | Armada/Cezar: main checkout untouched until landing (README) | none yet | Build in LocalPilot control plane or add-on (option C) |
| 27 | PR preparation / commit message generation | R | R | G | README claims only | none yet | Build in LocalPilot control plane or add-on (option C) |
| 28 | Merge conflict detection | G | G | G | Not verified anywhere | none yet | Build in LocalPilot control plane or add-on (option C) |
| 29 | Prompt templates with variables | V | V | G | Armada: Database/Interfaces/IPromptTemplateMethods.cs; Cezar: web/src/lib/prompt-templates.ts | none yet | Build in LocalPilot control plane or add-on (option C) |
| 30 | Prompt versioning and history | G | G | G | Langfuse (optional add-on) documents this; not part of any foundation | none yet | Build in LocalPilot control plane or add-on (option C) |
| 31 | Prompt testing and comparison | P | G | G | Armada: scripts/common/prompt-evaluations/; promptfoo (add-on) documents this | none yet | Build in LocalPilot control plane or add-on (option C) |
| 32 | Token / context-size estimates | G | G | V | SDK: llm/_tokenizer.py | none yet | Integrate and test (option C) |
| 33 | Decision records (approve/reject/edit/defer) | P | G | G | Armada: AskActionProposalMethods.cs (action proposals, not full decision records) | none yet | Build in LocalPilot control plane or add-on (option C) |
| 34 | Persistent, searchable conversation and task history | R | R | P | SDK: agent_server/persistence/store.py | none yet | Verify, then extend (option C) |
| 35 | History export | G | V | G | Cezar: routes/dashboard/export-menu.tsx | none yet | Build in LocalPilot control plane or add-on (option C) |
| 36 | Recovery after interruption | R | R | R | Documented, not tested in this phase | none yet | Verify, then extend (option C) |
| 37 | React web dashboard | V | V | P | Armada: src/Armada.Dashboard (React 19 + Vite); Cezar: packages/web (React 19 + Vite + Tailwind 4); OpenHands GUI is a conversation UI, not a control centre | none yet | Verify, then extend (option C) |
| 38 | Cost charts | R | V | R | Cezar: routes/dashboard/cost-visuals.tsx; Armada: Grafana dashboards in docker/armada/observability | none yet | Verify, then extend (option C) |
| 39 | Real-time updates | R | V | R | Cezar: web/src/api/dashboard-live.ts | none yet | Verify, then extend (option C) |
| 40 | VS Code extension | V | G | P | Armada: src/Armada.VSCode; SDK ships only vscode_extensions/openhands-settings | none yet | Verify, then extend (option C) |
| 41 | Inline code assistance | G | G | G | None; SideCar/Continue-class extension needed as companion | none yet | Build in LocalPilot control plane or add-on (option C) |
| 42 | Docker deployment templates | V | G | V | Armada: docker/armada/compose.yaml; SDK: agent_server/docker/Dockerfile | none yet | Integrate and test (option C) |
| 43 | Docker container management (status/logs/start/stop) | G | G | G | Dozzle / Docker SDK needed | none yet | Build in LocalPilot control plane or add-on (option C) |
| 44 | Remote Linux server over SSH | P | R | G | Armada Harbor dial-out (README); Cezar remote access docs | none yet | Build in LocalPilot control plane or add-on (option C) |
| 45 | GPU / VRAM monitoring | G | G | G | Glances / nvidia-smi / dcgm-exporter needed | none yet | Build in LocalPilot control plane or add-on (option C) |
| 46 | Ollama status and model inventory | V | G | R | Armada: OllamaPsResponse.cs, OllamaTagsResponse.cs | none yet | Verify, then extend (option C) |
| 47 | Database migrations | V | G | G | Armada: migrations/, Database/SchemaMigration.cs | none yet | Build in LocalPilot control plane or add-on (option C) |
| 48 | SQLite default, PostgreSQL optional | V | G | G | Armada: Database/Sqlite + Database/Postgresql implementations | none yet | Build in LocalPilot control plane or add-on (option C) |
| 49 | Automated tests present | V | V | V | Armada: src/Test.Nunit, Test.Xunit; Cezar: e2e configs; SDK: .agents/skills/verify-sdk + CI workflows | none yet | Integrate and test (option C) |
| 50 | Backup and restore | R | G | G | Armada README pre-migration backups | none yet | Build in LocalPilot control plane or add-on (option C) |
| 51 | Typed, versioned API | R | V | V | Cezar: packages/contract, packages/api-client; SDK: OpenAPI breakage CI (.github/scripts/check_agent_server_rest_api_breakage.py) | none yet | Integrate and test (option C) |
| 52 | Python FastAPI backend (stated preference) | G | G | V | Armada is .NET 10; Cezar is Node 20; OpenHands agent-server is Python | none yet | Integrate and test (option C) |

## Remote compute requirements (added after Phase 0 review, not counted above)

| Requirement | Option C component | Evidence | Remaining work |
|---|---|---|---|
| Agents run on a separate machine, controlled from the laptop | OpenHands `RemoteWorkspace` + agent-server | V (`sdk/workspace/remote/base.py`) | Spike over SSH tunnel |
| Models served from a separate machine | Ollama/vLLM on target, LiteLLM routing on laptop | V (`litellm/llms/ollama/`) | Spike over SSH tunnel |
| Provider-agnostic cloud GPU provisioning (AWS, RunPod, Vast, ...) | SkyPilot or dstack adapter | V (`sky/clouds/*.py`; `dstack/_internal/core/backends/*`) | Choose one; WSL needed for SkyPilot on Windows |
| Idle shutdown of cloud GPU | SkyPilot autostop / dstack `idle_duration` + LocalPilot idle timer | V (`autostopv1.proto`) / R (dstack docs) | RunPod supports terminate only (`sky/clouds/runpod.py`) |
| Static workstation over SSH | LocalPilot static SSH adapter | G | Build |
| GPU-hour ledger per target | LocalPilot | G | Build |

## Add-on components that close option C gaps (not counted above)

| Gap | Add-on | Evidence level |
|---|---|---|
| Prompt versioning, history | Langfuse prompt management (MIT core, `ee/` excluded) or LocalPilot SQLite tables | R |
| Prompt testing and comparison | promptfoo (MIT) CLI | R |
| Docker logs / status | Dozzle (MIT) or Docker SDK for Python | R |
| CPU/RAM/GPU monitoring | Glances REST API (LGPL-3.0, run as a separate process) + `nvidia-smi` | R |
| Inline completion in VS Code | SideCar (MIT) installed side-by-side, pointed at the same Ollama/LiteLLM | V (src/ollama/, src/agent/executor/permissionsGate.ts) |
| Worktree lifecycle | Port the design of Cezar `src/worktree-lifecycle/` (MIT, attribution kept) | V |
