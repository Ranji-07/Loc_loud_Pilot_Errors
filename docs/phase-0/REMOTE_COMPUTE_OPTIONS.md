# Remote Compute Options (Phase 0 addendum)

Research date: 2026-11-23. Design input only; no code.

## 1. Goal

LocalPilot keeps the same flow as the Phase 0 recommendation (control plane, dashboard, VS Code client, approval gate), but models and agents can run on a separate machine:

- a workstation on the same network or reachable over the internet,
- a rented GPU pod (RunPod, Vast.ai and similar),
- a cloud VM (AWS, GCP, Azure and others),
- or the laptop itself when nothing else is available.

Example target topology: the Windows laptop runs LocalPilot; a workstation runs Ollama/vLLM and the agent runtime.

```
 Windows laptop (always on while you work)            Compute target (workstation / cloud GPU)
 ┌──────────────────────────────────────────┐        ┌────────────────────────────────────────┐
 │ React dashboard   VS Code extension      │        │ LocalPilot node bundle (docker compose)│
 │        │                │                │        │  - Ollama or vLLM (models)             │
 │        └──── LocalPilot control plane ───┼─ SSH ──┼─ - OpenHands agent-server (agents,     │
 │              (FastAPI + SQLite on E:)    │ tunnel │    sandboxed Docker workspaces)        │
 │              - approvals, decisions      │  or    │  - node probe (nvidia-smi / Glances)   │
 │              - cost + GPU-hour ledger    │tailnet │  - repo worktrees for agent tasks      │
 │              - ComputeProvider adapters  │        └────────────────────────────────────────┘
 │        LiteLLM proxy (routes to targets) │
 └──────────────────────────────────────────┘
```

Nothing on the compute target listens on a public port. The laptop reaches it through an SSH tunnel (default) or a private tailnet.

## 2. What existing projects already provide (verified 2026-11-23)

| Need | Project | Licence | Activity | Evidence |
|---|---|---|---|---|
| Run agents on a remote machine and drive them from the laptop | OpenHands software-agent-sdk `RemoteWorkspace` + agent-server | MIT | 297 commits Oct 2026 | `openhands-sdk/openhands/sdk/workspace/remote/base.py`: `RemoteWorkspace(host, api_key)` with `execute_command`, `file_upload`, `file_download`, `git_changes`, `git_diff`, `alive` (`/health`) |
| Route model calls to whichever machine hosts the model | LiteLLM proxy | MIT core | 2,357 commits Oct 2026 | `litellm/llms/ollama/`, `litellm/router_strategy/*` (see REPOSITORY_RESEARCH.md §4.5) |
| Serve models on the target | Ollama (MIT), vLLM (Apache-2.0), llama.cpp server (MIT) | — | 155 / 2,015 / 719 commits Oct 2026 | metadata only |
| Provision GPU machines on many clouds with one API | SkyPilot | Apache-2.0 | 180 commits Oct 2026, v0.14.3 (2026-11-16) | `sky/clouds/{aws,gcp,azure,runpod,vast,lambda_cloud,kubernetes,ssh,...}.py`; autostop protocol `sky/schemas/proto/autostopv1.proto`; admin policy `examples/admin_policy/set_max_autostop_idle_minutes.yaml` |
| Same, plus SSH fleets of your own machines | dstack | MPL-2.0 | 68 commits Oct 2026, 0.22.8 (2026-11-12) | `src/dstack/_internal/core/backends/{aws,gcp,azure,runpod,vastai,lambdalabs,...}`; `server/services/ssh_fleets/provisioning.py`; docs: fleet `idle_duration` auto-terminates idle instances |
| Private network without public ports | Tailscale client (BSD-3) with Tailscale SaaS or self-hosted Headscale (BSD-3) | — | 159 / 216 commits Oct 2026 | metadata only |
| GPU cluster manager with its own UI | GPUStack | Apache-2.0 | 175 commits Oct 2026 | worker routes, GPU-matching filters; overlaps with LocalPilot's Model Centre, so reference only |

Limits found in source and docs:
- SkyPilot on RunPod: `CloudImplementationFeatures.STOP: 'Stopping not supported.'` (`sky/clouds/runpod.py`). RunPod pods can only be terminated, so models must live on a network volume or be re-downloaded. Vast.ai does not list STOP as unsupported.
- SkyPilot's SSH target class is `class SSH(kubernetes.Kubernetes)` (`sky/clouds/ssh.py`), so using it for a workstation installs a Kubernetes layer. That is heavy for a single workstation.
- SkyPilot on Windows needs WSL (official install docs: "Use WSL on Windows").
- dstack's Windows client support was not verified.
- Armada and Cezar also support remote operation (Armada's Admiral server plus Harbor agent; Cezar "locally or 24/7 on your own server"), but they move the whole orchestrator, not just models and agents.

## 3. Proposed design: one `ComputeProvider` interface, several adapters

LocalPilot owns the interface. Adapters wrap existing tools; none of them owns LocalPilot state.

| Operation | Meaning |
|---|---|
| `list_targets()` | Known machines and their status |
| `provision(spec)` / `start(target)` | Create or power on (cloud only; no-op for a static workstation) |
| `stop(target)` / `terminate(target)` | Respect provider limits (e.g. RunPod cannot stop) |
| `health(target)` | Ollama/vLLM reachable, agent-server `/health`, GPU visible |
| `metrics(target)` | GPU/VRAM/RAM/disk via `nvidia-smi` and Glances |
| `open_tunnel(target)` | SSH local forwards for model and agent-server ports |
| `price(target)` | Hourly rate used by the GPU-hour ledger |

Adapters, in build order:

1. **Static SSH host** (no extra dependency). Covers a workstation, a manually rented VM, and RunPod/Vast pods reached over SSH. Uses the user's existing SSH key from the OS key store or `~/.ssh`, never from project files.
2. **Cloud provisioning adapter** wrapping SkyPilot (recommended: Apache-2.0, widest provider list, autostop) or dstack (alternative: SSH fleets without Kubernetes, `idle_duration`). Run it inside WSL on the laptop or on the workstation. Choose after the Phase 1 spike.
3. **Local** (laptop CPU/iGPU) for small models and as the fallback when no target is up.

## 4. Flow for one agent task on a remote target

1. User approves the task plan in the dashboard (strict approval mode).
2. Control plane picks a target (router rules: model needed, VRAM, cost, privacy class). If the target is a stopped cloud machine, it shows the cost estimate and asks before starting it.
3. Control plane opens the tunnel and checks `health`.
4. The target creates a git worktree for the task from the project's git remote (or from a bundle uploaded by the laptop if the repository has no remote). The user's working copy on the laptop is never touched.
5. The agent runs in the agent-server's Docker workspace on the target. Model calls go to the target's local Ollama/vLLM, or back through LiteLLM if a different model is routed.
6. Every file write or command pauses at the confirmation policy. The control plane shows the request, diff (`git_diff`) and risk in the Approval Centre.
7. On acceptance, the result comes back as a branch push or a patch. The laptop applies it only after a checkpoint and a final approval.
8. Idle timer: when no task has run for N minutes (user setting), the control plane stops or terminates the cloud target and closes the GPU-hour ledger entry. A static workstation is never powered off by LocalPilot unless the user allows it.

## 5. Security rules for remote targets

- No public ports: Ollama binds to `127.0.0.1` on the target; access only through SSH forwards or the tailnet.
- Agent-server is protected by an API key held by the control plane, stored in the OS credential store, never in project files or the UI.
- Cloud credentials stay in the provisioning tool's own config (e.g. `~/.aws`, SkyPilot/dstack config); LocalPilot stores only a reference.
- Privacy class per project: "local only" projects are never routed to cloud targets.
- Every start, stop, provision and terminate is an audited, approval-gated action.

## 6. Open questions to settle in Phase 1

1. Repository transport: git remote (simplest) or uploaded bundle for repositories without a remote.
2. SkyPilot vs dstack for cloud provisioning (spike both against one RunPod or Vast pod; measure setup time and Windows/WSL friction).
3. Tailnet: Tailscale SaaS (free personal plan, verify terms) vs self-hosted Headscale vs plain SSH only.
4. Whether the control plane should optionally move to the workstation too (laptop becomes a browser + VS Code client). The design supports this because the control plane is a normal web service.
