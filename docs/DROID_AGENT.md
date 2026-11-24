# Droid agent in LocalPilot

LocalPilot can drive [Factory Droid](https://docs.factory.ai) through the `droid-sdk` Python package. You give
Droid a task from the dashboard (**Droid agent** page) or from VS Code (**LocalPilot: Ask Droid**). Every file
change or command Droid wants to make becomes a pending approval that you approve once or deny.

## How it works

- The backend starts one Droid session per task (`backend/localpilot/agents/droid.py`) in an allowed folder
  (`LOCALPILOT_AGENT_WORKSPACES`, default: this repository).
- Autonomy is limited to **off** (ask for everything) or **low**. Higher levels are rejected.
- Each permission request is stored in the `approvals` table and shown in the dashboard and in the VS Code
  "Pending approvals" view. LocalPilot answers only "proceed once" or "cancel"; it never sends "always allow".
- If nobody decides within `LOCALPILOT_APPROVAL_TIMEOUT_SECONDS` (default 1800), the request is denied.
- When you deny, Droid ends the turn. Use **Continue** to give it new instructions in the same session.
- **Stop** denies any pending request and interrupts the session.
- Runs, events, approvals and decisions are recorded (`agent_runs`, `agent_events`, `approvals`, audit log).
  A restart marks active runs `interrupted` and pending approvals `expired`.
- Droid's clarifying questions are not supported yet; they are cancelled with a note in the run log.

## Models

- **Factory cloud models** (default `claude-haiku-4-5-20251001`) use your Droid login and are billed in Factory
  credits. The run shows the credits Droid reported.
- **Local Ollama model**: `Local Ollama: qwen2.5-coder 7B`. LocalPilot writes its own Droid settings file at
  `<data_dir>/droid/settings.json` and passes it with `--settings`; your `~/.factory/settings.json` is not changed.

Droid's system prompt and tools take about 13K tokens, more than Ollama's default context, so the local model is
a copy of `qwen2.5-coder:7b` with a 24K context:

```powershell
ollama pull qwen2.5-coder:7b
ollama create localpilot-coder -f deploy/ollama/localpilot-coder.Modelfile
```

Measured on this laptop (12 CPU threads, no GPU): Ollama processed the prompt at about 9-11 tokens per second,
so the first turn took about 25 minutes and used 6.4 GB of RAM. The model also wrote its tool call as plain text
(`{"name": "Read", ...}`) instead of a real tool call, so Droid treated it as the final answer. The local route
works end to end, but this model on a CPU is not useful for agent work. Use a remote GPU (see `deploy/aws/`) and
a model with reliable tool calling there.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/agents/models` | Models (with `location`: local or cloud), default model, allowed folders |
| POST | `/api/v1/agents/runs` | Start a run: `prompt`, `model`, `autonomy`, `cwd`, optional `continue_run_id` |
| GET | `/api/v1/agents/runs`, `/agents/runs/{id}` | List or read runs |
| GET | `/api/v1/agents/runs/{id}/events?after=N` | Run events after sequence N, plus streaming text |
| GET | `/api/v1/agents/runs/{id}/stream` | Same as Server-Sent Events |
| POST | `/api/v1/agents/runs/{id}/stop` | Stop a run |
| GET | `/api/v1/approvals?status=pending` | Pending approvals |
| POST | `/api/v1/approvals/{id}/decide` | `{"decision": "approve" \| "deny", "comment": "..."}` |

POST calls need the `x-localpilot-client: 1` header, like the rest of the API.
