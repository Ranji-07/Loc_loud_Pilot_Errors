# Licence and Dependency Audit (Phase 0)

Research date: 2026-11-23. Licences were read from each repository's licence file header via the GitHub API. This is an engineering review, not legal advice.

## Selected components (Option C)

| Component | Licence | Use in LocalPilot | Obligations | Restrictions to respect |
|---|---|---|---|---|
| OpenHands software-agent-sdk | MIT | Python dependency + agent-server API | Keep copyright notice if code is copied | Do not use OpenHands Enterprise or OpenHands-Cloud (licence `NOASSERTION`, not reviewed) |
| LiteLLM | MIT outside `litellm/enterprise/` | Separate proxy process | Keep notice | `enterprise/` features need a commercial licence; do not enable them |
| Ollama | MIT | Separate process (local and remote) | None for API use | Models carry their own licences; record each model's licence in the Model Centre |
| promptfoo | MIT | Optional CLI | None for CLI use | — |
| Glances | LGPL-3.0 | Separate process via REST API | None when used over its API unmodified | Do not statically embed modified Glances code without LGPL compliance |
| Dozzle | MIT | Optional separate container | None | — |
| Docker SDK for Python | Apache-2.0 | Library | Keep NOTICE | — |
| SideCar | MIT | Recommended companion extension, not bundled | None if not redistributed | — |
| Cezar (design/selected code) | MIT | Port of worktree-lifecycle design; possible UI patterns | Keep copyright and licence text in any copied file | — |
| Armada (reference only) | MIT | Design reference | Same as above if code is copied | — |

LocalPilot can be released under MIT or Apache-2.0 with these components.

## Rejected or restricted

| Repository | Licence | Why it is restricted for LocalPilot |
|---|---|---|
| open-webui/open-webui | Open WebUI License (BSD-3 with clause 4 branding condition) | Clause 4 makes retaining Open WebUI branding a condition of use; conflicts with LocalPilot branding |
| langgenius/dify | Modified Apache-2.0 | No multi-tenant use without written permission; logo and copyright in the console must not be removed |
| Arize-ai/phoenix | Elastic License 2.0 | Not open source; forbids offering it as a hosted/managed service |
| coder/coder | AGPL-3.0 | Network copyleft would apply to a hosted LocalPilot if code were combined |
| netdata/netdata | GPL-3.0 | Acceptable only as an unmodified separate process; not as embedded code |
| langfuse/langfuse, Agenta-AI/agenta, TabbyML/tabby | MIT/Apache with `ee/` directories | Core is usable; `ee/` code is under a separate commercial licence |
| microsoft/autogen | CC-BY-4.0 (docs) / archived | Archived; not considered |

## Dependency and resource notes (from docs, not yet measured)

| Component | Runtime | Resource concern on the 16 GB Windows machine |
|---|---|---|
| OpenHands agent-server | Python 3.12+, Docker for sandboxed workspaces | Docker Desktop/WSL2 memory; measure in Phase 1 |
| LiteLLM proxy | Python; Postgres needed only for virtual keys/spend DB | Run with SQLite-free minimal config first; Postgres optional |
| Ollama (local) | Native Windows build | Only small models (≤ 4B parameters, quantised) on CPU/iGPU |
| Langfuse (optional) | Postgres + ClickHouse + Redis + S3-compatible store | Too heavy for the dev machine; deferred |
| Armada (if Option A) | .NET 10 SDK, Node for dashboard rebuild | — |
| Cezar (if Option B) | Node 20+, agent CLIs | — |

Open items for Phase 1: generate SBOMs (`pip-licenses`, `license-checker`) for every pulled dependency, check each repository's security advisories, and pin versions.
