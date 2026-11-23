# Repository Scorecard (Phase 0)

Research date: 2026-11-23. Weights follow prompt.md §2. Scores are analyst judgement against LocalPilot requirements, based on the evidence in REPOSITORY_RESEARCH.md (GitHub GraphQL metadata, repository trees, READMEs and docs, selective source paths). No candidate was installed or run in Phase 0, so scores reflect capability present in source, not tested behaviour.

Maintenance scores are capped at 1 for repositories with **zero default-branch commits in October 2026**, and Security/Arch are reduced where a licence or design limits reuse.

| Rank | Repository | Role | Core (20) | Arch (15) | Agents (10) | Models/Ollama (10) | Memory (10) | Git/Exec (10) | UI (10) | Docker/Linux (5) | Maint (5) | Security (5) | **Total** | Notes |
|---:|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 1 | jchristn/Armada | Foundation | 18 | 12 | 10 | 8 | 9 | 9 | 9 | 5 | 3 | 5 | **88** | Broadest feature set (worktrees, approvals, memory, prompt templates, Ollama endpoints, multi-DB, dashboard, VS Code ext, TUI, mobile). .NET 10, not Python. ~89% of commits from one author, 5 contributors, 19 stars. |
| 2 | OpenHands/software-agent-sdk (+ agent-server, OpenHands GUI) | Foundation (agent runtime) | 15 | 14 | 7 | 9 | 6 | 7 | 8 | 5 | 5 | 5 | **81** | Python SDK + FastAPI agent server, typed OpenAPI with breakage CI, confirmation policy, layered security analyzers, Docker workspaces, LiteLLM-based model layer, condenser. No multi-project control plane, no worktree manager. |
| 3 | open-mercato/cezar | Foundation | 16 | 12 | 9 | 5 | 7 | 10 | 9 | 3 | 5 | 3 | **79** | Strong cockpit: worktree lifecycle, queue, workflows, costs dashboard, memory, prompt templates, multi-project. Node 20/TS. Drives external agent CLIs; local models only through experimental OpenCode/pi backends; some backends bypass tool allowlists. |
| 4 | OrchestratorInc/agent-orchestrator | Foundation | 14 | 12 | 9 | 5 | 6 | 9 | 8 | 4 | 5 | 3 | **75** | Go backend + Electron desktop, SQLite with 260+ migrations, git worktree adapter, Docker agent adapter. Desktop-first, Ollama support not verified. |
| 5 | nedonatelli/sidecar | VS Code client | 13 | 9 | 6 | 10 | 8 | 7 | 6 | 1 | 3 | 5 | **68** | Ollama-first VS Code agent: permissions gate, shadow worktree sandbox, audit log, durable memory, spend caps, SQLite/Postgres providers. VS Code-only; 6 contributors. |
| 6 | cline/cline | VS Code client | 12 | 10 | 6 | 9 | 5 | 7 | 7 | 1 | 5 | 4 | **66** | Mature VS Code agent with tool approval, checkpoints, worktree util, CLI and hub. Large Apache-2.0 codebase. |
| 7 | Kilo-Org/kilocode | VS Code client | 12 | 10 | 6 | 9 | 5 | 6 | 7 | 2 | 5 | 4 | **66** | VS Code/JetBrains/CLI agent with saved permission rules, SQLite migrations, cost nudges. MIT. |
| 8 | langgenius/dify | Platform | 8 | 11 | 6 | 9 | 7 | 1 | 9 | 5 | 5 | 4 | **65** | Workflow/RAG platform. Modified Apache licence forbids multi-tenant use and logo removal. Not a coding environment. |
| 9 | anomalyco/opencode | Agent | 11 | 11 | 6 | 10 | 5 | 5 | 6 | 2 | 5 | 4 | **65** | Very active terminal coding agent with server mode; usable as a worker via Cezar or directly. Scored from metadata + Cezar integration docs only. |
| 10 | aaif-goose/goose | Agent | 10 | 11 | 6 | 9 | 5 | 4 | 6 | 2 | 5 | 4 | **62** | Rust agent (desktop + CLI), Apache-2.0, active. Scored from metadata only. |
| 11 | open-webui/open-webui | Chat UI | 8 | 9 | 4 | 10 | 6 | 1 | 9 | 5 | 5 | 4 | **61** | Best Ollama chat UI, but custom licence clause 4 restricts removing Open WebUI branding. Not suitable as a rebranded foundation. |
| 12 | Mintplex-Labs/anything-llm | Chat/RAG | 7 | 9 | 5 | 9 | 7 | 1 | 8 | 5 | 5 | 3 | **59** | All-in-one RAG chat with Ollama; little coding/git capability. |
| 13 | awslabs/cli-agent-orchestrator | Orchestrator | 10 | 11 | 9 | 4 | 4 | 4 | 5 | 3 | 5 | 3 | **58** | Python supervisor/specialist orchestration of CLI agents over tmux, MCP apps dashboard. Ollama support not verified (code search rate-limited). |
| 14 | langchain-ai/langgraph | Library | 6 | 13 | 8 | 6 | 6 | 0 | 2 | 3 | 5 | 3 | **52** | Graph-based agent orchestration with interrupts/checkpointers. Useful only if a custom planner graph is needed. |
| 15 | continuedev/continue | VS Code client | 9 | 10 | 3 | 9 | 5 | 3 | 6 | 1 | 1 | 3 | **50** | Last commit 2026-07-21; no commits in Oct 2026. |
| 16 | BerriAI/litellm | Component (gateway) | 6 | 13 | 0 | 10 | 0 | 0 | 5 | 5 | 5 | 4 | **48** | Not a foundation; best-in-class model gateway: routing strategies, budgets, spend tracking, Ollama. |
| 17 | TabbyML/tabby | Completion server | 7 | 10 | 1 | 7 | 6 | 2 | 6 | 5 | 1 | 3 | **48** | Last commit 2026-06-30; no commits in Oct 2026. |
| 18 | Aider-AI/aider | Agent | 8 | 8 | 2 | 9 | 4 | 8 | 3 | 2 | 1 | 2 | **47** | Last commit 2026-05-22; latest release 2025-08-09. |
| 19 | SWE-agent/SWE-agent | Agent | 6 | 9 | 3 | 7 | 3 | 6 | 2 | 4 | 1 | 4 | **45** | Last commit 2026-07-16; latest release 2025-05-22. |

## Excluded before scoring

| Repository | Reason (verified 2026-11-23) |
|---|---|
| RooCodeInc/Roo-Code | Archived; last commit 2026-05-15 |
| BloopAI/vibe-kanban | README states "Vibe Kanban is sunsetting"; 3 commits in Oct 2026 |
| microsoft/autogen | Archived |
| plandex-ai/plandex | Last commit 2025-10-03 |
| danielgross/localpilot | Last commit 2023-10-03 (macOS menu-bar proxy only) |
| FutureStackSolution/LocalPilot | Visual Studio (not VS Code) extension, last commit 2026-06-14 |
| codestoryai/sidecar | Different project (Rust "AI brains" for Aide editor); the requested SideCar is nedonatelli/sidecar |
| "Armada" name collisions | rguiu/armada, coderage-labs/armada, rafmacalaba/armada, armadasvc/armada: not the agent orchestrator at armadago.ai; jchristn/Armada is the canonical repo (developervariety/Armada is a contributor fork) |

## Reading the scores

- Armada scores highest on breadth, but its maintenance score reflects bus-factor risk (one author, 5 contributors), and it does not meet the Python backend preference.
- OpenHands Agent SDK scores highest on architecture and security, and is the only top candidate in Python, but lacks the multi-project control plane.
- Cezar has the best-verified worktree and cost-dashboard code, but local-model support is experimental and depends on third-party CLIs.
- Stars were recorded but not used as a scoring input.
