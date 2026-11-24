from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import func, or_, select, update

from . import audit
from .agents.droid import ACTIVE, AgentError, DroidManager
from .checkpoints import safe_path
from .db import Database
from .models import AgentProfile, AgentRun, ContextItem, Project, PromptVersion, SavedPrompt, Task, TaskAttempt, utcnow
from .redact import redact

log = logging.getLogger("localpilot.workspace")
BUSY = (*ACTIVE, "queued")
MAX_CONTEXT = 32_000


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def as_dict(row) -> dict:
    data = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    for k, v in data.items():
        if hasattr(v, "isoformat"):
            data[k] = v.isoformat() + "Z"
    return data


def require(s, model, id: str):
    row = s.get(model, id)
    if row is None:
        raise AgentError(f"Unknown {model.__tablename__} record", 404)
    return row


def revise(s, model, id: str, revision: int, fields: dict):
    result = s.execute(update(model).where(model.id == id, model.revision == revision)
                       .values(**fields, revision=revision + 1))
    if result.rowcount != 1:
        require(s, model, id)
        raise AgentError("Record changed; refresh before saving", 409)


def commit_at(root: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, timeout=5, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def context_file(root: Path, path: str) -> tuple[Path, str]:
    root = root.resolve()
    target = safe_path(root, path)
    if not target.is_file() or target.stat().st_size > 64 * 1024:
        raise AgentError("Context file is missing or exceeds 64 KiB")
    try:
        raw = target.read_bytes()
        text = raw.decode("utf-8")
        if "\0" in text:
            raise ValueError("binary")
    except (UnicodeError, ValueError, OSError):
        raise AgentError("Context must be a readable UTF-8 text file") from None
    return target, text


class Workspace:
    def __init__(self, db: Database, manager: Callable[[], DroidManager]):
        self.db, self.manager = db, manager
        self.lock = asyncio.Lock()
        self.worker: asyncio.Task | None = None

    def recover(self):
        with self.db.session() as s:
            if not s.scalar(select(AgentProfile.id).limit(1)):
                s.add(AgentProfile(id="droid", name="Droid", role="Coding", instructions=""))
            for t in s.scalars(select(Task).where(Task.status.in_(BUSY))).all():
                t.status = "interrupted" if t.run_id else "draft"
                t.error = "Server restarted. Start explicitly to run this task again."
                t.revision += 1

    def list(self, model, project_id: str | None = None, before: str | None = None, limit: int = 50):
        with self.db.session() as s:
            dated = hasattr(model, "created_at")
            q = select(model).order_by(*([model.created_at.desc()] if dated else []), model.id.desc()).limit(limit)
            if project_id:
                q = q.where(model.project_id == project_id)
            if before:
                cursor = require(s, model, before)
                if project_id and cursor.project_id != project_id:
                    raise AgentError("Cursor belongs to another project", 403)
                q = q.where(or_(model.created_at < cursor.created_at,
                                (model.created_at == cursor.created_at) & (model.id < before))
                            if dated else model.id < before)
            data = [as_dict(r) for r in s.scalars(q)]
            if model is Task:
                for row in data:
                    row.pop("snapshot")
            return data

    def project(self, id: str):
        with self.db.session() as s:
            return as_dict(require(s, Project, id))

    def create_project(self, name: str, root: str, actor: str):
        folder = self.manager().resolve_cwd(root)
        with self.db.session() as s:
            if s.scalar(select(Project.id).where(Project.root == str(folder))):
                raise AgentError("This project root is already registered", 409)
            row = Project(id=str(uuid.uuid4()), name=name, root=str(folder))
            s.add(row)
            s.flush()
            data = as_dict(row)
        audit.record(self.db, "project.created", row.id, actor=actor)
        return data

    def edit(self, model, id: str, revision: int, fields: dict, actor: str):
        with self.db.session() as s:
            revise(s, model, id, revision, fields)
            data = as_dict(require(s, model, id))
        audit.record(self.db, f"{model.__tablename__}.updated", id, actor=actor)
        return data

    def save_context(self, project_id: str, fields: dict, actor: str, id: str | None = None, revision: int = 1):
        p = self.project(project_id)
        fields = dict(fields)
        if fields["kind"] == "file":
            if not fields.get("path"):
                raise AgentError("A file reference needs a path")
            target, text = context_file(Path(p["root"]), fields["path"])
            fields.update(path=target.relative_to(Path(p["root"])).as_posix(), content="", source_hash=digest(text))
        else:
            fields.update(path=None, content=redact(fields["content"]), source_hash=digest(fields["content"]))
        fields["source_commit"] = commit_at(Path(p["root"]))
        with self.db.session() as s:
            if id:
                row = require(s, ContextItem, id)
                if row.project_id != project_id:
                    raise AgentError("Context belongs to another project", 403)
                revise(s, ContextItem, id, revision, fields)
                row = require(s, ContextItem, id)
            else:
                row = ContextItem(id=str(uuid.uuid4()), project_id=project_id, **fields)
                s.add(row)
                s.flush()
            data = as_dict(row)
        audit.record(self.db, "context.saved", row.id, actor=actor, project_id=project_id, kind=row.kind)
        return data

    def create_agent(self, fields: dict, actor: str):
        with self.db.session() as s:
            row = AgentProfile(id=str(uuid.uuid4()), **fields)
            s.add(row)
            s.flush()
            data = as_dict(row)
        audit.record(self.db, "agent_profile.created", row.id, actor=actor)
        return data

    def save_prompt(self, project_id: str, name: str, content: str, actor: str, id: str | None = None,
                    revision: int = 1):
        with self.db.session() as s:
            require(s, Project, project_id)
            if id:
                row = require(s, SavedPrompt, id)
                if row.project_id != project_id:
                    raise AgentError("Prompt belongs to another project", 403)
                revise(s, SavedPrompt, id, revision, {"name": name})
                row = require(s, SavedPrompt, id)
            else:
                row = SavedPrompt(id=str(uuid.uuid4()), project_id=project_id, name=name)
                s.add(row)
                s.flush()
            s.add(PromptVersion(prompt_id=row.id, version=row.revision, content=redact(content)))
            data = as_dict(row)
        audit.record(self.db, "prompt.saved", row.id, actor=actor, version=row.revision, project_id=project_id)
        return data

    def prompt_versions(self, id: str, before: int | None = None, limit: int = 25):
        with self.db.session() as s:
            require(s, SavedPrompt, id)
            q = select(PromptVersion).where(PromptVersion.prompt_id == id).order_by(PromptVersion.version.desc())
            if before:
                q = q.where(PromptVersion.version < before)
            return [as_dict(v) for v in s.scalars(q.limit(limit))]

    def create_task(self, fields: dict, actor: str, id: str | None = None, revision: int = 1):
        with self.db.session() as s:
            require(s, Project, fields["project_id"])
            require(s, AgentProfile, fields["agent_id"])
            if prompt_id := fields.pop("prompt_id", None):
                template = require(s, SavedPrompt, prompt_id)
                if template.project_id != fields["project_id"]:
                    raise AgentError("Prompt belongs to another project", 403)
                version = s.scalar(select(PromptVersion).where(PromptVersion.prompt_id == prompt_id,
                                                               PromptVersion.version == template.revision))
                content = version.content
                variables = fields.pop("variables", {})
                missing = {v for v in re.findall(r"\{\{([a-zA-Z_]\w*)\}\}", content) if not variables.get(v, "").strip()}
                if missing:
                    raise AgentError("Missing prompt variables: " + ", ".join(sorted(missing)))
                fields["objective"] = re.sub(r"\{\{([a-zA-Z_]\w*)\}\}", lambda m: variables[m[1]], content)
            else:
                fields.pop("variables", None)
                if re.search(r"\{\{[a-zA-Z_]\w*\}\}", fields["objective"]):
                    raise AgentError("Fill the prompt variables before saving or running the task")
            if parent_id := fields.get("continue_run_id"):
                parent = require(s, AgentRun, parent_id)
                owner = s.scalar(select(Task).join(TaskAttempt, TaskAttempt.task_id == Task.id)
                                 .where(TaskAttempt.run_id == parent_id))
                if not owner or owner.project_id != fields["project_id"] or owner.agent_id != fields["agent_id"]:
                    raise AgentError("Continue requires a run from the same project and agent", 403)
                if parent.status in ACTIVE or not parent.session_id or parent.autonomy != "off":
                    raise AgentError("Continue requires a finished strict-approval session", 409)
                fields["model"] = parent.model
            if not fields["objective"].strip():
                raise AgentError("Task objective is empty")
            ids = fields["context_ids"]
            if len(ids) != len(set(ids)):
                raise AgentError("Duplicate context selections")
            for cid in ids:
                if require(s, ContextItem, cid).project_id != fields["project_id"]:
                    raise AgentError("Context belongs to another project", 403)
            if id:
                row = require(s, Task, id)
                if row.project_id != fields["project_id"]:
                    raise AgentError("A task cannot move to another project", 403)
                if row.status in BUSY:
                    raise AgentError("Cancel the task before editing it", 409)
                revise(s, Task, id, revision, fields)
                row = require(s, Task, id)
            else:
                row = Task(id=str(uuid.uuid4()), **fields)
                s.add(row)
                s.flush()
            data = as_dict(row)
        audit.record(self.db, "task.updated" if id else "task.created", row.id, actor=actor,
                     project_id=row.project_id, agent_id=row.agent_id)
        return data

    def task(self, id: str):
        with self.db.session() as s:
            row = require(s, Task, id)
            data = as_dict(row)
            attempts = s.scalars(select(TaskAttempt).where(TaskAttempt.task_id == id)
                                .order_by(TaskAttempt.id.desc()).limit(25)).all()
            data["attempts"] = [as_dict(a) for a in reversed(attempts)]
            data["attempt_count"] = s.scalar(select(func.count()).select_from(TaskAttempt).where(TaskAttempt.task_id == id))
        if data["run_id"]:
            data["run"] = self.manager().get_run(data["run_id"])
        return data

    async def prepare(self, id: str) -> dict:
        with self.db.session() as s:
            t = as_dict(require(s, Task, id))
            p = as_dict(require(s, Project, t["project_id"]))
            a = as_dict(require(s, AgentProfile, t["agent_id"]))
            items = [as_dict(require(s, ContextItem, cid)) for cid in t["context_ids"]]
        folder = self.manager().resolve_cwd(p["root"])
        if not a["enabled"]:
            raise AgentError("The assigned agent is disabled", 409)
        models = await self.manager().models()
        model_id = t["model"] or a["model"] or self.manager().settings.droid_default_model
        model = next((m for m in models if m["id"] == model_id), None)
        if not model:
            raise AgentError("The selected model is not available", 409)
        sections = [("Objective", t["objective"]), ("Requirements", t["requirements"]),
                    ("Acceptance criteria", t["acceptance"]), ("Agent instructions (untrusted)", a["instructions"])]
        if t["include_instructions"]:
            sections.append(("Project instructions (untrusted)", p["instructions"]))
        if t["include_architecture"]:
            sections.append(("Architecture (untrusted)", p["architecture"]))
        sources = []
        for item in items:
            if item["project_id"] != t["project_id"]:
                raise AgentError("Context belongs to another project", 403)
            text = item["content"]
            if item["kind"] == "file":
                _, text = context_file(folder, item["path"])
                if digest(text) != item["source_hash"]:
                    raise AgentError(f"Context changed: {item['title']}. Refresh the attachment before starting.", 409)
            sources.append({k: item[k] for k in ("id", "title", "kind", "path", "source_hash", "source_commit", "revision")})
            sections.append((f"Selected context: {item['title']} (untrusted)", redact(text)))
        prompt = "\n\n".join(f"## {label}\n{text}" for label, text in sections if text)
        if len(prompt) > MAX_CONTEXT:
            raise AgentError(f"Selected context exceeds {MAX_CONTEXT:,} characters; select fewer files")
        snapshot = {"prompt": redact(prompt), "model": model["id"], "location": model["location"], "cwd": str(folder),
                "sources": sources, "project_revision": p["revision"], "agent_revision": a["revision"],
                "task_revision": t["revision"], "estimated_prompt_tokens": (len(prompt) + 3) // 4,
                "estimate_note": "Approximate prompt tokens only. Droid tool/system context and output are additional; price unknown."}
        snapshot["preview_hash"] = digest(json.dumps(snapshot, sort_keys=True))
        return snapshot

    async def enqueue(self, id: str, revision: int, allow_cloud: bool, preview_hash: str, actor: str):
        async with self.lock:
            with self.db.session() as s:
                t = require(s, Task, id)
                if t.revision != revision or t.status in BUSY:
                    raise AgentError("Task changed or is already active; refresh first", 409)
            snapshot = await self.prepare(id)
            if snapshot["preview_hash"] != preview_hash:
                raise AgentError("Model or context changed after preview; review it again before starting", 409)
            if snapshot["location"] != "local" and not allow_cloud:
                raise AgentError("Cloud inference needs explicit consent before starting", 403)
            with self.db.session() as s:
                revise(s, Task, id, revision, {"status": "queued", "queued_at": utcnow(), "run_id": None,
                                               "error": None, "snapshot": snapshot, "allow_cloud": allow_cloud})
            audit.record(self.db, "task.queued", id, actor=actor, model=snapshot["model"],
                         location=snapshot["location"])
        return self.task(id)

    async def cancel(self, id: str, actor: str):
        async with self.lock:
            with self.db.session() as s:
                t = require(s, Task, id)
                if t.status not in BUSY and t.status != "draft":
                    raise AgentError("Task is already finished", 409)
                run_id = t.run_id
                t.status, t.error, t.revision = "cancelled", "Cancelled by the user", t.revision + 1
            if run_id and self.manager().get_run(run_id)["status"] in ACTIVE:
                await self.manager().stop(run_id, actor=actor)
            audit.record(self.db, "task.cancelled", id, actor=actor)
        return self.task(id)

    async def dispatch(self):
        async with self.lock:
            with self.db.session() as s:
                active = s.scalars(select(Task).where(Task.status.in_(ACTIVE))).all()
                for t in active:
                    if t.run_id:
                        run = self.manager().get_run(t.run_id)
                        if t.status != run["status"]:
                            t.status, t.error, t.revision = run["status"], run["error"], t.revision + 1
                busy_projects = {t.project_id for t in active if t.status in ACTIVE}
                queued = [as_dict(t) for t in s.scalars(select(Task).where(Task.status == "queued")
                                                       .order_by(Task.queued_at, Task.id)).all()]
            for t in queued:
                if t["project_id"] in busy_projects:
                    continue
                snapshot = t["snapshot"]
                try:
                    with self.db.session() as s:
                        a = require(s, AgentProfile, t["agent_id"])
                        if not a.enabled:
                            raise AgentError("Assigned agent was disabled while the task was queued", 409)
                    self.manager().resolve_cwd(snapshot["cwd"])
                    catalog = await self.manager().models(refresh=True)
                    model = next((m for m in catalog if m["id"] == snapshot["model"]), None)
                    if not model or model["location"] != snapshot["location"]:
                        raise AgentError("Model availability or location changed after consent; review and retry", 409)
                    if model["location"] != "local" and not t["allow_cloud"]:
                        raise AgentError("Cloud inference was not approved for this task", 403)
                    for source in snapshot["sources"]:
                        if source["kind"] == "file":
                            _, text = context_file(Path(snapshot["cwd"]), source["path"])
                            if digest(text) != source["source_hash"]:
                                raise AgentError(f"Context changed while queued: {source['title']}", 409)
                    run = await self.manager().start(snapshot["prompt"], snapshot["model"], "off", snapshot["cwd"],
                                                     continue_run_id=t.get("continue_run_id"), expected_location=snapshot["location"])
                except AgentError as e:
                    if str(e).startswith("Too many agent runs"):
                        return
                    with self.db.session() as s:
                        row = require(s, Task, t["id"])
                        row.status, row.error, row.revision = "failed", str(e), row.revision + 1
                    continue
                with self.db.session() as s:
                    row = require(s, Task, t["id"])
                    row.run_id, row.status, row.revision = run["id"], run["status"], row.revision + 1
                    s.add(TaskAttempt(task_id=row.id, run_id=run["id"], snapshot=snapshot))
                audit.record(self.db, "task.started", t["id"], actor="system", run_id=run["id"],
                             project_id=t["project_id"], agent_id=t["agent_id"])
                busy_projects.add(t["project_id"])

    async def run_queue(self):
        while True:
            try:
                await self.dispatch()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Task queue reconciliation failed")
            await asyncio.sleep(0.5)

    async def shutdown(self):
        if self.worker:
            self.worker.cancel()
            try:
                await self.worker
            except asyncio.CancelledError:
                pass
