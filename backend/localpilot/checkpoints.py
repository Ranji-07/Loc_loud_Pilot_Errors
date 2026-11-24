from __future__ import annotations

import base64
import hashlib
import os
import subprocess
import tempfile
import threading
import uuid
from functools import wraps
from pathlib import Path

from sqlalchemy import select

from . import audit
from .agents.droid import ACTIVE, AgentError
from .models import AgentRun, FileCheckpoint
from .redact import redact


def hash_bytes(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def synchronized(fn):
    @wraps(fn)
    def call(self, *args, **kwargs):
        with self.lock:
            return fn(self, *args, **kwargs)
    return call


def safe_path(root: Path, value: str) -> Path:
    root = root.resolve()
    target = (root / value).resolve()
    if not target.is_relative_to(root) or target == root:
        raise AgentError("File action is outside the run workspace", 403)
    parts = [p.lower() for p in target.relative_to(root).parts]
    if any(p in (".git", ".factory", ".ssh", "secrets", ".venv", "node_modules") or p.startswith(".env") or
           ":" in p or p in ("credentials", "id_rsa", "id_ed25519") or
           p.endswith((".key", ".pem", ".p12", ".pfx")) for p in parts):
        raise AgentError("Secret or internal files cannot be changed through LocalPilot", 403)
    return target


def read_file(path: Path) -> bytes | None:
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise AgentError("Checkpoint requires a regular file no larger than 1 MiB")
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise AgentError("Checkpoint requires UTF-8 text") from None
    if "\0" in text or redact(text) != text:
        raise AgentError("Binary files or secret contents cannot be checkpointed")
    return data


def git_clean(root: Path, target: Path):
    try:
        is_git = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, timeout=5)
        if is_git.returncode != 0:
            return
        r = subprocess.run(["git", "-C", str(root), "-c", "core.fsmonitor=false", "status", "--porcelain",
                            "--untracked-files=all", "--ignored", "--", target.relative_to(root).as_posix()],
                           capture_output=True, timeout=5)
        if r.returncode or r.stdout.strip():
            raise AgentError("This file has uncommitted changes. Commit or move your work before approving.", 409)
    except (OSError, subprocess.TimeoutExpired):
        raise AgentError("Cannot check Git status safely; file approval is blocked", 409) from None


class Checkpoints:
    def __init__(self, db, resolve_cwd):
        self.db, self.resolve_cwd = db, resolve_cwd
        self.lock = threading.RLock()

    @synchronized
    def prepare(self, run_id: str, approval_id: str, cwd: str, actions) -> str:
        root = self.resolve_cwd(cwd)
        files = []
        seen = set()
        for action in actions:
            kind = type(action).__name__
            if kind not in ("CreateFile", "EditAction", "ApplyPatchAction"):
                continue
            changes = getattr(action, "files", None) or [action]
            for change in changes:
                if getattr(change, "move_to", None):
                    raise AgentError("Rename checkpoint is unavailable; use an explicit approved Git workflow")
                value = getattr(change, "file_path", "")
                if not value:
                    raise AgentError("File action did not supply affected paths")
                target = safe_path(root, value)
                if target in seen:
                    raise AgentError("Approval repeats the same file path")
                seen.add(target)
                before = read_file(target)
                operation = getattr(change, "operation", "create" if kind == "CreateFile" else "update")
                if operation == "create" and before is not None:
                    raise AgentError("Creating this file would overwrite existing work", 409)
                git_clean(root, target)
                old = getattr(change, "old_content", None)
                if old is not None and before is not None and before.decode("utf-8") != old:
                    raise AgentError("File differs from the proposed before-content; ask for a fresh proposal", 409)
                new = getattr(change, "content", None) if kind == "CreateFile" else getattr(change, "new_content", None)
                if new is not None and redact(new) != new:
                    raise AgentError("Proposed file contents contain a secret", 403)
                files.append({"path": target.relative_to(root).as_posix(), "requested_path": os.path.abspath(root / value),
                              "tool_use_id": getattr(getattr(action, "tool_use", None), "id", None),
                              "before": base64.b64encode(before).decode() if before is not None else None,
                              "before_hash": hash_bytes(before), "after_hash": None,
                              "expected_hash": hash_bytes(new.encode("utf-8")) if new is not None else None,
                              "expected_known": new is not None or operation == "delete",
                              "mode": target.stat().st_mode if before is not None else None})
        if not files:
            raise AgentError("No checkpointable files were supplied")
        id = str(uuid.uuid4())
        with self.db.session() as s:
            s.add(FileCheckpoint(id=id, run_id=run_id, approval_id=approval_id, root=str(root), files=files))
        return id

    @synchronized
    def validate(self, id: str):
        with self.db.session() as s:
            row = s.get(FileCheckpoint, id)
            if not row or row.status != "prepared":
                raise AgentError("Checkpoint is no longer available", 409)
            root = self.resolve_cwd(row.root)
            for f in row.files:
                target = safe_path(root, f["path"])
                if safe_path(root, f["requested_path"]) != target:
                    raise AgentError("File path target changed while approval was pending", 409)
                if hash_bytes(read_file(target)) != f["before_hash"]:
                    raise AgentError("File changed while approval was pending; request a new proposal", 409)
                git_clean(root, target)
            row.status = "approved"

    @synchronized
    def capture(self, run_id: str, finished: bool = False, tool_use_id: str | None = None):
        with self.db.session() as s:
            for row in s.scalars(select(FileCheckpoint).where(FileCheckpoint.run_id == run_id,
                                                               FileCheckpoint.status == "approved")):
                root = self.resolve_cwd(row.root)
                files = [dict(f) for f in row.files]
                try:
                    for f in files:
                        f["after_hash"] = hash_bytes(read_file(safe_path(root, f["path"])))
                    known = tool_use_id is not None and all(f["tool_use_id"] == tool_use_id and f["expected_known"]
                                                           and f["after_hash"] == f["expected_hash"] for f in files)
                    if known:
                        row.files, row.status = files, "completed"
                    elif finished:
                        row.status = "unavailable"
                except (AgentError, OSError):
                    if finished:
                        row.status = "unavailable"

    def list(self, run_id: str):
        with self.db.session() as s:
            rows = s.scalars(select(FileCheckpoint).where(FileCheckpoint.run_id == run_id)
                             .order_by(FileCheckpoint.created_at)).all()
            return [{"id": r.id, "approval_id": r.approval_id, "status": r.status,
                     "files": [{"path": f["path"], "changed": f["before_hash"] != f["after_hash"]} for f in r.files]} for r in rows]

    @synchronized
    def rollback(self, id: str, actor: str):
        with self.db.session() as s:
            row = s.get(FileCheckpoint, id)
            if not row:
                raise AgentError("Unknown checkpoint", 404)
            if row.status not in ("completed", "rollback_partial", "rolling_back"):
                raise AgentError("Checkpoint is not ready for rollback", 409)
            root = self.resolve_cwd(row.root)
            active = s.scalars(select(AgentRun).where(AgentRun.status.in_(ACTIVE))).all()
            if any(Path(r.cwd).resolve().is_relative_to(root) or root.is_relative_to(Path(r.cwd).resolve()) for r in active):
                raise AgentError("Stop active runs in this workspace before rolling back", 409)
            targets = [(safe_path(root, f["path"]), dict(f)) for f in row.files]
            staged = {}
            for target, f in targets:
                expected = f["before_hash"] if f.get("restored") else f["after_hash"]
                if hash_bytes(read_file(target)) != expected:
                    raise AgentError("File changed after this action; rollback would overwrite newer work", 409)
                if f["before"] is not None and not f.get("restored") and not target.parent.is_dir():
                    raise AgentError("A restore parent directory is missing; rollback made no changes", 409)
            try:
                for target, f in targets:
                    if f["before"] is not None and not f.get("restored"):
                        fd, tmp = tempfile.mkstemp(prefix=".localpilot-restore-", dir=target.parent)
                        staged[target] = tmp
                        with os.fdopen(fd, "wb") as out:
                            out.write(base64.b64decode(f["before"]))
                        if f["mode"] is not None:
                            os.chmod(tmp, f["mode"])
                for target, f in targets:
                    expected = f["before_hash"] if f.get("restored") else f["after_hash"]
                    if hash_bytes(read_file(target)) != expected:
                        raise AgentError("File changed during rollback preflight; no files restored", 409)
                row.status = "rolling_back"
                s.commit()
                for target, f in targets:
                    if f.get("restored"):
                        continue
                    if hash_bytes(read_file(target)) != f["after_hash"]:
                        raise AgentError("File changed during rollback", 409)
                    if f["before"] is None:
                        if target.exists():
                            target.unlink()
                    else:
                        os.replace(staged[target], target)
                    f["restored"] = True
                    row.files = [dict(entry) for _, entry in targets]
                    s.commit()
                row.status = "rolled_back"
            except Exception as exc:
                if row.status == "rolling_back":
                    row.status = "rollback_partial"
                    s.commit()
                    audit.record(self.db, "checkpoint.rollback_partial", id, actor=actor, run_id=row.run_id)
                    raise AgentError("Rollback partially applied. Inspect the files, then retry to restore the remaining files.", 409) from exc
                if isinstance(exc, AgentError):
                    raise
                raise AgentError("Rollback preflight failed; no files restored", 409) from exc
            finally:
                for tmp in staged.values():
                    if os.path.exists(tmp):
                        os.unlink(tmp)
            run_id = row.run_id
        audit.record(self.db, "checkpoint.rolled_back", id, actor=actor, run_id=run_id)
        return {"id": id, "status": "rolled_back"}
