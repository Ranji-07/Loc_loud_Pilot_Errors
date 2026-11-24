from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .droid import DroidManager

router = APIRouter(prefix="/api/v1")


class StartBody(BaseModel):
    prompt: str
    model: str | None = None
    autonomy: str = "off"
    cwd: str | None = None
    continue_run_id: str | None = None


class DecideBody(BaseModel):
    decision: str
    comment: str | None = None


def _mgr(req: Request) -> DroidManager:
    return req.app.state.droid


def _actor(req: Request) -> str:
    client = req.headers.get("x-localpilot-surface", "dashboard")
    return f"user:{client}"[:40]


@router.get("/agents/models")
async def agent_models(req: Request, refresh: bool = False) -> dict[str, Any]:
    m = _mgr(req)
    return {"default": m.settings.droid_default_model, "models": await m.models(refresh),
            "workspaces": [str(w) for w in m.settings.agent_workspaces]}


@router.get("/agents/runs")
def agent_runs(req: Request, limit: int = Query(50, ge=1, le=500)) -> list[dict[str, Any]]:
    return _mgr(req).list_runs(limit)


@router.post("/agents/runs")
async def agent_start(body: StartBody, req: Request) -> dict[str, Any]:
    return await _mgr(req).start(body.prompt, body.model, body.autonomy, body.cwd, body.continue_run_id)


@router.get("/agents/runs/{run_id}")
def agent_run(run_id: str, req: Request) -> dict[str, Any]:
    return _mgr(req).get_run(run_id)


@router.get("/agents/runs/{run_id}/events")
def agent_events(run_id: str, req: Request, after: int = Query(0, ge=0)) -> dict[str, Any]:
    return _mgr(req).events(run_id, after)


@router.get("/agents/runs/{run_id}/stream")
async def agent_stream(run_id: str, req: Request, after: int = Query(0, ge=0)) -> StreamingResponse:
    m = _mgr(req)
    m.get_run(run_id)

    async def gen():
        pos, last_partial = after, None
        while True:
            if await req.is_disconnected():
                return
            live = m.live(run_id)
            if live:
                live.changed.clear()
            chunk = m.events(run_id, pos)
            if chunk["events"] or chunk["partial"] != last_partial:
                pos, last_partial = chunk["next"], chunk["partial"]
                yield f"data: {json.dumps({**chunk, 'run': m.get_run(run_id)})}\n\n"
            if not chunk["active"]:
                yield f"event: end\ndata: {json.dumps({'next': pos, 'run': m.get_run(run_id)})}\n\n"
                return
            try:
                await asyncio.wait_for(live.changed.wait(), 15) if live else await asyncio.sleep(0.5)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/agents/runs/{run_id}/stop")
async def agent_stop(run_id: str, req: Request) -> dict[str, Any]:
    return await _mgr(req).stop(run_id, actor=_actor(req))


@router.get("/approvals")
def approvals(req: Request, status: str | None = None, limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
    return _mgr(req).list_approvals(status, limit)


@router.get("/approvals/{approval_id}")
def approval(approval_id: str, req: Request) -> dict[str, Any]:
    return _mgr(req).get_approval(approval_id)


@router.post("/approvals/{approval_id}/decide")
async def decide(approval_id: str, body: DecideBody, req: Request) -> dict[str, Any]:
    return _mgr(req).decide(approval_id, body.decision, body.comment, actor=_actor(req))
