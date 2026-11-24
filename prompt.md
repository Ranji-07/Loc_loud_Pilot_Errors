# LOCALPILOT — MASTER ENGINEERING PROMPT
## Existing GitHub Source Integration + Unified AI Engineering Platform

You are acting as a Principal Software Architect, Senior Full-Stack Engineer, AI Infrastructure Engineer, DevOps Engineer, UX Architect and Open-Source Integration Specialist.

Your responsibility is to build **LocalPilot**, a unified, self-hosted AI engineering environment.

Do not start by creating a new application from scratch.

Your first responsibility is to find, evaluate and reuse the best existing open-source GitHub projects that already solve our requirements.

The objective is to achieve at least **95% functional requirement coverage through existing, reusable and tested components wherever realistically possible**.

Avoid unnecessary development, duplicated functionality, expensive cloud inference and excessive LLM token consumption.

---

# 1. PRODUCT VISION

Product name: LocalPilot

LocalPilot should combine:

- AI coding agents.
- Multiple AI models.
- Local and remote model inference.
- Project-wide memory.
- Context management.
- Architecture and planning.
- Task orchestration.
- Agent collaboration.
- Human approval workflows.
- Git management.
- Code review.
- Documentation.
- Cost monitoring.
- Model management.
- Project management.
- Prompt engineering.
- Engineering history.
- Infrastructure management.

The product should feel like a complete AI engineering operating environment, not merely another chatbot or VS Code extension.

Core principle:

**One workspace. One project memory. Multiple replaceable AI workers. One controlled execution system.**

LocalPilot owns:
- Project context.
- Decisions.
- Task history.
- Permissions.
- Workflows.
- Model selection.
- Agent coordination.
- Cost controls.
- Infrastructure configuration.

Models and agents should be replaceable.

Avoid permanent dependency on any single AI provider.

---

# 2. REPOSITORY RESEARCH — MANDATORY FIRST PHASE

Before writing code, search GitHub extensively.

Research repositories relevant to:

1. AI coding environments.
2. Multi-agent coding systems.
3. VS Code AI extensions.
4. Self-hosted AI assistants.
5. Ollama integrations.
6. Local LLM management.
7. Model routing.
8. Agent orchestration.
9. Project memory.
10. RAG and codebase indexing.
11. Human approval systems.
12. Git worktree management.
13. AI task scheduling.
14. Prompt management.
15. AI engineering dashboards.
16. Docker-based AI deployments.
17. Linux GPU infrastructure management.
18. AI cost tracking.
19. Project documentation generation.
20. Agent execution sandboxes.

Investigate projects such as:

- SideCar.
- LocalPilot.
- Cezar.
- Armada.
- OpenHands.
- Aider.
- Continue.
- Cline.
- Roo Code.
- Open WebUI.
- LiteLLM.
- LangGraph.
- Dify.
- AnythingLLM.
- Tabby.
- SWE-agent.
- Other actively maintained alternatives.

These are research candidates, not mandatory dependencies.

Find additional repositories with stronger implementations.

## GitHub freshness requirement

The research date is November 23, 2026.

Check:
- Latest commit date.
- Commit activity through October 31, 2026.
- Releases.
- Open and closed issues.
- Pull requests.
- Contributor activity.
- Stars and forks.
- Licence.
- Installation complexity.
- Docker support.
- Linux support.
- Windows support.
- Self-hosting support.
- Ollama support.
- API compatibility.
- Security issues.
- Actual code quality.

Do not claim that a repository has October 2026 commits without verifying the commit history.

Do not confuse the latest release date with the latest commit date.

## Repository scoring

Score every serious candidate from 0–100:

| Category | Weight |
|---|---:|
| Core functionality | 20 |
| Architecture and extensibility | 15 |
| Agent management | 10 |
| Model and Ollama integration | 10 |
| Memory and context | 10 |
| Git and code execution | 10 |
| UI and usability | 10 |
| Docker/Linux deployment | 5 |
| Maintenance and community | 5 |
| Security and permissions | 5 |

Create a comparison report.

For every selected repository, identify:

- What can be reused directly.
- What should be integrated through APIs.
- What should be adapted.
- What should not be reused.
- What functionality is missing.
- Licence compatibility.
- Integration risks.
- Dependencies and resource requirements.

Do not copy code without respecting its licence.

Prefer modular integration over merging unrelated codebases.

Do not select a project based on stars alone.

---

# 3. RESOURCE-AWARE AI STRATEGY

This is a critical requirement.

LocalPilot must minimise AI costs by prioritising local inference.

## Available client hardware

Development machine:

- Windows.
- 16 GB RAM.
- AMD integrated graphics.
- No dedicated NVIDIA GPU.

Storage:
- C: approximately 38 GB free.
- D: approximately 20 GB free.
- E: approximately 80 GB free.

Use E: for project files, application data, logs, indexes and local databases.

Do not require large models to run on the Windows development machine.

## Cloud infrastructure budget

Initial cloud GPU budget:

₹2,000–₹3,000 monthly.

Target GPU:
- NVIDIA RTX 3090.
- 24 GB VRAM.
- Linux environment.

GPU rental must be optional.

Do not keep a cloud GPU running continuously.

Use persistent storage where practical so models do not need to be downloaded every time.

Compare actual rental costs, storage charges, bandwidth, taxes and minimum billing requirements before recommending a provider.

## Inference priority

Use this priority:

1. Existing cached results.
2. Deterministic application logic.
3. Local lightweight models, when available.
4. Remote self-hosted Ollama.
5. Free or low-cost external model APIs.
6. Paid premium APIs only when necessary.

Never call an expensive model when a simple programmatic operation can solve the problem.

## Model router

Implement intelligent routing based on:

- Task complexity.
- Required reasoning quality.
- Context length.
- Available VRAM.
- Model availability.
- Response latency.
- Token cost.
- GPU rental cost.
- Privacy classification.
- Task priority.

Examples:

| Task | Preferred execution |
|---|---|
| File classification | Python |
| Simple formatting | Python |
| Basic summarisation | Small local model |
| Prompt classification | Small local model |
| Project exploration | Local/self-hosted model |
| Architecture analysis | Strong reasoning model |
| Complex debugging | Strong coding/reasoning model |
| Large code generation | Remote coding model |
| Security review | Independent reviewer |
| Simple documentation | Local model |
| Critical architectural decision | Strong model + human approval |

Allow the user to override routing.

## Cost controls

Implement:

- Token accounting.
- GPU-hour accounting.
- Per-task budget.
- Per-project budget.
- Monthly budget.
- Model-specific pricing.
- Retry limits.
- Maximum agent iterations.
- Context reuse.
- Cached responses.
- Duplicate request detection.
- Automatic model downgrade for simple tasks.
- Cloud GPU idle shutdown.
- Cost estimates before expensive operations.

Distinguish inference token cost from infrastructure rental cost.

---

# 4. PRODUCT ARCHITECTURE

Build a modular system.

Preferred architecture:

## A. VS Code Extension

Purpose: coding-focused workspace.

Must provide:

- Project chat.
- AI coding agents.
- Task assignment.
- Agent status.
- Code review.
- Context selection.
- Inline code assistance.
- Approval requests.
- File modification previews.
- Git status.
- Task history.
- Terminal integration.
- Project documentation access.

Keep the extension lightweight.

Do not put the complete business logic inside VS Code.

## B. Independent Python Backend

Preferred stack:

- Python.
- FastAPI.
- Pydantic.
- SQLite initially.
- PostgreSQL optionally.
- REST APIs.
- Server-Sent Events or WebSockets.
- Structured logging.
- Background task queue.

The backend must work independently of VS Code.

VS Code is only one client.

## C. React Web Application

This is a major product requirement.

Build a full web dashboard with React and TypeScript.

Suggested stack:
- React.
- TypeScript.
- Vite or Next.js, based on the selected architecture.
- Tailwind CSS.
- A mature accessible component library.
- Responsive layouts.
- Charts for cost and performance.
- Real-time task updates.

The web dashboard should be independently accessible through a browser.

It must not simply duplicate the VS Code sidebar.

It should provide the complete management and decision-making environment.

---

# 5. REACT DASHBOARD — COMPLETE PRODUCT EXPERIENCE

Design this as a professional AI engineering control centre.

The interface should be clean, modern, fast, responsive and easy to navigate.

Avoid unnecessary visual complexity.

## Dashboard sections

### 1. Overview

Display:
- Active projects.
- Running agents.
- Pending approvals.
- Completed tasks.
- Failed tasks.
- Current model.
- GPU status.
- Monthly cost.
- Token usage.
- Recent decisions.
- Recent activity.

### 2. Project Management

Each project should have:

- Project overview.
- Repository connection.
- Project instructions.
- Architecture.
- Requirements.
- Documentation.
- Active tasks.
- Agent history.
- Technical debt.
- Git branches.
- Project memory.
- Project-specific settings.

Allow multiple isolated projects.

### 3. Agent Centre

Display:

- Available agents.
- Agent roles.
- Current tasks.
- Model assignment.
- Execution state.
- Agent logs.
- Token consumption.
- Runtime.
- Errors.
- Completed work.
- Review results.

Support:

- Sequential agents.
- Parallel agents.
- Specialist agents.
- Agent handoffs.
- Agent cancellation.
- Retry.
- Manual reassignment.

### 4. Prompt Studio

This is a high-priority feature.

Build an advanced prompt engineering environment.

Include:

- Prompt editor.
- Prompt templates.
- Variables.
- Context selection.
- System instructions.
- Model selection.
- Agent selection.
- Prompt versioning.
- Prompt history.
- Reusable workflows.
- Token estimates.
- Context size estimates.
- Output format configuration.
- Validation criteria.
- Prompt testing.
- Prompt comparison.
- Prompt optimisation.
- Saved prompt libraries.

Allow users to save successful prompts as reusable templates.

Avoid repeatedly sending huge system prompts.

Use reusable prompt references and compact context packages.

### 5. Decision Centre

A central location for engineering decisions.

Display:

- Proposed architecture changes.
- Model recommendations.
- Agent plans.
- Dependency changes.
- File modification proposals.
- Security warnings.
- Budget warnings.
- User approvals.
- Rejected recommendations.

For every important decision, store:

- Decision ID.
- Project.
- Description.
- Reasoning summary.
- Alternatives.
- Risks.
- Estimated cost.
- Responsible agent.
- Approval status.
- Timestamp.
- Final outcome.

Allow users to approve, reject, edit or defer decisions.

### 6. Approval Centre

Strict approval-based operation initially.

Before file writes or command execution, show:

- Proposed action.
- Files affected.
- Diff preview.
- Commands to execute.
- Potential risks.
- Expected output.
- Rollback option.

Actions:

- Approve.
- Reject.
- Modify.
- Request explanation.

Never execute unapproved destructive operations.

### 7. History Centre

Maintain complete history:

- Conversations.
- Agent runs.
- Tasks.
- Prompt versions.
- Decisions.
- File modifications.
- Git commits.
- Approvals.
- Rejected actions.
- Errors.
- Model usage.
- Cost records.

Provide:
- Search.
- Filters.
- Project selection.
- Date ranges.
- Export.
- Session recovery.

### 8. Model Centre

Manage:

- Ollama servers.
- Local models.
- Remote models.
- API providers.
- Model assignments.
- Model capabilities.
- Context limits.
- Quantisation.
- Availability.
- Performance.
- Pricing.
- Routing rules.

Show which model is being used and why.

### 9. Infrastructure Centre

Manage:

- Windows development environment.
- Linux server.
- Docker containers.
- GPU availability.
- VRAM usage.
- RAM usage.
- CPU.
- Storage.
- Network.
- Ollama status.
- Model storage.
- SSH connection.
- Server uptime.

Provide safe start, stop and health-check workflows.

### 10. Cost Centre

Display:

- Daily expenditure.
- Monthly expenditure.
- Tokens by model.
- Tokens by project.
- GPU hours.
- Cost by agent.
- Cost by task.
- Estimated future expenditure.
- Budget alerts.

Allow monthly spending limits.

### 11. Knowledge Centre

Provide:

- Project knowledge.
- Architecture maps.
- Decision records.
- Documentation.
- Dependency maps.
- Codebase summaries.
- Technical debt.
- Known issues.
- Research findings.

### 12. Settings Centre

Provide detailed configuration.

Categories:

- General.
- Appearance.
- Projects.
- Models.
- Ollama.
- Providers.
- Agents.
- Permissions.
- Approval rules.
- Prompt templates.
- Context management.
- Memory.
- Git.
- Docker.
- Linux server.
- GPU.
- Storage.
- Backups.
- Cost limits.
- Notifications.
- Security.
- API.
- Extensions.

Settings should have explanations, sensible defaults and validation.

Do not expose secrets in the UI.

---

# 6. GIT, DOCKER AND LINUX INTEGRATION

Do not treat Git, Docker and Linux as optional afterthoughts.

Research mature open-source implementations before writing integrations.

## Git

Support:

- Git status.
- Branch management.
- Commit history.
- Diff previews.
- Checkpoints.
- Rollback.
- Worktrees.
- Agent-specific branches.
- Merge conflict detection.
- Pull request preparation.
- Commit message generation.

Before any approved agent write operation:

1. Check repository status.
2. Identify uncommitted user changes.
3. Create a safe checkpoint or isolated worktree.
4. Execute approved work.
5. Show the resulting diff.
6. Run validation.
7. Allow user acceptance or rollback.

Never overwrite existing user changes.

## Docker

Support:

- Docker Engine.
- Docker Compose.
- Container status.
- Logs.
- Restart.
- Stop.
- Start.
- Health checks.
- Volume inspection.
- Network inspection.
- Resource usage.

Provide predefined secure deployment templates.

Do not automatically execute arbitrary Docker commands.

## Linux

Support remote Ubuntu server management.

Use:

- SSH.
- Secure key-based authentication.
- Docker.
- Ollama.
- NVIDIA drivers.
- NVIDIA Container Toolkit when required.
- GPU monitoring.
- Disk monitoring.
- Process monitoring.

Never expose Ollama publicly.

Prefer SSH tunnels or a secured private network.

Do not store SSH private keys in project files.

---

# 7. MEMORY AND PROJECT CONTEXT

Build a persistent project knowledge system.

Avoid sending complete conversation histories and entire repositories to models repeatedly.

Use layered context.

### Global memory
- User preferences.
- Global policies.
- General workflow instructions.

### Project memory
- Architecture.
- Requirements.
- Dependencies.
- Decisions.
- Rejected approaches.
- Known issues.
- Documentation.

### Task memory
- Objective.
- Relevant files.
- Constraints.
- Current status.
- Previous results.
- Acceptance criteria.

### Agent memory
- Agent-specific instructions.
- Previous assignments.
- Performance.
- Known limitations.

Store structured data in a database and human-readable decisions in Markdown.

Add source hashes and Git commit references to prevent stale context from being treated as current.

Use semantic search only where it provides measurable benefit.

---

# 8. SECURITY AND APPROVALS

Default operating mode: STRICT APPROVAL.

Permission levels:

1. Read-only.
2. Approved file modification.
3. Approved command execution.
4. Restricted automation.

Required protections:

- Project isolation.
- User confirmation.
- Git checkpoints.
- Command allowlists.
- Dangerous command blocks.
- Secret protection.
- API key encryption where appropriate.
- Audit logging.
- Sandbox execution.
- Agent worktree isolation.
- Prompt injection protection.
- File access boundaries.
- Network access controls.
- Dependency validation.
- Rollback.

Treat repository contents, documentation and agent outputs as untrusted inputs.

Do not allow a repository instruction or model response to silently override security policy.

---

# 9. QUALITY AND ENGINEERING STANDARDS

Use mature libraries rather than reinventing infrastructure.

Requirements:

- Modular architecture.
- Typed APIs.
- Database migrations.
- Unit tests.
- Integration tests.
- End-to-end tests.
- Security tests.
- Error handling.
- Structured logs.
- Configuration validation.
- Documentation.
- Backup and restore.
- Versioned APIs.

Every integration must have a defined interface.

Every major feature must have measurable acceptance criteria.

Do not create placeholder buttons or fake working features.

If a feature is not implemented, label it honestly.

---

# 10. TOKEN-EFFICIENT DEVELOPMENT RULES

This is mandatory.

You must minimise the amount of context and tokens used during development.

### Research efficiency

- Search repositories in batches.
- Avoid repeatedly researching the same project.
- Save findings in structured research files.
- Do not paste entire README files into prompts.
- Extract only relevant architecture and implementation details.
- Read source files selectively.
- Use GitHub API and repository metadata where possible.
- Record findings once and reuse them.

### Development efficiency

- Inspect the existing repository before changing it.
- Reuse existing components.
- Do not rewrite functioning modules without a reason.
- Do not regenerate entire files for minor changes.
- Use small patches.
- Work module by module.
- Reuse shared types and schemas.
- Keep prompts task-specific.
- Cache project summaries.
- Avoid repeated codebase analysis.

### Agent efficiency

- Use a planner only for tasks requiring planning.
- Use a coding agent for implementation.
- Use a reviewer for high-risk changes.
- Do not involve multiple agents in simple tasks.
- Limit parallel agents.
- Limit retries.
- Stop unproductive loops.
- Require clear completion criteria.
- Use deterministic scripts for predictable operations.

### Context efficiency

Each agent should receive only:

1. Relevant project summary.
2. Relevant architecture.
3. Relevant files.
4. Task requirements.
5. Constraints.
6. Acceptance criteria.

Do not send unrelated conversation history.

### Token reporting

Record:
- Input tokens.
- Output tokens.
- Cached tokens where supported.
- Model.
- Agent.
- Task.
- Project.
- Runtime.
- Estimated cost.

---

# 11. DEVELOPMENT APPROACH

Use a staged approach.

Do not attempt to build everything in one enormous implementation pass.

## Phase 0 — Repository discovery

Deliver:
- GitHub candidate list.
- Repository scores.
- Licence report.
- Feature comparison.
- Recommended foundation.
- Reusable modules.
- Missing functionality.
- Integration plan.

Do not write application code in this phase.

## Phase 1 — Foundation

Deliver:
- Selected codebase.
- LocalPilot branding.
- Development environment.
- Backend integration.
- Database.
- Configuration.
- Logging.
- Health checks.

## Phase 2 — Core intelligence

Deliver:
- Project registration.
- Project memory.
- Context engine.
- Task management.
- Prompt management.
- Model router.
- Ollama integration.

## Phase 3 — Agent operations

Deliver:
- Agent registry.
- Task assignment.
- Agent communication.
- Approval workflow.
- Agent history.
- Git checkpoints.
- Execution controls.

## Phase 4 — React dashboard

Deliver:
- Overview.
- Projects.
- Agent Centre.
- Prompt Studio.
- Decision Centre.
- Approval Centre.
- History Centre.
- Model Centre.
- Infrastructure Centre.
- Cost Centre.
- Knowledge Centre.
- Settings.

## Phase 5 — VS Code integration

Deliver:
- Sidebar.
- Project context.
- Coding agents.
- Code review.
- Diff preview.
- Approval requests.
- Task history.
- Dashboard deep links.

## Phase 6 — Infrastructure

Deliver:
- Docker support.
- Linux server.
- Remote Ollama.
- GPU monitoring.
- Persistent model storage.
- SSH connectivity.
- Cost-aware GPU lifecycle management.

## Phase 7 — Quality and optimisation

Deliver:
- Automated testing.
- Security testing.
- Benchmarking.
- Cost optimisation.
- Performance improvements.
- Backup and recovery.
- Documentation.

---

# 12. RECOMMENDED REPOSITORY ORGANISATION

Adapt this to the selected source repository rather than forcing a rewrite.

Potential target structure:

```
LocalPilot/
├── apps/
│   ├── web/
│   └── vscode-extension/
├── backend/
│   ├── api/
│   ├── core/
│   ├── orchestrator/
│   ├── agents/
│   ├── models/
│   ├── context/
│   ├── approvals/
│   ├── execution/
│   ├── git/
│   ├── infrastructure/
│   └── monitoring/
├── packages/
│   ├── shared-types/
│   ├── api-client/
│   └── ui/
├── config/
├── deploy/
│   ├── docker/
│   ├── linux/
│   └── ollama/
├── docs/
├── tests/
└── scripts/
```

The final structure must follow the selected architecture and avoid unnecessary duplication.

---

# 13. REQUIRED DELIVERABLES

Create these documents before major implementation:

1. REPOSITORY_RESEARCH.md
2. REPOSITORY_SCORECARD.md
3. REQUIREMENTS_MATRIX.md
4. LICENCE_AND_DEPENDENCY_AUDIT.md
5. ARCHITECTURE.md
6. DATABASE_SCHEMA.md
7. SECURITY.md
8. AGENT_PROTOCOL.md
9. MODEL_ROUTING.md
10. UI_UX_SPECIFICATION.md
11. INFRASTRUCTURE.md
12. DEVELOPMENT_ROADMAP.md

The requirements matrix must show:

- Requirement.
- Selected repository/module.
- Reuse or implementation approach.
- Status.
- Test evidence.
- Remaining work.

Calculate actual coverage.

Do not claim 95% coverage based on descriptions alone.

---

# 14. ACCEPTANCE CRITERIA

LocalPilot is successful when:

1. A user can manage multiple projects.
2. VS Code provides a productive coding experience.
3. The React dashboard manages the complete environment.
4. Local inference is preferred whenever practical.
5. Cloud inference is used only when justified.
6. Remote Ollama works securely.
7. Multiple agents can collaborate.
8. Agents share controlled project context.
9. Users approve file changes and commands.
10. Git checkpoints and rollback work.
11. Prompt templates are reusable.
12. Decisions are recorded.
13. Conversations and task history persist.
14. Costs are visible.
15. GPU infrastructure can be monitored.
16. Docker and Linux services can be managed.
17. Projects remain portable.
18. No provider lock-in is required.
19. The system can recover after interruptions.
20. The application is tested and documented.

---

# 15. FINAL INSTRUCTIONS

Do not immediately start generating code.

First inspect the existing repositories and identify the strongest foundation.

Prioritise:

1. Reuse.
2. Compatibility.
3. Reliability.
4. Security.
5. Cost efficiency.
6. Maintainability.
7. User experience.

Do not create a new subsystem when a suitable maintained implementation already exists.

Do not introduce unnecessary dependencies.

Do not use expensive AI models for deterministic work.

Do not build an elaborate architecture without evidence that it is needed.

Do not make assumptions about repository features: verify them in source code and tests.

Do not modify the user's existing repository without permission.

Do not expose secrets.

Do not claim features are complete without working implementation and tests.

**The immediate first task is repository research and selection, not coding.**

Return a concise executive summary, detailed comparison, verified requirement coverage and recommended implementation strategy.

Only after repository selection should development begin.
