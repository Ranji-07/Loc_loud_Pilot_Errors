from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass

import httpx
import psutil
from sqlalchemy import text

from .config import Settings
from .db import Database
from .redact import redact


@dataclass
class Check:
    name: str
    status: str  # ok | warn | error | not_configured | info
    detail: str
    latency_ms: int = 0
    fix: str | None = None


def _run(argv: list[str], timeout: float = 10) -> tuple[int, str]:
    exe = shutil.which(argv[0])
    if not exe:
        return 127, f"{argv[0]} not found on PATH"
    try:
        r = subprocess.run([exe, *argv[1:]], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out"


async def _timed(name: str, coro) -> Check:
    t = time.perf_counter()
    try:
        c = await coro
    except Exception as e:  # a failed probe must never break the health endpoint
        c = Check(name, "error", f"{type(e).__name__}: {e}")
    c.latency_ms = int((time.perf_counter() - t) * 1000)
    return c


async def _http(url: str, timeout: float = 3.0) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.get(url)


async def check_database(db: Database) -> Check:
    def q() -> None:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    await asyncio.to_thread(q)
    return Check("database", "ok", f"SQLite at {db.url.removeprefix('sqlite:///')}")


async def check_ollama(s: Settings) -> Check:
    try:
        v = (await _http(f"{s.ollama_url}/api/version")).json().get("version")
        tags = (await _http(f"{s.ollama_url}/api/tags")).json().get("models", [])
    except httpx.HTTPError:
        return Check("ollama", "error", f"Ollama is not reachable at {s.ollama_url}",
                     fix="Start Ollama (open the Ollama app) or run the 'Local setup' guide")
    names = [m.get("name", "") for m in tags]
    if s.small_model not in names and f"{s.small_model}:latest" not in names:
        return Check("ollama", "warn", f"Ollama {v} running, helper model {s.small_model} not pulled ({len(names)} models)",
                     fix=f"Run step 'Pull the helper model' in the Local setup guide (ollama pull {s.small_model})")
    return Check("ollama", "ok", f"Ollama {v}, {len(names)} model(s): {', '.join(names[:5])}")


async def check_remote_ollama(s: Settings) -> Check:
    try:
        v = (await _http(f"{s.remote_ollama_url}/api/version", 2.0)).json().get("version")
        return Check("remote_ollama", "ok", f"Remote Ollama {v} reachable through tunnel at {s.remote_ollama_url}")
    except httpx.HTTPError:
        if s.aws_state_file.exists():
            return Check("remote_ollama", "warn", "A remote target is recorded but the SSH tunnel is not open",
                         fix="Run step 'Open the SSH tunnel' in the AWS GPU trial guide")
        return Check("remote_ollama", "not_configured", "No remote GPU target yet")


async def check_optional_service(name: str, url: str | None, path: str, how: str) -> Check:
    if not url:
        return Check(name, "not_configured", f"Not configured ({how})")
    try:
        r = await _http(url.rstrip("/") + path)
        if r.status_code < 400:
            return Check(name, "ok", f"Reachable at {url}")
        return Check(name, "error", f"{url} answered HTTP {r.status_code}")
    except httpx.HTTPError:
        return Check(name, "error", f"Not reachable at {url}")


async def check_docker() -> Check:
    rc, out = await asyncio.to_thread(_run, ["docker", "info", "--format", "{{.ServerVersion}}"], 10)
    if rc == 127:
        return Check("docker", "not_configured", "Docker CLI not installed (needed from Phase 3 for agent sandboxes)")
    if rc != 0:
        return Check("docker", "warn", "Docker is installed but the engine is not running",
                     fix="Start Docker Desktop when you need agent sandboxes (not required for Phase 1)")
    return Check("docker", "ok", f"Docker engine {out.splitlines()[0]}")


async def check_aws(s: Settings) -> Check:
    rc, out = await asyncio.to_thread(_run, ["aws", "sts", "get-caller-identity", "--output", "json"], 15)
    if rc == 127:
        return Check("aws", "not_configured", "AWS CLI not installed", fix="Install AWS CLI v2, then run 'aws configure'")
    if rc != 0:
        return Check("aws", "warn", "AWS CLI installed but credentials are not working",
                     fix="Run 'aws configure' in a terminal (LocalPilot never stores AWS keys)")
    try:
        arn = json.loads(out).get("Arn", "")
        who = arn.split(":", 5)[-1]
    except (ValueError, IndexError):
        who = "configured"
    return Check("aws", "ok", f"AWS CLI signed in as {who}, region {s.aws_region}")


async def check_vscode() -> Check:
    rc, out = await asyncio.to_thread(_run, ["code", "--list-extensions"], 20)
    if rc == 127:
        return Check("vscode", "not_configured", "VS Code CLI 'code' not on PATH")
    if "localpilot.localpilot" in out.lower():
        return Check("vscode", "ok", "VS Code with the LocalPilot extension installed")
    return Check("vscode", "warn", "VS Code found, LocalPilot extension not installed",
                 fix="Run the 'VS Code extension' guide")


async def check_local_gpu() -> Check:
    rc, out = await asyncio.to_thread(_run, ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], 10)
    if rc == 127:
        return Check("local_gpu", "info", "No NVIDIA GPU on this machine; large models run on the remote target")
    if rc != 0:
        return Check("local_gpu", "warn", redact(out)[:200])
    return Check("local_gpu", "ok", out.splitlines()[0])


async def check_disk(s: Settings) -> Check:
    usage = psutil.disk_usage(str(s.data_dir.anchor or s.data_dir))
    free_gb = usage.free / 1e9
    status = "ok" if free_gb >= 10 else "warn"
    return Check("disk", status, f"{free_gb:.0f} GB free on {s.data_dir.anchor} (data dir {s.data_dir})",
                 fix=None if status == "ok" else "Free space on the data drive or move models")


async def run_all(s: Settings, db: Database) -> list[dict]:
    checks = await asyncio.gather(
        _timed("database", check_database(db)),
        _timed("ollama", check_ollama(s)),
        _timed("remote_ollama", check_remote_ollama(s)),
        _timed("litellm", check_optional_service("litellm", s.litellm_url, "/health/liveliness",
                                                 "set LOCALPILOT_LITELLM_URL after running the LiteLLM gateway guide")),
        _timed("agent_server", check_optional_service("agent_server", s.agent_server_url, "/health",
                                                      "OpenHands agent-server arrives in Phase 3")),
        _timed("docker", check_docker()),
        _timed("aws", check_aws(s)),
        _timed("vscode", check_vscode()),
        _timed("local_gpu", check_local_gpu()),
        _timed("disk", check_disk(s)),
    )
    return [asdict(c) for c in checks]
