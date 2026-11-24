from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select

from . import __version__, catalog, health
from .models import AuditEvent, ModelCall, UsageSnapshot
from .runbooks.engine import RunbookEngine
from .usage import probes, rules, summarizer

router = APIRouter(prefix="/api/v1")
AUDIT_EXPORT_MAX = 10_000


class ExecuteBody(BaseModel):
    approved: bool
    command: str | None = None
    confirm_high_risk: bool = False


class ApproveBody(BaseModel):
    approved: bool


class EvaluateBody(BaseModel):
    command: str | None = None


def _engine(req: Request) -> RunbookEngine:
    return req.app.state.engine


@router.get("/health")
async def get_health(req: Request) -> dict[str, Any]:
    checks = await health.run_all(req.app.state.settings, req.app.state.db)
    worst = "ok"
    if any(c["status"] == "error" for c in checks):
        worst = "error"
    elif any(c["status"] == "warn" for c in checks):
        worst = "warn"
    return {"version": __version__, "status": worst, "checks": checks}


@router.get("/runbooks")
def list_runbooks(req: Request) -> list[dict[str, Any]]:
    return [{"id": rb.id, "title": rb.title, "summary": rb.summary, "category": rb.category,
             "steps": len(rb.steps)} for rb in _engine(req).runbooks.values()]


@router.get("/runbooks/{runbook_id}")
def get_runbook(runbook_id: str, req: Request) -> dict[str, Any]:
    eng = _engine(req)
    rb = eng.runbook(runbook_id)
    return {**rb.model_dump(), "runs": eng.list_runs(runbook_id)}


@router.post("/runbooks/{runbook_id}/runs")
def start_run(runbook_id: str, req: Request) -> dict[str, Any]:
    return _engine(req).start_run(runbook_id)


@router.get("/runs")
def list_runs(req: Request) -> list[dict[str, Any]]:
    return _engine(req).list_runs()


@router.get("/runs/{run_id}")
def get_run(run_id: str, req: Request) -> dict[str, Any]:
    return _engine(req).get_run(run_id)


@router.post("/runs/{run_id}/steps/{step_id}/evaluate")
def evaluate(run_id: str, step_id: str, body: EvaluateBody, req: Request) -> dict[str, Any]:
    return _engine(req).evaluate(run_id, step_id, body.command).to_dict()


@router.post("/runs/{run_id}/steps/{step_id}/execute")
def execute(run_id: str, step_id: str, body: ExecuteBody, req: Request) -> dict[str, Any]:
    return _engine(req).execute(run_id, step_id, approved=body.approved, command=body.command,
                                confirm_high_risk=body.confirm_high_risk)


@router.post("/runs/{run_id}/steps/{step_id}/stop")
def stop(run_id: str, step_id: str, req: Request) -> dict[str, Any]:
    return _engine(req).stop(run_id, step_id)


@router.post("/runs/{run_id}/steps/{step_id}/skip")
def skip(run_id: str, step_id: str, req: Request) -> dict[str, Any]:
    return _engine(req).skip(run_id, step_id)


@router.post("/runs/{run_id}/steps/{step_id}/check")
def check(run_id: str, step_id: str, body: ApproveBody, req: Request) -> dict[str, Any]:
    return _engine(req).check(run_id, step_id, approved=body.approved)


@router.get("/runs/{run_id}/steps/{step_id}/output")
def output(run_id: str, step_id: str, req: Request, offset: int = Query(0, ge=0)) -> dict[str, Any]:
    return _engine(req).output(run_id, step_id, offset)


@router.get("/runs/{run_id}/steps/{step_id}/stream")
async def stream(run_id: str, step_id: str, req: Request, offset: int = Query(0, ge=0)) -> StreamingResponse:
    eng = _engine(req)
    eng.output(run_id, step_id, 0)  # validates ids before streaming starts

    async def gen():
        pos = offset
        while True:
            if await req.is_disconnected():
                return
            chunk = eng.output(run_id, step_id, pos)
            if chunk["lines"]:
                pos = chunk["next"]
                yield f"data: {json.dumps({'lines': chunk['lines'], 'next': pos})}\n\n"
            if chunk["done"]:
                yield f"event: end\ndata: {json.dumps({'next': pos})}\n\n"
                return
            await asyncio.sleep(0.3)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/usage")
async def usage(req: Request, include_aws: bool = True, include_remote: bool = True) -> dict[str, Any]:
    s = req.app.state.settings
    pricing = probes.load_pricing(s.pricing_file)
    local, gpu, oll = await asyncio.gather(
        asyncio.to_thread(probes.local_system, s),
        asyncio.to_thread(probes.local_gpu),
        probes.ollama_state(s.ollama_url),
    )
    snapshot: dict[str, Any] = {"local": local, "local_gpu": gpu, "ollama": oll}
    tasks = {}
    if include_aws:
        tasks["aws"] = asyncio.to_thread(probes.aws_instances, s, pricing)
    if include_remote:
        tasks["remote"] = asyncio.to_thread(probes.remote_target, s)
    for k, v in zip(tasks, await asyncio.gather(*tasks.values())):
        snapshot[k] = v
    alerts = rules.evaluate(snapshot)
    with req.app.state.db.session() as sess:
        row = UsageSnapshot(data={**snapshot, "alerts": alerts})
        sess.add(row)
        sess.flush()
        snap_id = row.id
    return {"id": snap_id, **snapshot, "alerts": alerts}


@router.post("/usage/{snapshot_id}/summary")
async def usage_summary(snapshot_id: int, req: Request) -> dict[str, Any]:
    with req.app.state.db.session() as sess:
        row = sess.get(UsageSnapshot, snapshot_id)
        if not row:
            raise HTTPException(404, "Unknown snapshot")
        data = dict(row.data)
    facts = rules.compact_facts(data, data.get("alerts", []))
    return {"facts": facts, **await summarizer.summarize(req.app.state.settings, req.app.state.db, facts)}


@router.get("/usage/model-calls")
def model_calls(req: Request, since: datetime | None = None) -> dict[str, Any]:
    """Totals per model; `since` (ISO date or datetime, UTC) limits the window, e.g. the start of the month."""
    q = select(ModelCall.model, ModelCall.provider, func.count(), func.sum(ModelCall.prompt_tokens),
               func.sum(ModelCall.completion_tokens), func.sum(ModelCall.cost_usd), func.sum(ModelCall.credits))
    since = _naive_utc(since)
    if since is not None:
        q = q.where(ModelCall.at >= since)
    day = func.date(ModelCall.at)
    daily = (select(day, ModelCall.provider, func.count(), func.sum(ModelCall.credits))
             .group_by(day, ModelCall.provider).order_by(day))
    if since is not None:
        daily = daily.where(ModelCall.at >= since)
    with req.app.state.db.session() as s:
        rows = s.execute(q.group_by(ModelCall.model, ModelCall.provider)).all()
        day_rows = s.execute(daily).all()
    by_model = [{"model": m, "provider": p, "location": _location(p), "calls": n,
                 "prompt_tokens": pt or 0, "completion_tokens": ct or 0, "cost_usd": round(c or 0, 6),
                 "credits": round(cr or 0, 2)} for m, p, n, pt, ct, c, cr in rows]
    totals = {loc: {"calls": sum(r["calls"] for r in by_model if r["location"] == loc),
                    "cost_usd": round(sum(r["cost_usd"] for r in by_model if r["location"] == loc), 6),
                    "credits": round(sum(r["credits"] for r in by_model if r["location"] == loc), 2)}
              for loc in ("local", "cloud")}
    days: dict[str, dict[str, Any]] = {}
    for d, p, n, cr in day_rows:
        row = days.setdefault(str(d), {"day": str(d), "local_calls": 0, "cloud_calls": 0, "credits": 0.0})
        row[f"{_location(p)}_calls"] += n
        row["credits"] = round(row["credits"] + (cr or 0), 2)
    return {"since": since.isoformat() + "Z" if since else None, "by_model": by_model, "totals": totals,
            "by_day": list(days.values())}


def _location(provider: str) -> str:
    # Cache hits replay a local model's earlier answer, so they are free and local.
    return "local" if provider in ("ollama", "cache") else "cloud"


def _naive_utc(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _audit_query(action: str | None, actor: str | None, q: str | None, since: datetime | None,
                 until: datetime | None, before: int | None):
    stmt = select(AuditEvent).order_by(AuditEvent.id.desc())
    if action:
        stmt = stmt.where(AuditEvent.action.startswith(action, autoescape=True))
    if actor:
        stmt = stmt.where(AuditEvent.actor.startswith(actor, autoescape=True))
    if q:
        stmt = stmt.where(AuditEvent.action.contains(q, autoescape=True) | AuditEvent.target.contains(q, autoescape=True))
    if since := _naive_utc(since):
        stmt = stmt.where(AuditEvent.at >= since)
    if until := _naive_utc(until):
        stmt = stmt.where(AuditEvent.at < until)
    if before is not None:
        stmt = stmt.where(AuditEvent.id < before)
    return stmt


def _audit_dict(r: AuditEvent) -> dict[str, Any]:
    return catalog._scrub({"id": r.id, "at": r.at.isoformat() + "Z", "actor": r.actor, "action": r.action,
                          "target": r.target, "detail": r.detail})


@router.get("/audit")
def audit_log(req: Request, limit: int = Query(100, ge=1, le=1000), before: int | None = Query(None, ge=1),
              action: str | None = None, actor: str | None = None, q: str | None = None,
              since: datetime | None = None, until: datetime | None = None) -> list[dict[str, Any]]:
    """Newest first. `action`/`actor` are prefixes (e.g. `approval.`), `q` searches action and target,
    `before` is the id of the last row already shown (cursor paging)."""
    with req.app.state.db.session() as s:
        rows = s.scalars(_audit_query(action, actor, q, since, until, before).limit(limit)).all()
        return [_audit_dict(r) for r in rows]


@router.get("/audit/actions")
def audit_actions(req: Request) -> list[dict[str, Any]]:
    with req.app.state.db.session() as s:
        rows = s.execute(select(AuditEvent.action, func.count()).group_by(AuditEvent.action)
                         .order_by(AuditEvent.action)).all()
    return [{"action": a, "count": n} for a, n in rows]


@router.get("/audit/export")
def audit_export(req: Request, format: str = Query("csv", pattern="^(csv|json)$"), action: str | None = None,
                 actor: str | None = None, q: str | None = None, since: datetime | None = None,
                 until: datetime | None = None) -> Response:
    with req.app.state.db.session() as s:
        rows = [_audit_dict(r) for r in s.scalars(_audit_query(action, actor, q, since, until, None)
                                                  .limit(AUDIT_EXPORT_MAX + 1)).all()]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    headers = {"Content-Disposition": f'attachment; filename="localpilot-history-{stamp}.{format}"'}
    headers["X-LocalPilot-Export-Truncated"] = str(len(rows) > AUDIT_EXPORT_MAX).lower()
    rows = rows[:AUDIT_EXPORT_MAX]
    if format == "json":
        return Response(json.dumps(rows, indent=2), media_type="application/json", headers=headers)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "at", "actor", "action", "target", "detail"])
    for r in rows:
        values = [r["id"], r["at"], r["actor"], r["action"], r["target"], json.dumps(r["detail"])]
        # Spreadsheet apps interpret even quoted CSV cells as formulas.
        w.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v for v in values])
    return Response(buf.getvalue(), media_type="text/csv", headers=headers)


@router.get("/models")
async def models_catalog(req: Request) -> dict[str, Any]:
    return catalog._scrub(await catalog.catalog(req.app.state.settings, req.app.state.db, req.app.state.droid.models()))


@router.get("/settings")
def settings_view(req: Request) -> dict[str, Any]:
    return catalog.settings_view(req.app.state.settings)


@router.get("/system/logs")
def system_logs(req: Request, lines: int = Query(200, ge=1, le=2000)) -> dict[str, Any]:
    return catalog.log_tail(req.app.state.settings, lines)
