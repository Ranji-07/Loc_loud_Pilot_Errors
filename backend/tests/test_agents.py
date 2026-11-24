from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from localpilot.agents.droid import DroidManager
from localpilot.config import Settings
from localpilot.db import Database
from localpilot.models import AgentRun, Approval
from localpilot.main import create_app

from .conftest import HEADERS


class TextDelta:
    def __init__(self, text): self.text = text


class AssistantMessage:
    def __init__(self, text): self.text = text


class ToolResult:
    def __init__(self, ok):
        self.tool_name, self.tool_use_id, self.is_error = "Create", "t1", not ok
        self.content = "created" if ok else "denied by user"


class CreateFile:
    def __init__(self):
        self.file_path, self.file_name, self.content = "E:/x/hello.txt", "hello.txt", "hi"


class Option:
    def __init__(self, v): self.value, self.label = v, v


class FakePermission:
    def __init__(self):
        self.options = [Option("proceed_once"), Option("proceed_always"), Option("cancel")]
        self.actions = [CreateFile()]

    def respond(self, outcome, comment=None):
        return ("responded", getattr(outcome, "value", outcome), comment)


class Usage:
    input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, thinking_tokens = 100, 20, 0, 0, 0
    factory_credits = 42


class Result:
    def __init__(self, subtype, text=""):
        self.subtype, self.text, self.usage, self.error = subtype, text, Usage(), None


class FakeStream:
    def __init__(self, sess, prompt):
        self.sess, self.prompt, self.result = sess, prompt, None

    async def __aenter__(self): return self

    async def __aexit__(self, *a): return False

    def __aiter__(self): return self._gen()

    async def _gen(self):
        yield TextDelta("thinking… ")
        if "wait" in self.prompt:
            await self.sess.interrupted.wait()
            self.result = Result("interrupted")
            return
        if "file" in self.prompt:
            resp = await self.sess.on_permission(FakePermission())
            self.sess.responses.append(resp)
            yield ToolResult(resp[1] == "proceed_once")
            if resp[1] == "cancel":  # real Droid ends the turn when a tool call is cancelled
                self.result = Result("interrupted")
                return
        yield AssistantMessage("done")
        self.result = Result("success", "done")


class FakeSession:
    instances: list["FakeSession"] = []

    def __init__(self, on_permission, resume_session_id=None, **kw):
        self.on_permission, self.kw = on_permission, kw
        self.id = resume_session_id or f"sess-{len(FakeSession.instances)}"
        self.responses, self.interrupted = [], asyncio.Event()
        FakeSession.instances.append(self)

    async def __aenter__(self): return self

    async def __aexit__(self, *a): return False

    def stream(self, prompt, include_partial_messages=False): return FakeStream(self, prompt)

    async def interrupt(self): self.interrupted.set()


async def fake_models():
    return [{"id": "claude-haiku-4-5-20251001", "name": "Haiku", "location": "cloud", "custom": False},
            {"id": "custom:Local-0", "name": "Local Ollama: qwen2.5-coder 7B", "location": "local", "custom": True}]


@pytest.fixture
def agent_client(settings: Settings):
    settings.droid_executable = sys.executable
    FakeSession.instances.clear()
    app = create_app(settings)
    with TestClient(app) as c:
        app.state.droid = DroidManager(settings, app.state.db, session_factory=lambda **kw: FakeSession(**kw),
                                       models_loader=fake_models)
        yield c


def wait_status(c: TestClient, run_id: str, want: set[str], timeout: float = 10) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = c.get(f"/api/v1/agents/runs/{run_id}").json()
        if run["status"] in want:
            return run
        time.sleep(0.05)
    raise AssertionError(f"run stayed {run['status']}")


def pending(c: TestClient) -> list[dict]:
    return c.get("/api/v1/approvals", params={"status": "pending"}).json()


def wait_pending(c: TestClient, timeout: float = 10) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        p = pending(c)
        if p:
            return p[0]
        time.sleep(0.05)
    raise AssertionError("no approval appeared")


def test_models_marks_local_and_cloud(agent_client):
    data = agent_client.get("/api/v1/agents/models").json()
    assert {m["location"] for m in data["models"]} == {"local", "cloud"}
    assert data["default"] == "claude-haiku-4-5-20251001"


def test_run_without_permissions_succeeds_and_records_usage(agent_client):
    run = agent_client.post("/api/v1/agents/runs", json={"prompt": "say hi"}, headers=HEADERS).json()
    done = wait_status(agent_client, run["id"], {"succeeded", "failed"})
    assert done["status"] == "succeeded" and done["result_text"] == "done"
    assert done["usage"]["factory_credits"] == 42 and done["model_location"] == "cloud"
    types = [e["type"] for e in agent_client.get(f"/api/v1/agents/runs/{run['id']}/events").json()["events"]]
    assert types == ["assistant", "finished"]


@pytest.mark.parametrize("decision,expected", [("approve", "proceed_once"), ("deny", "cancel")])
def test_permission_waits_for_human_decision(agent_client, decision, expected):
    run = agent_client.post("/api/v1/agents/runs", json={"prompt": "make a file"}, headers=HEADERS).json()
    ap = wait_pending(agent_client)
    assert ap["kind"] == "file_create" and ap["title"] == "Create file hello.txt"
    assert "proceed_always" in ap["options"]
    assert wait_status(agent_client, run["id"], {"waiting_approval"})["pending_approvals"] == 1
    r = agent_client.post(f"/api/v1/approvals/{ap['id']}/decide", json={"decision": decision}, headers=HEADERS)
    assert r.status_code == 200 and r.json()["status"] == ("approved" if decision == "approve" else "denied")
    done = wait_status(agent_client, run["id"], {"succeeded", "interrupted"})
    assert FakeSession.instances[-1].responses[0][1] == expected  # never "proceed_always"
    if decision == "approve":
        assert done["status"] == "succeeded"
    else:
        assert done["status"] == "interrupted" and "after you denied: Create file hello.txt" in done["error"]
    again = agent_client.post(f"/api/v1/approvals/{ap['id']}/decide", json={"decision": "approve"}, headers=HEADERS)
    assert again.status_code == 409
    actions = [a["action"] for a in agent_client.get("/api/v1/audit").json()]
    assert "approval.requested" in actions and f"approval.{r.json()['status']}" in actions


def test_stop_denies_pending_and_interrupts(agent_client):
    run = agent_client.post("/api/v1/agents/runs", json={"prompt": "make a file"}, headers=HEADERS).json()
    ap = wait_pending(agent_client)
    stopped = agent_client.post(f"/api/v1/agents/runs/{run['id']}/stop", headers=HEADERS).json()
    assert stopped["status"] == "stopped" and "denied" not in (stopped["error"] or "")
    assert agent_client.get(f"/api/v1/approvals/{ap['id']}").json()["status"] == "denied"
    assert FakeSession.instances[-1].responses[0][1] == "cancel"

    run2 = agent_client.post("/api/v1/agents/runs", json={"prompt": "wait forever"}, headers=HEADERS).json()
    wait_status(agent_client, run2["id"], {"running"})
    out = agent_client.post(f"/api/v1/agents/runs/{run2['id']}/stop", headers=HEADERS).json()
    assert out["status"] == "stopped"
    assert agent_client.post(f"/api/v1/agents/runs/{run2['id']}/stop", headers=HEADERS).status_code == 409


def test_continue_resumes_same_session(agent_client):
    first = agent_client.post("/api/v1/agents/runs", json={"prompt": "say hi"}, headers=HEADERS).json()
    first = wait_status(agent_client, first["id"], {"succeeded"})
    second = agent_client.post("/api/v1/agents/runs", json={"prompt": "and again", "continue_run_id": first["id"]},
                               headers=HEADERS).json()
    second = wait_status(agent_client, second["id"], {"succeeded"})
    assert second["session_id"] == first["session_id"] and second["parent_run_id"] == first["id"]


def test_guards(agent_client, tmp_path: Path):
    post = lambda body: agent_client.post("/api/v1/agents/runs", json=body, headers=HEADERS)
    assert post({"prompt": "x", "autonomy": "high"}).status_code == 400
    assert post({"prompt": "   "}).status_code == 400
    assert post({"prompt": "x", "cwd": str(tmp_path)}).status_code == 403
    assert agent_client.post("/api/v1/agents/runs", json={"prompt": "x"}).status_code == 403  # no client header
    assert agent_client.post("/api/v1/approvals/nope/decide", json={"decision": "approve"},
                             headers=HEADERS).status_code == 404
    assert agent_client.get("/api/v1/agents/runs/nope").status_code == 404


def test_concurrency_limit(agent_client):
    ids = [agent_client.post("/api/v1/agents/runs", json={"prompt": f"wait {i}"}, headers=HEADERS).json()["id"]
           for i in range(2)]
    assert agent_client.post("/api/v1/agents/runs", json={"prompt": "wait 3"}, headers=HEADERS).status_code == 409
    for i in ids:
        agent_client.post(f"/api/v1/agents/runs/{i}/stop", headers=HEADERS)


def test_restart_marks_active_runs_interrupted(settings: Settings):
    settings.droid_executable = sys.executable
    app = create_app(settings)
    with TestClient(app) as c:
        app.state.droid = DroidManager(settings, app.state.db, session_factory=lambda **kw: FakeSession(**kw),
                                       models_loader=fake_models)
        run = c.post("/api/v1/agents/runs", json={"prompt": "make a file"}, headers=HEADERS).json()
        ap = wait_pending(c)
    # Rewind the rows to what a hard crash (no clean shutdown) would leave behind.
    db = Database(settings.db_path)
    with db.session() as s:
        s.get(AgentRun, run["id"]).status = "waiting_approval"
        s.get(Approval, ap["id"]).status = "pending"
    db.dispose()
    with TestClient(create_app(settings)) as c:
        assert c.get(f"/api/v1/agents/runs/{run['id']}").json()["status"] == "interrupted"
        assert c.get(f"/api/v1/approvals/{ap['id']}").json()["status"] == "expired"
