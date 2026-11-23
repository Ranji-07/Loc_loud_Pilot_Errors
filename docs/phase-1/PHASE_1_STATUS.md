# Phase 1 status

Phase 1 goal: a working foundation you can install and use. That means the control plane, guided setup with
strict approval, usage checks with a small local model, a dashboard, a VS Code extension, and an AWS trial kit
that creates nothing until you approve it. Architecture follows Phase 0 **Option C** (FastAPI control plane
+ OpenHands SDK + LiteLLM + Ollama + new dashboard + thin VS Code extension). The OpenHands agent-server
integration is Phase 3.

## Built

| Area | Where | Notes |
|---|---|---|
| Control plane | `backend/localpilot` | FastAPI on 127.0.0.1:8765; refuses non-loopback bind unless explicitly allowed; Host check (DNS rebinding); custom header required on state-changing calls (blocks cross-site requests) |
| Storage | SQLite (WAL) + Alembic `0001_initial` | runs, steps, audit events, model calls (tokens, cost), usage snapshots |
| Logging | JSON lines, rotating, `E:\LocalPilot\data\logs` | secrets redacted from step output |
| Runbook engine | `runbooks/engine.py` + `config/runbooks/*.yaml` | approve → execute, modify (re-checked), stop (kills the process tree), skip, verify, live output (SSE), timeouts, long-running steps, per-step `cwd`, restart recovery |
| Command policy | `policy.py` | allowlist of programs/cmdlets, scripts only from `deploy/` or `scripts/`, deny patterns, loopback-only HTTP, risk escalation (high risk needs explicit confirmation) |
| Health | `health.py` | DB, Ollama, remote Ollama, LiteLLM, agent server, Docker, AWS identity, VS Code + extension, local GPU, disk |
| Usage | `usage/` | psutil, Ollama, AWS instances + cost-so-far, remote SSH probe; deterministic alerts; small-model rewording with a grounding check and a cache |
| Dashboard | `apps/web` | Overview, Setup guide, Usage, Audit log |
| VS Code extension | `apps/vscode-extension` | status bar health, activity bar views, open dashboard or guide inside VS Code, usage to an output channel, start backend |
| AWS kit | `deploy/aws` | check, quota request, default VPC, launch (dry run), status, tunnel, remote probes, stop/start/terminate, idle shutdown on the instance |
| LiteLLM kit | `deploy/litellm` | install/start scripts + config with local and remote routes |
| Scripts | `scripts/` | `start-localpilot.ps1`, `check-usage.ps1` (online and offline) |

## Verified

- **Backend tests: 59 passed** (`backend/tests`): policy allow/deny/risk cases, approval required, modify is
  policy-checked and audited, exact exit codes, stop of a long-running step, skip/complete rules, verify, SSE
  stream, redaction, host/origin/header guards, migrations idempotent, restart recovery, `cwd` cannot leave the
  repo, shipped runbooks load, usage grounding checks.
- **Live server with real Ollama** (qwen2.5:0.5b on `E:\LocalPilot\ollama\models`): local-setup steps succeed;
  model test runs; usage summary about 2 to 3 s on the CPU, with token counts logged.
- **Dashboard in a browser** (headless Chrome): health cards; execute with live output; editing to
  `notepad.exe` shows the policy block and disables Execute; Skip; Stop of a running model prompt; Verify;
  Usage page with the small-model summary. No page errors. Screenshots are in `docs/screenshots/`.
- **VS Code guide via the backend**: npm install → build `localpilot-0.1.0.vsix` → installed → `code
  --list-extensions` shows `localpilot.localpilot@0.1.0`; the health check reports it installed.
- **AWS kit, read-only parts only**: `check-account.ps1` and `launch.ps1 -DryRun` against your account. This
  found and fixed a PowerShell quoting bug in the VPC filter; with no VPC, the dry run now says to run
  *Create the default network*. High-risk launch without confirmation is rejected with HTTP 428.

## Not verified yet (honest gaps)

- No AWS resources were created (your choice), so launch, user-data/Ollama install, the tunnel, remote
  probes, idle shutdown, stop/start/terminate and the remote usage path are **untested against real AWS**.
- The VS Code extension UI (status bar, tree views, commands) was installed but not driven interactively.
  Only packaging and installation were verified.
- The LiteLLM install/start scripts have not been run.
- Docker engine is not running on this laptop. The Docker health check reports it; no Docker features yet.
- The small model's wording is checked for invented numbers only. A wrong non-numeric claim could still slip
  through; the rule-based summary is always available.

## Next phases

| Phase | Scope |
|---|---|
| 1b (when you choose) | Run the AWS guide end to end on t3.medium (~$0.05 for a short test), then g4dn.xlarge after quota approval |
| 2 | Model routing: LiteLLM gateway as the single model endpoint, budgets per task, cost alerts, model registry with local, remote and cloud tiers |
| 3 | Agents: OpenHands software-agent-sdk + agent-server (local Docker or the remote machine), task runs with approval gates in the dashboard |
| 4 | Repository workflows: plan → diff → approve → apply, tests, PR creation |
| 5 | VS Code deep integration: inline diff review, chat panel, SideCar side-by-side |
| 6 | Compute providers: static SSH workstation adapter, then SkyPilot/dstack for multi-cloud |
| 7 | Hardening and packaging: installer, auto-update, backups, security review |
