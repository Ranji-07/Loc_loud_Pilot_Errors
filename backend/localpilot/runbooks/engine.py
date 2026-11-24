from __future__ import annotations

import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select

from .. import audit
from ..config import Settings
from ..db import Database
from ..models import RunbookRun, StepRun, utcnow
from ..policy import RISK_ORDER, CommandPolicy, PolicyDecision
from ..redact import redact
from .schema import Runbook, Step

log = logging.getLogger("localpilot.runbooks")

MAX_LIVE_LINES = 5000
_CURSOR_HOME = re.compile(r"\x1b\[\d*G")
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\x1b[@-Z\\-_]")
TERMINAL = {"succeeded", "failed", "stopped", "skipped", "interrupted"}


class RunbookError(Exception):
    status_code = 400

    def __init__(self, message: str, *, status_code: int | None = None, detail: dict | None = None) -> None:
        super().__init__(message)
        if status_code:
            self.status_code = status_code
        self.detail = detail or {}


@dataclass
class LiveStep:
    run_id: str
    step_id: str
    process: subprocess.Popen | None = None
    lines: list[str] = field(default_factory=list)
    dropped: int = 0
    stop_requested: bool = False
    timed_out: bool = False
    done: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def append(self, line: str) -> None:
        with self.lock:
            self.lines.append(line)
            if len(self.lines) > MAX_LIVE_LINES:
                extra = len(self.lines) - MAX_LIVE_LINES
                del self.lines[:extra]
                self.dropped += extra

    def read(self, offset: int) -> tuple[list[str], int]:
        with self.lock:
            start = max(0, offset - self.dropped)
            return self.lines[start:], self.dropped + len(self.lines)


def shell_argv(command: str) -> list[str]:
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if pwsh:
        prefix = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; $ProgressPreference='SilentlyContinue'; "
                  "if ($PSStyle) { $PSStyle.OutputRendering = 'PlainText' }; ")
        # pwsh -Command reports only success/failure (0/1); re-raise the native exit code so step results are exact.
        suffix = "\n$__ok = $?; if (-not $__ok) { if ($LASTEXITCODE) { exit $LASTEXITCODE } else { exit 1 } }"
        return [pwsh, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "RemoteSigned", "-Command",
                prefix + command + suffix]
    return ["bash", "-lc", command]


def clean_line(line: str) -> str:
    """Drop terminal control codes; for spinner-style \r redraws keep only the final frame."""
    line = _CURSOR_HOME.sub("\r", line.rstrip("\r\n"))
    line = _ANSI.sub("", line)
    if "\r" in line:
        line = line.rsplit("\r", 1)[-1]
    return line


def kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


class RunbookEngine:
    def __init__(self, settings: Settings, db: Database, policy: CommandPolicy, runbooks: dict[str, Runbook]) -> None:
        self.settings = settings
        self.db = db
        self.policy = policy
        self.runbooks = runbooks
        self._live: dict[tuple[str, str], LiveStep] = {}
        self._lock = threading.Lock()

    # ---- lifecycle -------------------------------------------------------
    def recover(self) -> int:
        """Mark steps that were running when the server stopped as interrupted."""
        with self.db.session() as s:
            rows = s.scalars(select(StepRun).where(StepRun.status == "running")).all()
            for r in rows:
                r.status = "interrupted"
                r.finished_at = utcnow()
                r.output = (r.output or "") + "\n[LocalPilot restarted while this step was running]"
        if rows:
            audit.record(self.db, "runbook.recovered", "engine", actor="system", steps=len(rows))
        return len(rows)

    def shutdown(self) -> None:
        for live in list(self._live.values()):
            if live.process and live.process.poll() is None:
                live.stop_requested = True
                kill_tree(live.process)

    # ---- queries ---------------------------------------------------------
    def runbook(self, runbook_id: str) -> Runbook:
        try:
            return self.runbooks[runbook_id]
        except KeyError:
            raise RunbookError(f"Unknown runbook {runbook_id}", status_code=404)

    def list_runs(self, runbook_id: str | None = None) -> list[dict]:
        with self.db.session() as s:
            q = select(RunbookRun).order_by(RunbookRun.created_at.desc()).limit(50)
            if runbook_id:
                q = q.where(RunbookRun.runbook_id == runbook_id)
            return [self._run_dict(s, r) for r in s.scalars(q).all()]

    def get_run(self, run_id: str) -> dict:
        with self.db.session() as s:
            run = s.get(RunbookRun, run_id)
            if not run:
                raise RunbookError("Unknown run", status_code=404)
            return self._run_dict(s, run)

    def _run_dict(self, s, run: RunbookRun) -> dict:
        rb = self.runbooks.get(run.runbook_id)
        rows = {r.step_id: r for r in s.scalars(select(StepRun).where(StepRun.run_id == run.id)).all()}
        steps = []
        for step in rb.steps if rb else []:
            row = rows.get(step.id)
            decision = self.policy.evaluate(step.command, step.risk)
            steps.append({
                "id": step.id,
                "title": step.title,
                "explain": step.explain,
                "command": step.command,
                "expected": step.expected,
                "check": step.check,
                "rollback": step.rollback,
                "optional": step.optional,
                "long_running": step.long_running,
                "cwd": step.cwd,
                "declared_risk": step.risk,
                "policy": decision.to_dict(),
                "status": row.status if row else "pending",
                "executed_command": row.command if row else None,
                "modified": row.modified if row else False,
                "exit_code": row.exit_code if row else None,
                "started_at": _iso(row.started_at) if row else None,
                "finished_at": _iso(row.finished_at) if row else None,
            })
        required = [st for st in steps if not st["optional"]]
        status = "completed" if required and all(st["status"] in ("succeeded", "skipped") for st in required) else "active"
        return {
            "id": run.id,
            "runbook_id": run.runbook_id,
            "title": rb.title if rb else run.runbook_id,
            "status": status,
            "created_at": _iso(run.created_at),
            "steps": steps,
        }

    # ---- commands --------------------------------------------------------
    def start_run(self, runbook_id: str) -> dict:
        self.runbook(runbook_id)
        run_id = str(uuid.uuid4())
        with self.db.session() as s:
            s.add(RunbookRun(id=run_id, runbook_id=runbook_id))
        audit.record(self.db, "runbook.started", f"{runbook_id}/{run_id}")
        return self.get_run(run_id)

    def _load(self, run_id: str, step_id: str) -> tuple[Runbook, Step]:
        with self.db.session() as s:
            run = s.get(RunbookRun, run_id)
            if not run:
                raise RunbookError("Unknown run", status_code=404)
            rb = self.runbook(run.runbook_id)
        try:
            return rb, rb.step(step_id)
        except KeyError:
            raise RunbookError(f"Unknown step {step_id}", status_code=404)

    def evaluate(self, run_id: str, step_id: str, command: str | None) -> PolicyDecision:
        _, step = self._load(run_id, step_id)
        return self.policy.evaluate(command if command is not None else step.command, step.risk)

    def execute(self, run_id: str, step_id: str, *, approved: bool, command: str | None = None,
                confirm_high_risk: bool = False) -> dict:
        _, step = self._load(run_id, step_id)
        if not approved:
            raise RunbookError("Strict approval mode: the step must be explicitly approved", status_code=400)
        final = (command if command is not None else step.command).strip()
        modified = final != step.command.strip()
        decision = self.policy.evaluate(final, step.risk)
        if not decision.allowed:
            audit.record(self.db, "step.blocked", f"{run_id}/{step_id}", command=final, reasons=decision.reasons)
            raise RunbookError("Command blocked by policy", status_code=403, detail=decision.to_dict())
        if RISK_ORDER[decision.risk] >= RISK_ORDER["high"] and not confirm_high_risk:
            raise RunbookError("High-risk step needs confirm_high_risk=true", status_code=428, detail=decision.to_dict())

        key = (run_id, step_id)
        with self._lock:
            existing = self._live.get(key)
            if existing and not existing.done.is_set():
                raise RunbookError("Step is already running", status_code=409)
            live = LiveStep(run_id, step_id)
            self._live[key] = live

        with self.db.session() as s:
            row = s.scalars(select(StepRun).where(StepRun.run_id == run_id, StepRun.step_id == step_id)).first()
            if not row:
                row = StepRun(run_id=run_id, step_id=step_id)
                s.add(row)
            row.status = "running"
            row.original_command = step.command
            row.command = final
            row.modified = modified
            row.risk = decision.risk
            row.exit_code = None
            row.output = ""
            row.started_at = utcnow()
            row.finished_at = None
        audit.record(self.db, "step.executed", f"{run_id}/{step_id}", command=final, modified=modified,
                     original=step.command if modified else None, risk=decision.risk)

        timeout = None if step.long_running else (step.timeout or self.settings.step_timeout_seconds)
        try:
            self._spawn(live, final, timeout, self._cwd(step))
        except OSError as e:
            live.append(f"[failed to start: {e}]")
            self._finish(live, None)
        return self.get_run(run_id)

    def _cwd(self, step: Step):
        return (self.settings.repo_root / step.cwd).resolve() if step.cwd else self.settings.repo_root

    def _spawn(self, live: LiveStep, command: str, timeout: int | None, cwd) -> None:
        env = os.environ.copy()
        env["LOCALPILOT_DATA_DIR"] = str(self.settings.data_dir)
        env["LOCALPILOT_AWS_REGION"] = self.settings.aws_region
        env.setdefault("NO_COLOR", "1")
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            shell_argv(command), cwd=cwd, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1, **kwargs,
        )
        live.process = proc
        log.info("step started", extra={"run": live.run_id, "step": live.step_id, "pid": proc.pid})

        def reader() -> None:
            assert proc.stdout
            for line in proc.stdout:
                cleaned = clean_line(line)
                if cleaned.strip():
                    live.append(redact(cleaned))
            rc = proc.wait()
            self._finish(live, rc)

        def watchdog() -> None:
            if not live.done.wait(timeout):
                live.timed_out = True
                live.append(f"[timed out after {timeout}s]")
                kill_tree(proc)

        threading.Thread(target=reader, daemon=True, name=f"step-{live.step_id}").start()
        if timeout:
            threading.Thread(target=watchdog, daemon=True).start()

    def _finish(self, live: LiveStep, rc: int | None) -> None:
        if live.stop_requested:
            status = "stopped"
        elif rc == 0 and not live.timed_out:
            status = "succeeded"
        else:
            status = "failed"
        lines, _ = live.read(0)
        with self.db.session() as s:
            row = s.scalars(select(StepRun).where(StepRun.run_id == live.run_id, StepRun.step_id == live.step_id)).first()
            if row:
                row.status = status
                row.exit_code = rc
                row.output = "\n".join(lines[-2000:])
                row.finished_at = utcnow()
        live.done.set()
        audit.record(self.db, f"step.{status}", f"{live.run_id}/{live.step_id}", actor="system", exit_code=rc)

    def stop(self, run_id: str, step_id: str) -> dict:
        self._load(run_id, step_id)
        live = self._live.get((run_id, step_id))
        if not live or live.done.is_set() or not live.process:
            raise RunbookError("Step is not running", status_code=409)
        live.stop_requested = True
        audit.record(self.db, "step.stop_requested", f"{run_id}/{step_id}")
        kill_tree(live.process)
        live.done.wait(10)
        return self.get_run(run_id)

    def skip(self, run_id: str, step_id: str) -> dict:
        _, step = self._load(run_id, step_id)
        live = self._live.get((run_id, step_id))
        if live and not live.done.is_set():
            raise RunbookError("Stop the step before skipping it", status_code=409)
        with self.db.session() as s:
            row = s.scalars(select(StepRun).where(StepRun.run_id == run_id, StepRun.step_id == step_id)).first()
            if not row:
                row = StepRun(run_id=run_id, step_id=step_id, original_command=step.command)
                s.add(row)
            row.status = "skipped"
            row.finished_at = utcnow()
        audit.record(self.db, "step.skipped", f"{run_id}/{step_id}")
        return self.get_run(run_id)

    def output(self, run_id: str, step_id: str, offset: int = 0) -> dict:
        self._load(run_id, step_id)
        live = self._live.get((run_id, step_id))
        if live:
            lines, nxt = live.read(offset)
            return {"lines": lines, "next": nxt, "done": live.done.is_set()}
        with self.db.session() as s:
            row = s.scalars(select(StepRun).where(StepRun.run_id == run_id, StepRun.step_id == step_id)).first()
            stored = row.output.split("\n") if row and row.output else []
        return {"lines": stored[offset:], "next": len(stored), "done": True}

    def check(self, run_id: str, step_id: str, *, approved: bool) -> dict:
        _, step = self._load(run_id, step_id)
        if not step.check:
            raise RunbookError("This step has no verification command", status_code=404)
        if not approved:
            raise RunbookError("Strict approval mode: verification must be approved", status_code=400)
        decision = self.policy.evaluate(step.check, "low")
        if not decision.allowed:
            raise RunbookError("Verification command blocked by policy", status_code=403, detail=decision.to_dict())
        try:
            res = subprocess.run(shell_argv(step.check), cwd=self._cwd(step), capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=90)
            out = redact("\n".join(clean_line(x) for x in (res.stdout + res.stderr).strip().splitlines()))
            passed = res.returncode == 0
        except subprocess.TimeoutExpired:
            out, passed = "[verification timed out]", False
        audit.record(self.db, "step.verified", f"{run_id}/{step_id}", passed=passed)
        return {"passed": passed, "output": out[-4000:]}


def _iso(dt) -> str | None:
    return dt.isoformat() + "Z" if dt else None
