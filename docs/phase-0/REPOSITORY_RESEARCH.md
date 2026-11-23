# Repository Research (Phase 0)

Research date: 2026-11-23. Scope: Phase 0 only (discovery, scoring, licences, recommendation). No application code was written and no candidate was installed or run.

Related files: [REPOSITORY_SCORECARD.md](REPOSITORY_SCORECARD.md), [REQUIREMENTS_MATRIX.md](REQUIREMENTS_MATRIX.md), [LICENCE_AND_DEPENDENCY_AUDIT.md](LICENCE_AND_DEPENDENCY_AUDIT.md).

## 1. Method

1. Candidate discovery: GitHub repository search (`gh search repos`), web search for the named projects whose repositories were ambiguous (SideCar, Cezar, Armada), and two curated lists (andyrewlee/awesome-agent-orchestrators, Agent-Analytics/awesome-multi-agent-orchestrators).
2. Metadata: one batched GitHub GraphQL query per 11 repositories. Commit counts use `history(since, until)` on the default branch, so they count commits by committed date, including merge commits. Release date and commit date are reported separately.
3. Source verification: full recursive file trees for the 10 strongest candidates, filtered by keyword; README feature lines; selected docs (`cezar/docs/reference.md`); licence file headers for every `NOASSERTION` licence; contributor counts via the REST API.
4. Not done in Phase 0: installing, running or testing any candidate; security issue triage per repository; code quality review beyond structure. These are Phase 1 entry tasks.

## 2. Candidate metadata (verified 2026-11-23)

"Last ≤ Oct 31" is the most recent default-branch commit on or before 2026-10-31. "Oct" is the number of default-branch commits dated 2026-10-01 to 2026-10-31.

| Repository | Stars | Forks | Licence (SPDX) | Lang | Open / closed issues | Merged PRs | Latest release | Head commit | Oct commits | Aug–Oct commits | Last ≤ Oct 31 | Contributors |
|---|--:|--:|---|---|---|--:|---|---|--:|--:|---|---|
| nedonatelli/sidecar | 9 | 2 | MIT | TS | 34 / 144 | 340 | v0.136.0 (2026-11-09) | 2026-11-22 | 628 | 858 | 2026-10-31 | 6 (1 main author) |
| open-mercato/cezar | 1,137 | 194 | MIT | TS | 177 / 581 | 1,293 | v0.20.0 (2026-11-15) | 2026-11-23 | 353 | 526 | 2026-10-31 | 48 |
| jchristn/Armada | 19 | 7 | MIT | C# | 0 / 0 | 96 | v1.3.0 (2026-11-06) | 2026-11-21 | 1,748 | 2,077 | 2026-10-31 | 5 (1 main author) |
| OpenHands/OpenHands (GUI) | 94,140 | 12,599 | MIT | TS | 664 / 5,052 | 8,659 | v1.43.0 (2026-11-20) | 2026-11-23 | 454 | 883 | 2026-10-31 | n/c |
| OpenHands/software-agent-sdk | 1,421 | 809 | MIT | Python | 371 / n/c | 3,154 | v1.63.1 (2026-11-20) | 2026-11-23 | 297 | n/c | n/c | 100+ |
| cline/cline | 71,843 | 7,950 | Apache-2.0 | TS | 941 / 4,142 | 5,177 | v4.1.27 (2026-11-21) | 2026-11-23 | 227 | 942 | 2026-10-30 | n/c |
| Kilo-Org/kilocode | 28,093 | 3,390 | MIT | TS | 653 / 4,817 | 6,845 | v7.8.32 (2026-11-20) | 2026-11-23 | 1,153 | 5,909 | 2026-10-31 | n/c |
| anomalyco/opencode (was sst/opencode) | 228,740 | 31,092 | MIT | TS | 2,709 / 32,056 | 12,730 | v1.19.6 (2026-11-17) | 2026-11-23 | 2,007 | 5,507 | 2026-10-31 | n/c |
| OrchestratorInc/agent-orchestrator (was ComposioHQ) | 15,044 | 2,067 | Apache-2.0 | TS/Go | 441 / 2,240 | 3,375 | v0.15.4 (2026-11-22) | 2026-11-23 | 661 | 1,724 | 2026-10-31 | n/c |
| awslabs/cli-agent-orchestrator | 1,644 | 352 | Apache-2.0 | Python | 140 / 302 | 810 | v2.5.5 (2026-11-23) | 2026-11-23 | 179 | 331 | 2026-10-30 | n/c |
| aaif-goose/goose (was block/goose) | 56,894 | 6,657 | Apache-2.0 | Rust | 378 / 3,522 | 6,602 | v1.60.2 (2026-11-20) | 2026-11-23 | 152 | 699 | 2026-10-31 | n/c |
| openai/codex | 136,210 | 21,614 | Apache-2.0 | Rust | 28,209 / 13,862 | 14,186 | rust-v0.171.0 (2026-11-20) | 2026-11-23 | 1,282 | 4,140 | 2026-10-31 | n/c |
| BerriAI/litellm | 63,759 | 13,493 | MIT + `enterprise/` | Python | 1,465 / 12,878 | 21,928 | v1.110.2 (2026-11-20) | 2026-11-23 | 2,357 | 13,626 | 2026-10-31 | 100+ |
| langchain-ai/langgraph | 45,306 | 7,830 | MIT | Python | 357 / 1,439 | 4,191 | 1.2.24 (2026-11-20) | 2026-11-20 | 145 | 239 | 2026-10-31 | n/c |
| langgenius/dify | 161,735 | 25,542 | Modified Apache-2.0 | Python | 619 / 19,403 | 16,472 | 1.20.0 (2026-11-18) | 2026-11-23 | 919 | 2,503 | 2026-10-31 | n/c |
| open-webui/open-webui | 159,332 | 23,121 | Open WebUI License (BSD-3 + branding clause) | Svelte | 265 / 11,123 | 5,567 | v0.13.4 (2026-11-17) | 2026-11-17 | 1,252 | 2,312 | 2026-10-31 | n/c |
| Mintplex-Labs/anything-llm | 68,542 | 7,738 | MIT | JS | 325 / 3,955 | 2,000 | v1.20.0 (2026-11-17) | 2026-11-21 | 148 | 356 | 2026-10-30 | n/c |
| ollama/ollama | 187,921 | 19,148 | MIT | Go | 2,668 / 8,998 | 3,823 | v0.40.17 (2026-11-10) | 2026-11-22 | 155 | 369 | 2026-10-31 | n/c |
| langfuse/langfuse | 37,751 | 4,300 | MIT + `ee/` | TS | 333 / 2,982 | 10,281 | v4.84.0 (2026-11-23) | 2026-11-23 | 878 | 2,269 | 2026-10-31 | n/c |
| promptfoo/promptfoo | 27,583 | 2,821 | MIT | TS | 170 / 1,209 | 9,275 | code-scan-action-0.2.3 (2026-11-18) | 2026-11-23 | 476 | 1,194 | 2026-10-31 | n/c |
| Agenta-AI/agenta | 4,931 | 730 | MIT + `ee/` | TS | 197 / 1,744 | 5,126 | v0.131.0 (2026-11-23) | 2026-11-23 | 2,663 | 9,974 | 2026-10-31 | n/c |
| Helicone/helicone | 6,293 | 709 | Apache-2.0 | TS | 66 / 262 | 4,860 | v2025.08.21-1 (2025-08-21) | 2026-11-17 | 5 | 14 | 2026-10-28 | n/c |
| mem0ai/mem0 | 69,371 | 8,250 | Apache-2.0 | Python | 506 / 1,897 | 2,601 | ts-v3.3.1 (2026-09-25) | 2026-11-23 | 11 | 138 | 2026-10-30 | n/c |
| getzep/graphiti | 33,025 | 3,402 | Apache-2.0 | Python | 267 / 399 | 822 | v0.31.2 (2026-10-20) | 2026-11-23 | 55 | 123 | 2026-10-28 | n/c |
| e2b-dev/E2B | 14,979 | 1,183 | Apache-2.0 | Python | 46 / 378 | 1,156 | @e2b/cli@2.24.0 (2026-11-13) | 2026-11-18 | 85 | 237 | 2026-10-30 | n/c |
| nolabs-ai/nono | 5,077 | 340 | Apache-2.0 | Rust | 254 / 743 | 1,114 | v0.82.0 (2026-11-14) | 2026-11-23 | 88 | 304 | 2026-10-30 | n/c |
| portainer/portainer | 38,892 | 2,947 | Zlib | TS | 718 / 5,443 | 4,790 | 2.45.4 (2026-11-18) | 2026-11-22 | 25 | 117 | 2026-10-27 | n/c |
| amir20/dozzle | 15,007 | 658 | MIT | Go | 5 / 1,123 | 3,849 | v11.5.0 (2026-11-19) | 2026-11-23 | 203 | 541 | 2026-10-31 | n/c |
| nicolargo/glances | 34,005 | 1,842 | LGPL-3.0 | Python | 90 / 2,162 | 954 | v4.5.9 (2026-11-07) | 2026-11-23 | 271 | 666 | 2026-10-31 | n/c |
| netdata/netdata | 81,600 | 6,741 | GPL-3.0 | Go | 206 / 8,217 | 13,996 | v2.13.0 (2026-11-19) | 2026-11-23 | 373 | 992 | 2026-10-31 | n/c |
| NVIDIA/dcgm-exporter | 1,937 | 362 | Apache-2.0 | Go | 91 / 320 | 210 | 4.9.0 (2026-11-06) | 2026-11-06 | 0 | 2 | 2026-09-18 | n/c |
| louislam/uptime-kuma | 94,785 | 8,877 | MIT | JS | 738 / 4,368 | 1,986 | 2.5.12 (2026-11-17) | 2026-11-23 | 116 | 242 | 2026-10-31 | n/c |
| coder/coder | 17,461 | 1,683 | AGPL-3.0 | Go | 322 / 7,061 | 19,341 | v2.38.10 (2026-11-16) | 2026-11-23 | 725 | 2,011 | 2026-10-31 | n/c |
| Arize-ai/phoenix | 12,382 | 1,322 | Elastic License 2.0 | Python | 1,107 / 6,100 | 9,037 | arize-phoenix-v22.0.1 (2026-11-21) | 2026-11-23 | 412 | 1,184 | 2026-10-31 | n/c |
| crewAIInc/crewAI | 61,197 | 9,257 | MIT | Python | 452 / 2,543 | 2,630 | 1.15.44 (2026-11-19) | 2026-11-23 | 193 | 413 | 2026-10-29 | n/c |
| continuedev/continue | 36,540 | 5,585 | Apache-2.0 | TS | 269 / 6,497 | 4,078 | v2.0.0-vscode (2026-06-19) | 2026-07-21 | **0** | **0** | 2026-07-21 | n/c |
| TabbyML/tabby | 33,923 | 1,800 | Apache-2.0 + `ee/` | Rust | 261 / 757 | 3,001 | v0.32.0 (2026-01-25) | 2026-06-30 | **0** | **0** | 2026-06-30 | n/c |
| Aider-AI/aider | 50,225 | 5,185 | Apache-2.0 | Python | 1,419 / 3,193 | 288 | v0.86.0 (2025-08-09) | 2026-05-22 | **0** | **0** | 2026-05-22 | n/c |
| SWE-agent/SWE-agent | 20,855 | 2,283 | MIT | Python | 70 / 599 | 640 | v1.1.0 (2025-05-22) | 2026-07-16 | **0** | **0** | 2026-07-16 | n/c |
| RooCodeInc/Roo-Code | 24,238 | 3,444 | Apache-2.0 | TS | archived | 4,326 | v3.54.0 (2026-05-15) | 2026-05-15 | **0** | **0** | 2026-05-15 | n/c |
| BloopAI/vibe-kanban | 28,793 | 3,071 | Apache-2.0 | Rust | 385 / 503 | 1,849 | v0.1.46 (2026-11-15) | 2026-11-15 | 3 | 13 | 2026-10-28 | n/c |
| microsoft/autogen | 61,965 | 9,411 | CC-BY-4.0 / MIT code | Python | archived | 2,540 | python-v0.7.5 (2025-09-30) | 2026-11-12 | 2 | 2 | 2026-10-28 | n/c |
| plandex-ai/plandex | 15,929 | 1,192 | MIT | Go | 45 / 166 | 33 | cli/v2.2.1 (2025-07-16) | 2025-10-03 | **0** | **0** | 2025-10-03 | n/c |
| danielgross/localpilot | 3,329 | 135 | MIT | Python | 20 / 6 | 2 | none | 2023-10-03 | **0** | **0** | 2023-10-03 | n/c |
| FutureStackSolution/LocalPilot | 22 | 7 | MIT | C# | 8 / 11 | 35 | none | 2026-06-14 | **0** | **0** | 2026-06-14 | n/c |

n/c = not collected in Phase 0. Commit counts for repositories with merge-queue bots (LiteLLM, Agenta) are inflated by merge commits.

Freshness findings:
- **No October 2026 commits:** Continue, Tabby, Aider, SWE-agent, Roo Code (archived), Plandex, both "LocalPilot" repositories. Aider's latest release (2025-08-09) is 9 months older than its latest commit (2026-05-22), which shows why release and commit dates must be read separately.
- **Sunsetting or archived:** Vibe Kanban (README: "Vibe Kanban is sunsetting"), Roo Code, AutoGen.
- **Low October activity:** NVIDIA dcgm-exporter (0, last commit 2026-09-18), Helicone (5), mem0 (11).
- OpenHands has split: `OpenHands/OpenHands` is now the TypeScript/Electron GUI ("agent canvas"); the Python agent runtime lives in `OpenHands/software-agent-sdk` (packages `openhands-sdk`, `openhands-tools`, `openhands-workspace`, `openhands-agent-server`).

## 3. Named candidates: identification

| Name in prompt | Resolved repository | Notes |
|---|---|---|
| SideCar | nedonatelli/sidecar | VS Code extension, marketplace id `nedonatelli.sidecar-ai`. Not codestoryai/sidecar (Rust backend for the Aide editor). |
| LocalPilot | danielgross/localpilot; FutureStackSolution/LocalPilot | Neither is a usable foundation (stale macOS proxy; Visual Studio extension inactive since June). Name collision: several unrelated "LocalPilot" repositories exist (JetBrains plugin, WooCommerce plugin, ML research agent). Check trademark/name clashes before publishing. |
| Cezar | open-mercato/cezar | Orchestrator/ADE for Claude Code, Codex, OpenCode, Pi, Cursor, Junie. |
| Armada | jchristn/Armada | Multi-agent coordinator (armadago.ai). Other "armada" repositories are unrelated. |

## 4. Verified findings for the leading candidates

Paths below were seen in the repository tree on 2026-11-23. Existence was verified; behaviour was not executed.

### 4.1 jchristn/Armada (MIT, .NET 10, 7,767 files)
- Components: `src/Armada.Server` (REST + WebSocket + MCP), `src/Armada.Dashboard` (React 19 + Vite), `src/Armada.VSCode` (VS Code extension), `src/Armada.Tui`, `src/Armada.Mobile`, `src/Armada.Helm`, `src/Armada.Harbor` (tray agent that dials out to the server).
- Data: SQLite, PostgreSQL, SQL Server, MySQL implementations under `src/Armada.Core/Database/*`; `migrations/` scripts; `Database/SchemaMigration.cs`.
- Approvals and permissions: `ICliPermissionRequestMethods.cs`, `ICliPermissionRuleMethods.cs`, `Authorization/PermissionLevel.cs`, `AskActionProposalMethods.cs`.
- Memory and prompts: `IMemoryMethods.cs`, `IPromptTemplateMethods.cs`, `scripts/common/prompt-evaluations/`.
- Models: `Services/OllamaTagModel.cs`, `OllamaPsModel.cs`, `docs/CAPTAIN_ROUTING.md`; README lists Ollama, OpenAI-compatible, Anthropic, Gemini, Bedrock and others as managed endpoints.
- Deployment: `docker/armada/compose.yaml`, Grafana/Prometheus/Loki/Tempo observability configs, install scripts for Windows, Linux, WSL, macOS.
- Tests: `src/Test.Nunit`, `src/Test.Xunit`, `src/Test.Automated`, `src/Test.Smoke`.
- Risks: 2,715 of roughly 3,035 contributor commits from one author; 19 stars; v1.3.0 removed fields "with no deprecation period" (README). .NET stack conflicts with the Python backend preference.

### 4.2 OpenHands/software-agent-sdk (MIT, Python, 2,293 files)
- `openhands-agent-server/openhands/agent_server/`: FastAPI-style routers (`acp_router.py`, `agent_profiles_router.py`), `docker_runtime/`, `persistence/store.py`, `_secret_redaction.py`, OpenAI-compatible endpoint (`openai/router.py`, `usage.py`).
- `openhands-sdk/openhands/sdk/security/`: `confirmation_policy.py`, `llm_analyzer.py`, `ensemble.py`, `defense_in_depth/{shell_semantics,policy_rails,pattern}.py`, `grayswan/`.
- `openhands-sdk/openhands/sdk/llm/`: LiteLLM provider layer, `router/` (base, multimodal, random), `_tokenizer.py`, `utils/metrics.py`.
- `openhands-sdk/openhands/sdk/context/condenser/` (LLM-summarising and pipeline condensers), `context/memory.py`, `git/` (diff, changes, commits), `mcp/`, `workspace/` (local, remote, Docker, Apptainer, Kubernetes agent-sandbox).
- `clients/typescript/`: generated TypeScript client for the agent server, including `security/confirmation-policy.ts` and `vscode-client.ts`.
- CI checks REST API breakage and OpenAPI schema quality (`.github/scripts/check_agent_server_rest_api_breakage.py`).
- Gaps: no multi-project control plane, worktree manager, decision records, cost centre or GPU lifecycle.

### 4.3 open-mercato/cezar (MIT, Node 20 / TypeScript, 4,615 files)
- Packages: `cezar` (orchestrator), `contract` (shared types), `api-client`, `web` (React 19 + Vite + Tailwind 4), `desktop` (Tauri), `mobile`.
- Worktrees: `src/git-worktree.ts`, `src/worktree-lifecycle/{coordinator,executor,store,templates}.ts`, settings UI for worktree retention.
- Cockpit: `web/src/routes/dashboard/{costs,cost-visuals,export-menu,automations}.tsx`, `api/dashboard-live.ts`, `routes/manager/manager-approvals.tsx`, `manager-memory.tsx`, `prompt-templates.ts`.
- Agent backends (docs/reference.md): Claude Code (default), Codex, Cursor; OpenCode, pi and Junie marked **experimental**. OpenCode and Junie ignore `allowedTools`; Junie auto-approves every permission; Claude Code permission prompts cannot be answered by Cezar. Local models are reachable only through those experimental backends.
- 48 contributors; Windows, Linux and macOS installers.

### 4.4 nedonatelli/sidecar (MIT, VS Code extension, 1,620 files)
- `src/ollama/` (29+ backend adapters, model catalog), `src/agent/executor/permissionsGate.ts`, `src/agent/shadow/{sandbox,sandboxApproval}.ts` (README: shadow workspace in an ephemeral git worktree), `src/agent/auditLog.ts`, `src/agent/memory/{durableMemory,teamMemory,pinnedMemory}.ts`, `src/config/modelCosts.json`, `src/db/{sqliteProvider,postgresProvider}.ts`, `src/mcpServer/agentServer.ts`.
- README: local-first on Ollama, OS keychain for keys, daily/weekly spend caps, SWE-bench Lite runs on local models (Nov 2026).
- Risk: 6 contributors, single main author.

### 4.5 BerriAI/litellm (MIT outside `enterprise/`)
- `litellm/router.py`; `litellm/router_strategy/{complexity_router, lowest_cost.py, lowest_latency.py, budget_limiter.py, auto_router, tag_based_routing.py, ...}`; `litellm/llms/ollama/`; `litellm/proxy/management_endpoints/budget_management_endpoints.py`.
- Fits LocalPilot's model router and cost controls directly through its OpenAI-compatible proxy API. Enterprise-licensed features under `enterprise/` must not be used without a licence.

### 4.6 Other verified notes
- Cline: tool approval, checkpoints, worktree utilities (`apps/cli/src/utils/worktree.ts`, `apps/vscode/proto/cline/checkpoints.proto`), Ollama runtime in desktop example.
- Kilo Code: saved permission rules (`packages/core/src/permission/saved.ts`), SQLite migrations, max-cost nudge.
- OrchestratorInc/agent-orchestrator: Go backend with git worktree adapter, Docker agent adapter, 260+ SQLite migrations, Electron desktop.
- awslabs/cli-agent-orchestrator: supervisor/specialist model over tmux, MCP-app dashboards; Ollama support not verified (code search was rate-limited).

## 5. Recommended foundation

No candidate meets the 95% target (see REQUIREMENTS_MATRIX.md: best weighted coverage 47%, best verified-only coverage 29%). The choice is therefore about which gaps are cheapest and safest to close.

**Recommendation: Option C, a Python composition with a thin LocalPilot control plane.**

| Layer | Choice | Integration mode |
|---|---|---|
| Control plane (projects, tasks, decisions, approvals, history, cost ledger, layered memory, GPU lifecycle) | New LocalPilot FastAPI + Pydantic + SQLAlchemy/Alembic + SQLite | Build (this is LocalPilot's core value and no candidate provides it in Python) |
| Agent runtime, sandboxing, confirmation and security analysers | OpenHands software-agent-sdk + agent-server | Python dependency + agent-server REST API; no fork |
| Model gateway, routing, budgets, spend logs, Ollama | LiteLLM proxy (MIT core only) | OpenAI-compatible HTTP API |
| Local and remote inference | Ollama (local small models; remote RTX 3090 via SSH tunnel) | HTTP via LiteLLM |
| Web dashboard | New React + TypeScript + Vite + Tailwind + shadcn/ui (Radix) | Build; reuse layout/patterns from Cezar `packages/web` and Armada Dashboard (MIT, with attribution) where code is copied |
| VS Code | Thin LocalPilot extension (sidebar, approvals, native diff, task history, deep links) + SideCar installed side-by-side for inline chat/completion | Build thin client; SideCar not forked |
| Worktrees and checkpoints | Port design of Cezar `worktree-lifecycle` (MIT) onto plain `git` CLI | Adapt |
| Prompt testing/comparison | promptfoo CLI | Subprocess; optional |
| Docker / host / GPU monitoring | Docker SDK for Python, Glances REST API (separate process), `nvidia-smi` over SSH; Dozzle optional for logs | API integration |
| Remote compute (workstation, rented GPU, AWS and other clouds) | LocalPilot `ComputeProvider` interface; static SSH adapter first, then SkyPilot (or dstack) for cloud provisioning; OpenHands `RemoteWorkspace` for agents on the target | Adapters; see [REMOTE_COMPUTE_OPTIONS.md](REMOTE_COMPUTE_OPTIONS.md) |

Why C over A (Armada, highest score 88):
- Meets the stated Python/FastAPI backend preference; Armada is .NET 10.
- Avoids inheriting a 7.7k-file codebase with one main author and breaking changes without deprecation.
- The pieces reused in C are maintained by large communities (OpenHands SDK and LiteLLM each have 100+ contributors).
- The strongest verified capabilities in C (sandboxing, confirmation policy, shell-semantics blocking, prompt-injection analysers, routing strategies, budgets) are the hardest parts to build safely.

Trade-off: C needs more new code than A. The control plane, dashboard and VS Code client are new builds. If time-to-first-working-product matters more than the Python preference, Option A (Armada as foundation + LiteLLM in front of its API captains) is the faster path.

What not to reuse:
- Open WebUI as a rebranded base (licence clause 4 forbids removing its branding beyond small deployments).
- Dify as a base (multi-tenant and logo restrictions; not a coding environment).
- Arize Phoenix (Elastic License 2.0), Coder (AGPL-3.0) and any `ee/` or `enterprise/` directories.
- Inactive projects (Continue, Tabby, Aider, SWE-agent, Roo Code, Plandex, Vibe Kanban).
- mem0/graphiti until semantic memory shows measurable benefit (prompt.md §7).

## 6. Integration plan (input to Phase 1, not started)

1. Phase 1 entry spikes (each with a pass/fail result recorded in REQUIREMENTS_MATRIX.md "Test evidence"):
   - Run LiteLLM proxy on Windows against a local small Ollama model; confirm spend logging and a budget block.
   - Run OpenHands agent-server with a Docker workspace on Windows (Docker Desktop/WSL2) using the LiteLLM endpoint; confirm confirmation-policy pauses before a file write.
   - Measure idle RAM of LiteLLM + agent-server + Ollama small model on the 16 GB machine.
2. Define LocalPilot interfaces before code: `ModelGateway`, `AgentRuntime`, `ApprovalGate`, `WorkspaceManager`, `CostLedger`, `InfraProbe`.
3. Store application data under `E:\LocalPilot\data` (DB, logs, indexes), per prompt.md §3.

## 7. Preliminary GPU rental notes (to be finalised in INFRASTRUCTURE.md)

| Provider | RTX 3090 rate | Storage | Source (read 2026-11-23) |
|---|---|---|---|
| RunPod Community Cloud | ~$0.22/hr | Network volume $0.07/GB/mo (survives termination, tied to one data centre); volume disk $0.10/GB/mo running, $0.20 stopped | runpod.io/pricing (storage lines); hackceleration.com summary (GPU rate) |
| RunPod Secure Cloud | ~$0.50/hr | same | hackceleration.com summary |
| Vast.ai | from $0.143/hr (1×3090, on-demand) | billed while stopped (host-set) | computeprices.com, 2026-11-23 |

Illustrative budget only: ₹2,500 at an assumed ₹88 per USD is about $28. With a 100 GB RunPod network volume ($7/mo), about $21 remains, roughly 95 GPU-hours on Community Cloud. Exchange rate, GST on imported services, card fees and minimum top-ups were **not** verified and must be checked before choosing a provider.
