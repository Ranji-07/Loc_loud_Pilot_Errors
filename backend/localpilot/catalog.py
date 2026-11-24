"""Read-only views for the dashboard: model catalog, settings and the backend log."""
from __future__ import annotations

import asyncio
import json
import re
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from sqlalchemy import func, select

from .config import Settings
from .db import Database
from .models import ModelCall
from .redact import redact

_SECRET_NAME = re.compile(r"^(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|secret[_-]?key|aws_secret_access_key|password|authorization)$", re.I)


def _bare(name: str) -> str:
    return name.removesuffix(":latest")


def _param(parameters: str, name: str) -> str | None:
    for line in (parameters or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == name:
            return parts[1]
    return None


async def ollama_models(url: str, timeout: float = 3.0, transport: httpx.AsyncBaseTransport | None = None) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, transport=transport) as c:
            tags = (await c.get(f"{url}/api/tags")).json().get("models", [])
            ps = (await c.get(f"{url}/api/ps")).json().get("models", [])
            shows = await asyncio.gather(*(c.post(f"{url}/api/show", json={"model": m.get("name")}) for m in tags),
                                         return_exceptions=True)
    except (httpx.HTTPError, ValueError):
        return {"url": url, "reachable": False, "models": []}
    loaded = {m.get("name"): m for m in ps}
    out = []
    for m, sh in zip(tags, shows):
        info: dict[str, Any] = {}
        if isinstance(sh, httpx.Response) and sh.status_code == 200:
            try:
                info = sh.json()
            except ValueError:
                info = {}
        details = info.get("details") or m.get("details") or {}
        max_ctx = next((v for k, v in (info.get("model_info") or {}).items() if k.endswith(".context_length")), None)
        num_ctx = _param(info.get("parameters", ""), "num_ctx")
        lm = loaded.get(m.get("name"))
        out.append({
            "name": m.get("name"), "family": details.get("family"), "parameter_size": details.get("parameter_size"),
            "quantization": details.get("quantization_level"), "parent_model": details.get("parent_model") or None,
            "size_gb": round(m.get("size", 0) / 1e9, 2), "max_context": max_ctx,
            "configured_context": int(num_ctx) if num_ctx and num_ctx.isdigit() else None,
            "capabilities": info.get("capabilities") or [], "loaded": lm is not None,
            "loaded_gb": round(lm.get("size", 0) / 1e9, 2) if lm else None,
            "loaded_on_gpu_gb": round(lm.get("size_vram", 0) / 1e9, 2) if lm else None,
        })
    return {"url": url, "reachable": True, "models": out}


def model_usage(db: Database) -> dict[str, dict[str, Any]]:
    q = (select(ModelCall.model, func.count(), func.sum(ModelCall.prompt_tokens), func.sum(ModelCall.completion_tokens),
                func.sum(ModelCall.credits), func.max(ModelCall.at))
         .where(ModelCall.provider != "cache").group_by(ModelCall.model))
    with db.session() as s:
        rows = s.execute(q).all()
    return {m: {"calls": n, "prompt_tokens": pt or 0, "completion_tokens": ct or 0, "credits": round(cr or 0, 2),
                "last_used": last.isoformat() + "Z" if last else None} for m, n, pt, ct, cr, last in rows}


async def catalog(settings: Settings, db: Database, droid_models) -> dict[str, Any]:
    """`droid_models` is an awaitable of Droid's model list (may raise when the CLI is missing)."""
    local, remote, droid = await asyncio.gather(
        ollama_models(settings.ollama_url), ollama_models(settings.remote_ollama_url, 2.0), droid_models,
        return_exceptions=True)
    usage = model_usage(db)
    local_offers = {_bare(m["model"]): m["displayName"] for m in settings.droid_local_models}

    def used_by(name: str) -> list[str]:
        roles = []
        if _bare(name) == _bare(settings.small_model):
            roles.append("Usage summaries (LOCALPILOT_SMALL_MODEL)")
        if _bare(name) in local_offers:
            roles.append(f"Offered to Droid as \"{local_offers[_bare(name)]}\"")
        return roles

    if isinstance(local, dict):
        for m in local["models"]:
            m["used_by"] = used_by(m["name"])
    if isinstance(remote, dict):
        for m in remote["models"]:
            m["used_by"] = []
    if isinstance(remote, dict) and not remote["reachable"]:
        remote["reason"] = "Remote Ollama is not reachable at the configured endpoint"

    if isinstance(droid, BaseException):
        droid_block: dict[str, Any] = {"available": False, "reason": str(droid) or type(droid).__name__, "models": []}
    else:
        models = []
        for m in droid:
            u = usage.get(m["id"], {})
            models.append({**m, "default": m["id"] == settings.droid_default_model, **u})
        droid_block = {"available": True, "default": settings.droid_default_model, "models": models}

    routing = [
        {"task": "Usage summaries", "route": ["Cache (same facts within "
                                              f"{settings.summary_cache_seconds} s)", "Rule-based text",
                                              f"Small local model {settings.small_model} rewords it"],
         "note": "Numbers the model adds are rejected and the rule-based text is shown instead."},
        {"task": "Droid tasks", "route": ["The model you pick for the task (default "
                                          f"{settings.droid_default_model})"],
         "note": "There is no automatic router yet (Phase 2)."},
    ]
    return {"local": local if isinstance(local, dict) else {"url": settings.ollama_url, "reachable": False, "models": []},
            "remote": remote if isinstance(remote, dict) else {"url": settings.remote_ollama_url, "reachable": False, "models": []},
            "droid": droid_block, "routing": routing}


GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("General", [
        ("host", "Address the backend listens on. Only loopback addresses are accepted unless the next setting is on."),
        ("port", "Port for the dashboard and API."),
        ("allow_non_loopback_bind", "Allow listening on a network address. Off by default because LocalPilot runs approved commands."),
        ("log_level", "Detail level of the backend log (DEBUG, INFO, WARNING, ERROR)."),
    ]),
    ("Storage", [
        ("data_dir", "Database, logs and agent files. Keep it on the large data drive."),
        ("repo_root", "The LocalPilot repository."),
        ("runbooks_dir", "Folder with the setup guides (YAML)."),
        ("web_dist", "Built dashboard served by the backend."),
        ("pricing_file", "Prices used for AWS cost estimates."),
    ]),
    ("Models and providers", [
        ("ollama_url", "Local Ollama server."),
        ("remote_ollama_url", "Remote Ollama reached through the SSH tunnel."),
        ("litellm_url", "Optional LiteLLM gateway."),
        ("small_model", "Small local model that rewords usage summaries."),
        ("summary_cache_seconds", "How long an identical summary is reused instead of calling the model again."),
    ]),
    ("Agents", [
        ("droid_executable", "Path to the Droid CLI. Empty means it is found on PATH."),
        ("droid_default_model", "Model preselected for new Droid tasks."),
        ("droid_local_models", "Local Ollama models offered to Droid."),
        ("agent_workspaces", "Folders Droid may work in."),
        ("max_active_agent_runs", "How many Droid runs may be active at the same time."),
        ("agent_server_url", "OpenHands agent-server (Phase 3)."),
    ]),
    ("Permissions", [
        ("approval_timeout_seconds", "An approval request that waits longer than this is denied."),
        ("step_timeout_seconds", "Setup guide steps that run longer than this are stopped."),
    ]),
    ("Infrastructure", [
        ("aws_region", "AWS region used by the remote GPU guide and cost checks."),
    ]),
]


def _scrub(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: "hidden" if _SECRET_NAME.search(k) else _scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    if isinstance(value, str):
        if value.startswith(("http://", "https://")):
            parts = urlsplit(value)
            host = parts.hostname or ""
            if ":" in host:
                host = f"[{host}]"
            netloc = f"hidden@{host}" + (f":{parts.port}" if parts.port else "") if parts.username or parts.password else parts.netloc
            query = urlencode([(k, "hidden" if _SECRET_NAME.search(k) else v) for k, v in parse_qsl(parts.query, keep_blank_values=True)])
            value = urlunsplit(parts._replace(netloc=netloc, query=query, fragment=""))
        return redact(value)
    return value


def settings_view(settings: Settings) -> dict[str, Any]:
    fields = type(settings).model_fields
    derived = {"runbooks_dir": settings.repo_root / "config" / "runbooks",
               "web_dist": settings.repo_root / "apps" / "web" / "dist",
               "pricing_file": settings.repo_root / "config" / "pricing.yaml",
               "agent_workspaces": [settings.repo_root]}
    groups = []
    for title, items in GROUPS:
        rows = []
        for name, description in items:
            value = getattr(settings, name)
            default = derived.get(name, fields[name].get_default(call_default_factory=True))
            secret = bool(_SECRET_NAME.search(name))
            rows.append({"name": name, "env": f"LOCALPILOT_{name.upper()}", "description": description,
                         "value": "hidden" if secret else _scrub(value), "default": "hidden" if secret else _scrub(default),
                         "is_default": _scrub(value) == _scrub(default), "secret": secret})
        groups.append({"title": title, "settings": rows})
    return {"groups": groups, "editable": False,
            "how_to_change": "Set LOCALPILOT_<NAME> in backend/.env (or the environment), then restart LocalPilot."}


def log_tail(settings: Settings, lines: int) -> dict[str, Any]:
    path = settings.log_dir / "localpilot.jsonl"
    if not path.exists():
        return {"path": str(path), "lines": []}
    with path.open(encoding="utf-8", errors="replace") as f:
        tail = deque(f, maxlen=lines)
    out = []
    for raw in tail:
        raw = raw.rstrip("\n")
        try:
            rec = _scrub(json.loads(raw))
            out.append({"ts": rec.pop("ts", None), "level": rec.pop("level", None), "msg": rec.pop("msg", ""),
                        "logger": rec.pop("logger", None), "extra": rec})
        except (ValueError, AttributeError):
            out.append({"ts": None, "level": None, "msg": redact(raw), "logger": None, "extra": {}})
    return {"path": str(path), "lines": out}
