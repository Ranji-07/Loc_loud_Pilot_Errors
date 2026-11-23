# Getting started with LocalPilot

This guide takes you from nothing running to a working setup: dashboard, local helper model, VS Code
extension, and (optionally) an AWS machine for bigger models. You do every step in the dashboard. Each
step shows its exact command, and nothing runs until you press **Execute**.

## 1. Start LocalPilot

```powershell
cd E:\Loc_loud_Pilot_Errors
./scripts/start-localpilot.ps1
```

This starts the backend on `http://127.0.0.1:8765` and opens the dashboard. The first run builds the
dashboard (about 30 seconds). Keep the window open; press `Ctrl+C` to stop LocalPilot.

The backend only listens on `127.0.0.1`, so other computers cannot reach it. Data, logs and the
database live in `E:\LocalPilot\data`.

## 2. How a guided step works

Open **Setup guide** and pick a guide. Press **Start guide** (or **Start over** for a fresh run). Each step card has:

| Control | What it does |
|---|---|
| **Execute** / **Run again** | Runs the command shown. This is your approval. Output streams live into the card. |
| Edit the command box | Modifies the command before running. The card shows *(modified)* and re-checks it against the policy as you type. **reset** restores the original. |
| **Stop** | Kills the running command and everything it started. The step becomes *stopped*. |
| **Skip** | Marks the step skipped and moves on. Stop a running step before skipping it. |
| **Verify** | Runs the step's read-only check command (for example "is the model installed?"). |
| Risk badge | *low*, *medium* (downloads or installs), *high* (creates or bills cloud resources). High-risk steps need an extra tick box before **Execute** works. |

Blocked commands never run. Examples are recursive deletes, `git reset --hard`, piping downloads into a
shell, IAM changes, non-loopback web requests, and programs not on the allowlist. The card explains why.
Scripts may only run from `deploy/` or `scripts/` in this repository. Every action is recorded in **Audit log**.

## 3. Local setup guide (free, about 2 minutes)

Run **Local setup (laptop)** top to bottom:

1. Check Python, the backend runtime.
2. Check Ollama. If it fails, open Ollama from the Start menu. **Verify** calls its local API.
3. Check where models are stored. Expected: `E:\LocalPilot\ollama\models`. This is already set.
4. Pull the helper model `qwen2.5:0.5b` (about 400 MB). It is already pulled, so you can **Skip** or **Verify** this step.
5. Test the helper model with one short prompt on the CPU.
6. Check the AWS CLI and VS Code CLI.
7. View the full health report (the same data as the **Overview** page).

## 4. VS Code extension guide

Run **VS Code extension**: install the build dependencies, build `localpilot-0.1.0.vsix`, install it into VS
Code, then verify. Afterwards, reload VS Code windows (`Ctrl+Shift+P` → *Developer: Reload Window*). You get:

- A **LocalPilot** status bar item showing overall health (click it for details).
- A LocalPilot icon in the activity bar with **Health** and **Setup guides** views. Clicking a guide opens it
  inside VS Code.
- Commands (`Ctrl+Shift+P`): *LocalPilot: Open Dashboard*, *Open Setup Guide*, *Show Usage*, *Show Health*,
  *Start Backend*.

To remove the extension: `code --uninstall-extension localpilot.localpilot`.

## 5. Checking usage

- Dashboard **Usage** page: CPU, RAM, disks, top processes, loaded models, AWS instances and cost so far, the
  remote GPU, alerts, and token counts for every model call LocalPilot makes. **Explain with small model**
  asks `qwen2.5:0.5b` to reword the rule-based summary for a beginner. All numbers come from scripts, not the
  model. If the model adds a number that is not in the facts, its text is discarded and the rule-based
  summary is shown.
- Terminal:

  ```powershell
  ./scripts/check-usage.ps1            # numbers and alerts from the backend
  ./scripts/check-usage.ps1 -Summary   # plus the small-model summary
  ./scripts/check-usage.ps1 -Offline   # without the backend: direct Windows, Ollama and AWS checks
  ollama ps                            # models currently loaded in RAM
  ```

## 6. AWS guide (optional, costs money)

LocalPilot stays on your laptop; the AWS machine only runs models. Facts about your account (eu-north-1)
as checked:

- GPU quota is **0** (on-demand and spot). GPU machines need a quota request first. The standard quota (64 vCPUs) allows the CPU trial.
- There is **no VPC** in the region yet. The guide's *Create the default network* step creates the free AWS default VPC.
- No LocalPilot machines exist. Nothing is billing.

Steps in **AWS GPU trial (remote models)**:

| Step | Cost | Notes |
|---|---|---|
| Check the AWS account | free, read-only | Shows quotas, network, prices, any LocalPilot machines |
| Request GPU quota | free | High risk (changes your account). AWS approval takes hours to days. Optional. |
| Create the default network | free | High risk (creates a VPC). One time. |
| Dry-run the launch | free | AWS confirms the launch would work. Creates nothing. |
| Launch the trial machine | **t3.medium ≈ $0.043/h**, g4dn.xlarge ≈ $0.56/h; disk ≈ $0.08/GB-month | Creates an SSH key in `~/.ssh`, a firewall rule allowing SSH only from your current IP, and one machine. Ollama on the machine listens only on its own localhost. The machine powers off after 30 idle minutes. |
| Wait for setup | billing | 3 to 6 minutes on first boot |
| Open the SSH tunnel | billing | Long-running: keep it going, press **Stop** when done. Maps `127.0.0.1:11435` → remote Ollama. |
| List models / test remote model / check usage | billing | Same path agents will use later |
| Stop the machine | ends compute billing | Disk and models stay (billed per GB-month). Start again with `deploy/aws/start.ps1`. |
| Terminate | ends all billing | Deletes the machine, its disk and the firewall rule |

To switch to a GPU after quota approval, edit the launch command in the step card to
`-InstanceType g4dn.xlarge` before pressing **Execute**.

## 7. LiteLLM gateway (optional)

**LiteLLM model gateway** installs LiteLLM into `E:\LocalPilot\tools\litellm` and serves
`http://127.0.0.1:4000` with `local-small` (laptop Ollama) and `remote-small` (remote Ollama through the
tunnel). Not needed for Phase 1.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard does not open | Is `start-localpilot.ps1` still running? Something else may hold port 8765: `Get-NetTCPConnection -LocalPort 8765` |
| Ollama check fails | Start the Ollama app; check `ollama --version` |
| VS Code shows "LocalPilot offline" | Start the backend (or run *LocalPilot: Start Backend*) |
| A step says "Policy blocks this command" | Edit it back (**reset**) or put the logic in a script under `scripts/` |
| Step shows *interrupted* | LocalPilot was restarted while it ran; run it again |
