from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .agents.droid import AgentError
from .agents.routes import _actor
from .models import AgentProfile, ContextItem, Project, SavedPrompt, Task

router = APIRouter(prefix="/api/v1")


class Fields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def strings(cls, v):
        return v.strip() if isinstance(v, str) else v


class ProjectBody(Fields):
    name: str = Field(min_length=1, max_length=120)
    root: str = Field(min_length=1, max_length=2000)


class ProjectEdit(Fields):
    revision: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    instructions: str = Field(default="", max_length=16000)
    architecture: str = Field(default="", max_length=16000)


class ContextBody(Fields):
    kind: Literal["file", "instructions", "architecture", "decision", "note"]
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=16000)
    path: str | None = Field(default=None, max_length=2000)
    revision: int = Field(default=1, ge=1)


class AgentBody(Fields):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="Coding", min_length=1, max_length=120)
    instructions: str = Field(default="", max_length=16000)
    model: str | None = Field(default=None, max_length=120)
    enabled: bool = True
    revision: int = Field(default=1, ge=1)


class PromptBody(Fields):
    name: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=16000)
    revision: int = Field(default=1, ge=1)


class TaskBody(Fields):
    project_id: str
    agent_id: str = "droid"
    objective: str = Field(default="", max_length=16000)
    requirements: str = Field(default="", max_length=8000)
    acceptance: str = Field(default="", max_length=8000)
    model: str | None = Field(default=None, max_length=120)
    context_ids: list[str] = Field(default_factory=list, max_length=20)
    continue_run_id: str | None = None
    include_instructions: bool = False
    include_architecture: bool = False
    prompt_id: str | None = None
    variables: dict[str, Annotated[str, Field(max_length=8000)]] = Field(default_factory=dict, max_length=20)


class TaskEdit(TaskBody):
    revision: int = Field(ge=1)


class QueueBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    preview_hash: str = Field(min_length=64, max_length=64)
    approved: bool = False
    allow_cloud: bool = False


def ws(req):
    return req.app.state.workspace


@router.get("/projects")
def projects(req: Request, before: str | None = None, limit: int = Query(50, ge=1, le=100)):
    return ws(req).list(Project, before=before, limit=limit)


@router.post("/projects")
def create_project(body: ProjectBody, req: Request):
    return ws(req).create_project(body.name, body.root, _actor(req))


@router.get("/projects/{id}")
def project(id: str, req: Request):
    return ws(req).project(id)


@router.patch("/projects/{id}")
def edit_project(id: str, body: ProjectEdit, req: Request):
    return ws(req).edit(Project, id, body.revision, body.model_dump(exclude={"revision"}), _actor(req))


@router.get("/projects/{id}/context")
def context(id: str, req: Request, before: str | None = None, limit: int = Query(50, ge=1, le=100)):
    ws(req).project(id)
    return ws(req).list(ContextItem, id, before, limit)


@router.post("/projects/{id}/context")
def create_context(id: str, body: ContextBody, req: Request):
    return ws(req).save_context(id, body.model_dump(exclude={"revision"}), _actor(req))


@router.put("/projects/{id}/context/{item_id}")
def edit_context(id: str, item_id: str, body: ContextBody, req: Request):
    return ws(req).save_context(id, body.model_dump(exclude={"revision"}), _actor(req), item_id, body.revision)


@router.get("/agent-profiles")
def profiles(req: Request, before: str | None = None, limit: int = Query(50, ge=1, le=100)):
    return ws(req).list(AgentProfile, before=before, limit=limit)


@router.post("/agent-profiles")
def create_profile(body: AgentBody, req: Request):
    return ws(req).create_agent(body.model_dump(exclude={"revision"}), _actor(req))


@router.patch("/agent-profiles/{id}")
def edit_profile(id: str, body: AgentBody, req: Request):
    return ws(req).edit(AgentProfile, id, body.revision, body.model_dump(exclude={"revision"}), _actor(req))


@router.get("/projects/{id}/prompts")
def prompts(id: str, req: Request, before: str | None = None, limit: int = Query(50, ge=1, le=100)):
    ws(req).project(id)
    return ws(req).list(SavedPrompt, id, before, limit)


@router.post("/projects/{id}/prompts")
def create_prompt(id: str, body: PromptBody, req: Request):
    return ws(req).save_prompt(id, body.name, body.content, _actor(req))


@router.put("/projects/{id}/prompts/{prompt_id}")
def edit_prompt(id: str, prompt_id: str, body: PromptBody, req: Request):
    return ws(req).save_prompt(id, body.name, body.content, _actor(req), prompt_id, body.revision)


@router.get("/prompts/{id}/versions")
def versions(id: str, req: Request, before: int | None = Query(None, ge=1), limit: int = Query(25, ge=1, le=100)):
    return ws(req).prompt_versions(id, before, limit)


@router.get("/tasks")
def tasks(req: Request, project_id: str | None = None, before: str | None = None,
          limit: int = Query(50, ge=1, le=100)):
    return ws(req).list(Task, project_id, before, limit)


@router.post("/tasks")
def create_task(body: TaskBody, req: Request):
    return ws(req).create_task(body.model_dump(), _actor(req))


@router.get("/tasks/{id}")
def task(id: str, req: Request):
    return ws(req).task(id)


@router.patch("/tasks/{id}")
def edit_task(id: str, body: TaskEdit, req: Request):
    return ws(req).create_task(body.model_dump(exclude={"revision"}), _actor(req), id, body.revision)


@router.get("/tasks/{id}/preview")
async def preview(id: str, req: Request):
    return await ws(req).prepare(id)


@router.post("/tasks/{id}/start")
async def start(id: str, body: QueueBody, req: Request):
    if not body.approved:
        raise AgentError("Starting inference requires explicit approval", 403)
    return await ws(req).enqueue(id, body.revision, body.allow_cloud, body.preview_hash, _actor(req))


@router.post("/tasks/{id}/cancel")
async def cancel(id: str, req: Request):
    return await ws(req).cancel(id, _actor(req))
