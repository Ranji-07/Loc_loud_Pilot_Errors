from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select

from . import __version__, health
from .models import AuditEvent, ModelCall, UsageSnapshot
from .runbooks.engine import RunbookEngine
from .usage import probes, rules, summarizer

router = APIRouter(prefix="/api/v1")


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
    if since is not None:
        if since.tzinfo is not None:
            since = since.astimezone(timezone.utc).replace(tzinfo=None)
        q = q.where(ModelCall.at >= since)
    with req.app.state.db.session() as s:
        rows = s.execute(q.group_by(ModelCall.model, ModelCall.provider)).all()
    by_model = [{"model": m, "provider": p, "location": "local" if p == "ollama" else "cloud", "calls": n,
                 "prompt_tokens": pt or 0, "completion_tokens": ct or 0, "cost_usd": round(c or 0, 6),
                 "credits": round(cr or 0, 2)} for m, p, n, pt, ct, c, cr in rows]
    totals = {loc: {"calls": sum(r["calls"] for r in by_model if r["location"] == loc),
                    "cost_usd": round(sum(r["cost_usd"] for r in by_model if r["location"] == loc), 6),
                    "credits": round(sum(r["credits"] for r in by_model if r["location"] == loc), 2)}
              for loc in ("local", "cloud")}
    return {"since": since.isoformat() + "Z" if since else None, "by_model": by_model, "totals": totals}


@router.get("/audit")
def audit_log(req: Request, limit: int = Query(100, ge=1, le=1000)) -> list[dict[str, Any]]:
    with req.app.state.db.session() as s:
        rows = s.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)).all()
        return [{"id": r.id, "at": r.at.isoformat() + "Z", "actor": r.actor, "action": r.action,
                 "target": r.target, "detail": r.detail} for r in rows]
