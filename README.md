# LocalPilot

A self-hosted AI engineering platform: a local FastAPI control plane, a web dashboard, and a thin VS Code
extension. Models run on this laptop (Ollama) or on a remote GPU machine (AWS or a workstation), reached
over an SSH tunnel. Every command runs only after you approve it.

Status: **Phase 1** (foundation: backend, guided setup, usage checks, dashboard, VS Code extension, AWS trial kit).
See [docs/phase-1/PHASE_1_STATUS.md](docs/phase-1/PHASE_1_STATUS.md) for what is built and tested.

## Quick start (Windows, PowerShell 7)

```powershell
./scripts/start-localpilot.ps1          # starts http://127.0.0.1:8765 and opens the dashboard
```

Then follow **Setup guide** in the dashboard. Full walkthrough: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## Layout

| Path | What it is |
|---|---|
| `backend/` | FastAPI control plane (`python -m localpilot`), SQLite + Alembic, runbook engine, command policy, usage probes |
| `apps/web/` | React + Vite + Tailwind dashboard (built into `apps/web/dist`, served by the backend) |
| `apps/vscode-extension/` | VS Code extension `localpilot.localpilot` (status bar, health, guides, usage) |
| `config/runbooks/` | Guided setup steps (YAML) shown in the dashboard |
| `deploy/aws/` | AWS trial kit: check, quota, network, launch, tunnel, stop, terminate |
| `deploy/litellm/` | Optional LiteLLM gateway (local and remote model routes) |
| `scripts/` | `start-localpilot.ps1`, `check-usage.ps1` |
| `docs/phase-0/` | Research, scorecard, requirements matrix, licences, remote-compute options |

## Development

```powershell
cd backend; .\.venv\Scripts\python.exe -m pytest -q     # backend tests
cd apps/web; npm run dev                                 # dashboard with hot reload on :5173 (proxies /api to :8765)
```
