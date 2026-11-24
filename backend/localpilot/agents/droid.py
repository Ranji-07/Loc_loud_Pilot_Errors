"""Droid agent runs driven through the Factory droid-sdk.

Every permission request Droid raises becomes an `Approval` row and waits for a human decision from any
client. Only "proceed once" or "cancel" are ever sent back: LocalPilot never persists an "always allow" rule.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import func, select

from .. import audit
from ..config import Settings
from ..db import Database
from ..models import AgentEvent, AgentRun, Approval, ModelCall, utcnow
from ..redact import redact

log = logging.getLogger("localpilot.agents")

AUTONOMY_LEVELS = ("off", "low")
ACTIVE = ("starting", "running", "waiting_approval")
TERMINAL = ("succeeded", "failed", "interrupted", "stopped")
MAX_TEXT = 20_000


class AgentError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        if status_code:
            self.status_code = status_code


@dataclass
class LiveRun:
    run_id: str
    task: asyncio.Task | None = None
    session: Any = None
    pending: dict[str, asyncio.Future] = field(default_factory=dict)
    changed: asyncio.Event = field(default_factory=asyncio.Event)
    partial: str = ""
    state: str = "starting"
    stop_requested: bool = False
    denied: str | None = None

    def notify(self) -> None:
        self.changed.set()


SessionFactory = Callable[..., Any]


def _clip(text: Any, n: int = MAX_TEXT) -> str:
    s = text if isinstance(text, str) else json.dumps(text, default=str)
    s = redact(s)
    return s if len(s) <= n else s[:n] + f"\n… [{len(s) - n} more characters]"


def serialize_action(action: Any) -> dict[str, Any]:
    kind = type(action).__name__
    out: dict[str, Any] = {"type": kind}
    for name in ("file_path", "file_name", "full_command", "impact_level", "risk_level_reason", "tool_name",
                 "server_name", "reason", "operation", "target", "title"):
        v = getattr(action, name, None)
        if v is not None:
            out[name] = _clip(str(v), 2000)
    for name in ("content", "old_content", "new_content", "patch_content", "plan"):
        v = getattr(action, name, None)
        if v is not None:
            out[name] = _clip(str(v))
    files = getattr(action, "files", None)
    if files:
        out["files"] = [{"file_path": getattr(f, "file_path", ""), "operation": getattr(f, "operation", "")} for f in files]
    return out


def describe(actions: list[dict[str, Any]]) -> tuple[str, str, str]:
    """(kind, title, risk) for an approval card."""
    if not actions:
        return "other", "Droid asks for permission", "medium"
    a = actions[0]
    t = a["type"]
    name = a.get("file_name") or a.get("file_path") or ""
    if t == "CreateFile":
        return "file_create", f"Create file {name}", "medium"
    if t in ("EditAction", "ApplyPatchAction"):
        more = f" (+{len(a.get('files', [])) - 1} files)" if len(a.get("files", [])) > 1 else ""
        return "file_edit", f"Edit file {name}{more}", "medium"
    if t == "ExecuteAction":
        impact = (a.get("impact_level") or "").lower()
        risk = "high" if impact == "high" else "medium" if impact == "medium" else "low"
        return "command", f"Run command: {a.get('full_command', '')[:200]}", risk
    if t == "McpToolAction":
        return "tool", f"Use tool {a.get('tool_name', '')}", "medium"
    if t in ("SandboxViolationAction", "DroidShieldViolationAction"):
        return "security", f"Security check: {a.get('reason', t)}"[:300], "high"
    return "other", t, "medium"


class DroidManager:
    def __init__(self, settings: Settings, db: Database, session_factory: SessionFactory | None = None,
                 models_loader: Callable[[], Any] | None = None) -> None:
        self.settings = settings
        self.db = db
        self._factory = session_factory or self._sdk_session
        self._models_loader = models_loader or self._sdk_models
        self._live: dict[str, LiveRun] = {}
        self._models: tuple[float, list[dict]] | None = None

    # ---- environment -------------------------------------------------------
    @property
    def settings_file(self) -> Path:
        return self.settings.data_dir / "droid" / "settings.json"

    def write_settings_file(self) -> Path:
        base = self.settings.ollama_url.rstrip("/") + "/v1"
        models = []
        for m in self.settings.droid_local_models:
            models.append({"model": m["model"], "displayName": m["displayName"], "baseUrl": m.get("baseUrl", base),
                           "apiKey": "ollama", "provider": "generic-chat-completion-api",
                           "maxOutputTokens": m.get("maxOutputTokens", 4096),
                           "maxContextLimit": m.get("maxContextLimit", 16384)})
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(json.dumps({"customModels": models}, indent=2), encoding="utf-8")
        return self.settings_file

    def executable(self) -> str | None:
        return self.settings.droid_executable or shutil.which("droid")

    def _runtime(self):
        from droid_sdk import Runtime
        return Runtime(executable=self.executable(), args=["--settings", str(self.write_settings_file())])

    def _sdk_session(self, *, cwd: Path, model: str, autonomy: str, on_permission, on_question,
                     resume_session_id: str | None):
        from droid_sdk import Autonomy, InteractionHandlers, Session, SessionConfig
        handlers = InteractionHandlers(on_permission=on_permission, on_question=on_question)
        if resume_session_id:
            return Session.resume(resume_session_id, interactions=handlers, runtime=self._runtime(),
                                  disable_builtin_skills=True)
        cfg = SessionConfig(autonomy=Autonomy(autonomy), disable_builtin_skills=True)
        return Session(cwd=cwd, model=model, config=cfg, interactions=handlers, runtime=self._runtime())

    async def _sdk_models(self) -> list[dict]:
        from droid_sdk import list_models
        local_names = {m["displayName"] for m in self.settings.droid_local_models}
        out = []
        for m in await list_models(runtime=self._runtime()):
            local = m.display_name in local_names
            out.append({"id": m.id, "name": m.display_name, "location": "local" if local else "cloud",
                        "custom": local})
        return out

    async def models(self, refresh: bool = False) -> list[dict]:
        if not self.executable():
            raise AgentError("Droid CLI not found on PATH", 503)
        if refresh or not self._models or time.time() - self._models[0] > 600:
            self._models = (time.time(), await self._models_loader())
        return self._models[1]

    def resolve_cwd(self, cwd: str | None) -> Path:
        roots = [Path(r).resolve() for r in self.settings.agent_workspaces]
        target = Path(cwd).resolve() if cwd else roots[0]
        if not target.is_dir():
            raise AgentError(f"Folder not found: {target}")
        if not any(target == r or target.is_relative_to(r) for r in roots):
            raise AgentError("Folder is outside the allowed agent workspaces (LOCALPILOT_AGENT_WORKSPACES)", 403)
        return target

    # ---- lifecycle -----------------------------------------------------------
    def recover(self) -> int:
        with self.db.session() as s:
            runs = s.scalars(select(AgentRun).where(AgentRun.status.in_(ACTIVE))).all()
            for r in runs:
                r.status, r.finished_at = "interrupted", utcnow()
                r.error = "LocalPilot restarted while this run was active"
            for a in s.scalars(select(Approval).where(Approval.status == "pending")).all():
                a.status, a.decided_by, a.decided_at = "expired", "system", utcnow()
        return len(runs)

    async def shutdown(self) -> None:
        for live in list(self._live.values()):
            await self.stop(live.run_id, actor="system")

    # ---- runs ----------------------------------------------------------------
    async def start(self, prompt: str, model: str | None, autonomy: str = "off", cwd: str | None = None,
                    continue_run_id: str | None = None) -> dict:
        prompt = prompt.strip()
        if not prompt:
            raise AgentError("Prompt is empty")
        if autonomy not in AUTONOMY_LEVELS:
            raise AgentError(f"Autonomy must be one of {AUTONOMY_LEVELS} (strict approval mode)")
        if not self.executable():
            raise AgentError("Droid CLI not found on PATH", 503)
        if sum(1 for lv in self._live.values() if lv.task and not lv.task.done()) >= self.settings.max_active_agent_runs:
            raise AgentError("Too many agent runs are active; stop one first", 409)

        parent = None
        if continue_run_id:
            parent = self.get_run(continue_run_id)
            if parent["status"] in ACTIVE:
                raise AgentError("The previous turn is still running", 409)
            if not parent["session_id"]:
                raise AgentError("The previous run has no Droid session to continue", 409)
            model, autonomy, folder = parent["model"], parent["autonomy"], Path(parent["cwd"])
        else:
            folder = self.resolve_cwd(cwd)
        model = model or self.settings.droid_default_model
        location = await self._location(model)

        run_id = str(uuid.uuid4())
        with self.db.session() as s:
            s.add(AgentRun(id=run_id, prompt=prompt, model=model, model_location=location, autonomy=autonomy,
                           cwd=str(folder), status="starting", parent_run_id=continue_run_id,
                           session_id=parent["session_id"] if parent else None, usage={}))
        audit.record(self.db, "agent.started", run_id, model=model, location=location, autonomy=autonomy,
                     cwd=str(folder), prompt=_clip(prompt, 500), continued_from=continue_run_id)
        live = LiveRun(run_id)
        self._live[run_id] = live
        live.task = asyncio.create_task(self._drive(live, prompt, model, autonomy, folder,
                                                    parent["session_id"] if parent else None))
        return self.get_run(run_id)

    async def _location(self, model: str) -> str:
        local_ids = {m["model"] for m in self.settings.droid_local_models}
        if model.startswith("custom:"):
            try:
                for m in await self.models():
                    if m["id"] == model:
                        return m["location"]
            except AgentError:
                pass
            return "local"
        return "local" if model in local_ids else "cloud"

    async def _drive(self, live: LiveRun, prompt: str, model: str, autonomy: str, cwd: Path,
                     resume_id: str | None) -> None:
        started = time.perf_counter()
        status, error, text, usage = "failed", None, "", {}
        try:
            session = self._factory(cwd=cwd, model=model, autonomy=autonomy,
                                    on_permission=lambda req: self._on_permission(live, req),
                                    on_question=lambda req: self._on_question(live, req),
                                    resume_session_id=resume_id)
            async with session as sess:
                live.session = sess
                self._update(live.run_id, status="running", session_id=getattr(sess, "id", None))
                live.state = "running"
                live.notify()
                async with sess.stream(prompt, include_partial_messages=True) as stream:
                    async for ev in stream:
                        self._handle(live, ev)
                result = stream.result
                text = getattr(result, "text", "") or ""
                usage = _usage_dict(getattr(result, "usage", None))
                subtype = getattr(result, "subtype", "error_during_execution")
                if subtype == "success":
                    status = "succeeded"
                elif subtype == "interrupted":
                    status = "stopped" if live.stop_requested else "interrupted"
                    if live.denied and not live.stop_requested:
                        error = (f"Droid ended this turn after you denied: {live.denied}. "
                                 "Use Continue to give it different instructions.")
                else:
                    err = getattr(result, "error", None)
                    error = getattr(err, "message", None) or subtype
        except asyncio.CancelledError:
            status, error = "stopped", "Cancelled"
        except Exception as e:  # the SDK raises DroidError subclasses for process/protocol failures
            log.exception("agent run failed")
            error = f"{type(e).__name__}: {redact(str(e))[:1000]}"
        finally:
            for fut in live.pending.values():
                if not fut.done():
                    fut.set_result(("deny", "run ended"))
            ms = int((time.perf_counter() - started) * 1000)
            with self.db.session() as s:
                run = s.get(AgentRun, live.run_id)
                if run:
                    run.status, run.error, run.finished_at = status, error, utcnow()
                    run.result_text = _clip(text)
                    run.usage = usage or run.usage
                    loc = run.model_location
                    s.add(ModelCall(task="droid-agent", provider="ollama" if loc == "local" else "factory",
                                    model=model, input_hash=live.run_id,
                                    prompt_tokens=int(usage.get("input_tokens", 0)) + int(usage.get("cache_read_tokens", 0))
                                    + int(usage.get("cache_creation_tokens", 0)),
                                    completion_tokens=int(usage.get("output_tokens", 0)), duration_ms=ms,
                                    cost_usd=0.0, credits=float(usage.get("factory_credits", 0) or 0),
                                    output=_clip(text, 2000)))
            self._event(live, "finished", {"status": status, "error": error})
            audit.record(self.db, f"agent.{status}", live.run_id, actor="system", error=error,
                         credits=usage.get("factory_credits"))
            live.state = status
            live.session = None
            live.notify()
            self._live.pop(live.run_id, None)

    def _handle(self, live: LiveRun, ev: Any) -> None:
        t = type(ev).__name__
        if t == "TextDelta":
            live.partial += getattr(ev, "text", "")
            live.notify()
        elif t == "AssistantMessage":
            live.partial = ""
            if getattr(ev, "text", ""):
                self._event(live, "assistant", {"text": _clip(ev.text)})
        elif t == "ToolCall":
            self._event(live, "tool_call", {"tool": ev.name, "id": ev.tool_use_id, "input": _clip(dict(ev.input) if hasattr(ev.input, "keys") else ev.input, 4000)})
        elif t == "ToolResult":
            self._event(live, "tool_result", {"tool": ev.tool_name, "id": ev.tool_use_id, "is_error": bool(ev.is_error),
                                              "content": _clip(ev.content, 4000)})
        elif t == "ErrorEvent":
            self._event(live, "error", {"message": _clip(getattr(ev, "message", ""), 2000)})
        elif t == "WorkingStateChanged":
            st = getattr(ev, "state", "")
            live.state = str(getattr(st, "value", st)).lower()
            live.notify()
        elif t == "SessionTitleUpdated":
            self._update(live.run_id, title=str(getattr(ev, "title", ""))[:200])
            live.notify()
        elif t == "TokenUsageUpdate":
            self._update(live.run_id, usage=_usage_dict(ev))
            live.notify()

    async def _on_permission(self, live: LiveRun, req: Any):
        from droid_sdk import ToolConfirmationOutcome as O
        offered = [getattr(o.value, "value", o.value) for o in req.options]
        actions = [serialize_action(a) for a in req.actions]
        kind, title, risk = describe(actions)
        approval_id = str(uuid.uuid4())
        with self.db.session() as s:
            s.add(Approval(id=approval_id, source="droid", run_id=live.run_id, kind=kind, title=title, risk=risk,
                           details={"actions": actions}, options=offered, status="pending"))
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        live.pending[approval_id] = fut
        self._update(live.run_id, status="waiting_approval")
        self._event(live, "approval_requested", {"approval_id": approval_id, "title": title, "risk": risk, "kind": kind})
        audit.record(self.db, "approval.requested", approval_id, actor="agent", run=live.run_id, title=title, risk=risk)
        try:
            decision, comment = await asyncio.wait_for(fut, self.settings.approval_timeout_seconds)
        except asyncio.TimeoutError:
            decision, comment = "expired", "No decision before the timeout"
            self._close_approval(approval_id, "expired", "system", comment)
        finally:
            live.pending.pop(approval_id, None)
        if not live.stop_requested:
            self._update(live.run_id, status="running")
        self._event(live, "approval_decided", {"approval_id": approval_id, "decision": decision})
        if decision != "approve":
            live.denied = title
        if decision == "approve" and "proceed_once" in offered:
            return req.respond(O.PROCEED_ONCE)
        return req.respond(O.CANCEL, comment=comment) if comment else req.respond(O.CANCEL)

    async def _on_question(self, live: LiveRun, req: Any):
        self._event(live, "error", {"message": "Droid asked a clarifying question; questions are not supported yet "
                                               "from LocalPilot, so it was cancelled. Put the details in your prompt."})
        return req.cancel()

    def decide(self, approval_id: str, decision: str, comment: str | None = None, actor: str = "user") -> dict:
        if decision not in ("approve", "deny"):
            raise AgentError("decision must be 'approve' or 'deny'")
        with self.db.session() as s:
            a = s.get(Approval, approval_id)
            if not a:
                raise AgentError("Unknown approval", 404)
            if a.status != "pending":
                raise AgentError(f"Approval is already {a.status}", 409)
            run_id = a.run_id
        live = self._live.get(run_id or "")
        fut = live.pending.get(approval_id) if live else None
        if not fut or fut.done():
            self._close_approval(approval_id, "expired", "system", "The agent run is no longer waiting")
            raise AgentError("The agent run is no longer waiting for this approval", 409)
        status = "approved" if decision == "approve" else "denied"
        self._close_approval(approval_id, status, actor, comment)
        audit.record(self.db, f"approval.{status}", approval_id, actor=actor, run=run_id, comment=comment)
        # Futures are not thread-safe and sync callers may run in a worker thread.
        fut.get_loop().call_soon_threadsafe(lambda: fut.done() or fut.set_result((decision, comment)))
        return self.get_approval(approval_id)

    def _close_approval(self, approval_id: str, status: str, actor: str, comment: str | None) -> None:
        with self.db.session() as s:
            a = s.get(Approval, approval_id)
            if a and a.status == "pending":
                a.status, a.decided_by, a.comment, a.decided_at = status, actor, comment, utcnow()

    async def stop(self, run_id: str, actor: str = "user") -> dict:
        live = self._live.get(run_id)
        if not live or not live.task or live.task.done():
            raise AgentError("Run is not active", 409)
        live.stop_requested = True
        audit.record(self.db, "agent.stop_requested", run_id, actor=actor)
        for aid, fut in list(live.pending.items()):
            if not fut.done():
                self._close_approval(aid, "denied", actor, "Run stopped")
                fut.set_result(("deny", "Run stopped by the user"))
        if live.session is not None:
            try:
                await asyncio.wait_for(live.session.interrupt(), 10)
            except Exception:
                live.task.cancel()
        else:
            live.task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(live.task), 20)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            live.task.cancel()
        return self.get_run(run_id)

    # ---- persistence helpers -------------------------------------------------
    def _update(self, run_id: str, **fields: Any) -> None:
        with self.db.session() as s:
            run = s.get(AgentRun, run_id)
            if run:
                for k, v in fields.items():
                    if v is not None:
                        setattr(run, k, v)

    def _event(self, live: LiveRun, type_: str, data: dict) -> None:
        with self.db.session() as s:
            seq = (s.scalar(select(func.max(AgentEvent.seq)).where(AgentEvent.run_id == live.run_id)) or 0) + 1
            s.add(AgentEvent(run_id=live.run_id, seq=seq, type=type_, data=data))
        live.notify()

    # ---- queries -------------------------------------------------------------
    def get_run(self, run_id: str) -> dict:
        with self.db.session() as s:
            r = s.get(AgentRun, run_id)
            if not r:
                raise AgentError("Unknown run", 404)
            pending = s.scalar(select(func.count()).select_from(Approval)
                               .where(Approval.run_id == run_id, Approval.status == "pending"))
            return self._run_dict(r, pending)

    def _run_dict(self, r: AgentRun, pending: int = 0) -> dict:
        live = self._live.get(r.id)
        return {"id": r.id, "agent": r.agent, "session_id": r.session_id, "parent_run_id": r.parent_run_id,
                "title": r.title or r.prompt[:80], "prompt": r.prompt, "model": r.model,
                "model_location": r.model_location, "autonomy": r.autonomy, "cwd": r.cwd, "status": r.status,
                "state": live.state if live else r.status, "result_text": r.result_text, "error": r.error,
                "usage": r.usage, "pending_approvals": pending, "created_at": _iso(r.created_at),
                "finished_at": _iso(r.finished_at)}

    def list_runs(self, limit: int = 50) -> list[dict]:
        with self.db.session() as s:
            rows = s.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)).all()
            return [self._run_dict(r) for r in rows]

    def events(self, run_id: str, after: int = 0) -> dict:
        self.get_run(run_id)
        with self.db.session() as s:
            rows = s.scalars(select(AgentEvent).where(AgentEvent.run_id == run_id, AgentEvent.seq > after)
                             .order_by(AgentEvent.seq)).all()
            events = [{"seq": e.seq, "at": _iso(e.at), "type": e.type, "data": e.data} for e in rows]
        live = self._live.get(run_id)
        return {"events": events, "next": events[-1]["seq"] if events else after,
                "partial": live.partial if live else "", "active": live is not None}

    def live(self, run_id: str) -> LiveRun | None:
        return self._live.get(run_id)

    def get_approval(self, approval_id: str) -> dict:
        with self.db.session() as s:
            a = s.get(Approval, approval_id)
            if not a:
                raise AgentError("Unknown approval", 404)
            return _approval_dict(a)

    def list_approvals(self, status: str | None = None, limit: int = 100) -> list[dict]:
        with self.db.session() as s:
            q = select(Approval).order_by(Approval.created_at.desc()).limit(limit)
            if status:
                q = q.where(Approval.status == status)
            return [_approval_dict(a) for a in s.scalars(q).all()]


def _approval_dict(a: Approval) -> dict:
    return {"id": a.id, "source": a.source, "run_id": a.run_id, "kind": a.kind, "title": a.title, "risk": a.risk,
            "details": a.details, "options": a.options, "status": a.status, "decided_by": a.decided_by,
            "comment": a.comment, "created_at": _iso(a.created_at), "decided_at": _iso(a.decided_at)}


def _usage_dict(u: Any) -> dict:
    if not u:
        return {}
    keys = ("input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens", "thinking_tokens",
            "factory_credits")
    return {k: getattr(u, k, 0) or 0 for k in keys}


def _iso(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None
