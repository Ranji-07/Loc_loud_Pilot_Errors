import time

import pytest

from localpilot.models import Task

from .conftest import HEADERS
from .test_agents import FakeSession, agent_client, wait_pending


def project(c, root, name="Project"):
    r = c.post("/api/v1/projects", json={"name": name, "root": str(root)}, headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


def task(c, p, **fields):
    r = c.post("/api/v1/tasks", json={"project_id": p["id"], "objective": "say hi", **fields}, headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


def start(c, t, cloud=True):
    preview = c.get(f"/api/v1/tasks/{t['id']}/preview")
    assert preview.status_code == 200, preview.text
    return c.post(f"/api/v1/tasks/{t['id']}/start", json={"revision": t["revision"], "approved": True,
                  "allow_cloud": cloud, "preview_hash": preview.json()["preview_hash"]}, headers=HEADERS)


def wait_task(c, id, statuses, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = c.get(f"/api/v1/tasks/{id}").json()
        if r["status"] in statuses:
            return r
        time.sleep(0.05)
    raise AssertionError(f"Task remained {r['status']}")


@pytest.fixture
def workspace_client(agent_client, settings, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    settings.agent_workspaces = [root]
    yield agent_client, root


def test_projects_validate_boundary_and_revisions(workspace_client, tmp_path):
    c, root = workspace_client
    p = project(c, root)
    assert c.post("/api/v1/projects", json={"name": "Again", "root": str(root)}, headers=HEADERS).status_code == 409
    assert c.post("/api/v1/projects", json={"name": "Outside", "root": str(tmp_path)}, headers=HEADERS).status_code == 403
    body = {"revision": p["revision"], "name": "Renamed", "instructions": "rules", "architecture": "layers"}
    assert c.patch(f"/api/v1/projects/{p['id']}", json=body, headers=HEADERS).json()["revision"] == 2
    assert c.patch(f"/api/v1/projects/{p['id']}", json=body, headers=HEADERS).status_code == 409
    assert c.post("/api/v1/projects", json={"name": " ", "root": str(root)}, headers=HEADERS).status_code == 422
    assert c.post("/api/v1/projects", json={"name": "X", "root": str(root)}).status_code == 403
    assert c.get("/api/v1/projects", params={"limit": 101}).status_code == 422


def test_selected_context_only_and_staleness(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    (root / "a.txt").write_text("selected file", encoding="utf-8")
    r = c.post(f"/api/v1/projects/{p['id']}/context", json={"kind": "file", "title": "A", "path": "a.txt"}, headers=HEADERS)
    item = r.json()
    note = c.post(f"/api/v1/projects/{p['id']}/context", json={"kind": "note", "title": "Unselected",
                  "content": "do not send this"}, headers=HEADERS).json()
    t = task(c, p, context_ids=[item["id"]])
    preview = c.get(f"/api/v1/tasks/{t['id']}/preview").json()
    assert "selected file" in preview["prompt"] and "do not send this" not in preview["prompt"]
    assert preview["sources"][0]["source_hash"] == item["source_hash"]
    (root / "a.txt").write_text("changed", encoding="utf-8")
    assert c.get(f"/api/v1/tasks/{t['id']}/preview").status_code == 409
    r = c.put(f"/api/v1/projects/{p['id']}/context/{item['id']}", json={"kind": "file", "title": "A", "path": "a.txt",
               "revision": item["revision"]}, headers=HEADERS)
    assert r.json()["revision"] == 2
    assert "changed" in c.get(f"/api/v1/tasks/{t['id']}/preview").json()["prompt"]
    assert c.post("/api/v1/tasks", json={"project_id": p["id"], "objective": "x",
                  "context_ids": [note["id"], note["id"]]}, headers=HEADERS).status_code == 400


@pytest.mark.parametrize("path", ["../outside.txt", ".env", ".env.local", ".git/config", "key.pem", "id_rsa"])
def test_context_blocks_secret_and_outside_paths(workspace_client, path):
    c, root = workspace_client
    p = project(c, root)
    r = c.post(f"/api/v1/projects/{p['id']}/context", json={"kind": "file", "title": "Bad", "path": path}, headers=HEADERS)
    assert r.status_code == 403


def test_binary_large_and_cross_project_context(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    (root / "binary").write_bytes(b"a\0b")
    (root / "large").write_bytes(b"x" * 65537)
    for name in ("binary", "large"):
        assert c.post(f"/api/v1/projects/{p['id']}/context", json={"kind": "file", "title": name,
                      "path": name}, headers=HEADERS).status_code == 400
    other = root / "other"
    other.mkdir()
    p2 = project(c, other)
    item = c.post(f"/api/v1/projects/{p2['id']}/context", json={"kind": "note", "title": "Private",
                  "content": "second"}, headers=HEADERS).json()
    assert c.post("/api/v1/tasks", json={"project_id": p["id"], "objective": "x",
                  "context_ids": [item["id"]]}, headers=HEADERS).status_code == 403


def test_prompt_versions_and_variable_rendering(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    prompt = c.post(f"/api/v1/projects/{p['id']}/prompts", json={"name": "Reusable", "content": "Review {{file}}"},
                    headers=HEADERS).json()
    r = c.put(f"/api/v1/projects/{p['id']}/prompts/{prompt['id']}", json={"name": "Reusable", "content": "Test {{file}}",
              "revision": 1}, headers=HEADERS)
    assert r.json()["revision"] == 2
    versions = c.get(f"/api/v1/prompts/{prompt['id']}/versions").json()
    assert [v["content"] for v in versions] == ["Test {{file}}", "Review {{file}}"]
    assert c.get(f"/api/v1/prompts/{prompt['id']}/versions?before=2").json()[0]["version"] == 1
    assert c.post("/api/v1/tasks", json={"project_id": p["id"], "prompt_id": prompt["id"]},
                  headers=HEADERS).status_code == 400
    t = task(c, p, prompt_id=prompt["id"], variables={"file": "README.md"})
    assert t["objective"] == "Test README.md" and t["status"] == "draft"
    assert not FakeSession.instances


def test_start_requires_current_preview_and_explicit_cloud_consent(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    t = task(c, p)
    assert start(c, t, cloud=False).status_code == 403
    preview = c.get(f"/api/v1/tasks/{t['id']}/preview").json()
    c.patch(f"/api/v1/projects/{p['id']}", json={"revision": 1, "name": "Changed"}, headers=HEADERS)
    body = {"revision": 1, "approved": True, "allow_cloud": True, "preview_hash": preview["preview_hash"]}
    assert c.post(f"/api/v1/tasks/{t['id']}/start", json=body, headers=HEADERS).status_code == 409
    body["preview_hash"] = c.get(f"/api/v1/tasks/{t['id']}/preview").json()["preview_hash"]
    body["approved"] = False
    assert c.post(f"/api/v1/tasks/{t['id']}/start", json=body, headers=HEADERS).status_code == 403
    assert not FakeSession.instances


def test_queue_execution_strict_approval_and_retry(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    t = task(c, p, objective="make a file")
    assert start(c, t).status_code == 200
    assert start(c, t).status_code == 409
    ap = wait_pending(c)
    t = wait_task(c, t["id"], {"waiting_approval"})
    assert t["run"]["autonomy"] == "off" and len(t["attempts"]) == 1
    r = c.post(f"/api/v1/approvals/{ap['id']}/decide", json={"decision": "deny"},
               headers={**HEADERS, "x-localpilot-surface": "vscode"})
    assert r.json()["decided_by"] == "user:vscode"
    t = wait_task(c, t["id"], {"interrupted"})
    assert start(c, t).status_code == 200
    ap = wait_pending(c)
    c.post(f"/api/v1/approvals/{ap['id']}/decide", json={"decision": "approve"}, headers=HEADERS)
    t = wait_task(c, t["id"], {"succeeded"})
    assert len(t["attempts"]) == 2 and t["attempts"][0]["run_id"] != t["attempts"][1]["run_id"]
    assert t["run"]["result_text"] == "done"
    assert any(e["action"] == "task.started" for e in c.get("/api/v1/audit").json())


def test_queue_serializes_same_project_and_cancelled_draft(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    t1 = task(c, p, objective="wait forever")
    t2 = task(c, p)
    start(c, t1)
    wait_task(c, t1["id"], {"running"})
    start(c, t2)
    time.sleep(0.7)
    assert c.get(f"/api/v1/tasks/{t2['id']}").json()["status"] == "queued"
    assert c.post(f"/api/v1/tasks/{t2['id']}/cancel", headers=HEADERS).json()["status"] == "cancelled"
    c.post(f"/api/v1/tasks/{t1['id']}/cancel", headers=HEADERS)
    assert c.get(f"/api/v1/tasks/{t1['id']}").json()["run"]["status"] == "stopped"
    assert len(FakeSession.instances) == 1


def test_agent_assign_disable_and_context_limit(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    profile = c.post("/api/v1/agent-profiles", json={"name": "Reviewer", "role": "Review", "model": "custom:Local-0",
                    "instructions": "Independent review only"}, headers=HEADERS).json()
    t = task(c, p, agent_id=profile["id"])
    preview = c.get(f"/api/v1/tasks/{t['id']}/preview").json()
    assert preview["location"] == "local" and "Independent review only" in preview["prompt"]
    c.patch(f"/api/v1/agent-profiles/{profile['id']}", json={k: v for k, v in {**profile, "enabled": False}.items()
            if k not in ("id", "adapter")}, headers=HEADERS)
    assert c.get(f"/api/v1/tasks/{t['id']}/preview").status_code == 409
    t = task(c, p, objective="a" * 16000, requirements="b" * 8000, acceptance="c" * 8000)
    assert c.get(f"/api/v1/tasks/{t['id']}/preview").status_code == 400


def test_recovery_pauses_queued_tasks(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    t = task(c, p)
    with c.app.state.db.session() as s:
        row = s.get(Task, t["id"])
        row.status = "queued"
    c.app.state.workspace.recover()
    out = c.get(f"/api/v1/tasks/{t['id']}").json()
    assert out["status"] == "draft" and "Start explicitly" in out["error"]
    assert not FakeSession.instances


def test_lists_cursor_and_task_edit(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    for _ in range(5):
        task(c, p)
    first = c.get("/api/v1/tasks", params={"project_id": p["id"], "limit": 2}).json()
    second = c.get("/api/v1/tasks", params={"project_id": p["id"], "limit": 2, "before": first[-1]["id"]}).json()
    assert not {t["id"] for t in first} & {t["id"] for t in second}
    t = first[0]
    body = {"project_id": p["id"], "objective": "New objective", "revision": t["revision"]}
    out = c.patch(f"/api/v1/tasks/{t['id']}", json=body, headers=HEADERS)
    assert out.json()["objective"] == "New objective"
    assert c.patch(f"/api/v1/tasks/{t['id']}", json=body, headers=HEADERS).status_code == 409


def test_dispatch_rejects_local_model_reclassified_as_cloud(workspace_client):
    c, root = workspace_client
    c.portal.call(c.app.state.workspace.shutdown)
    p = project(c, root)
    t = task(c, p, model="custom:Local-0")
    assert start(c, t, cloud=False).status_code == 200
    async def changed_models():
        return [{"id": "custom:Local-0", "name": "Changed", "location": "cloud", "custom": True}]
    c.app.state.droid._models_loader = changed_models
    c.portal.call(c.app.state.workspace.dispatch)
    out = c.get(f"/api/v1/tasks/{t['id']}").json()
    assert out["status"] == "failed" and "location changed" in out["error"]
    assert not FakeSession.instances


def test_quoted_secret_redacted_from_context_and_saved_prompts(workspace_client):
    import json
    from localpilot.redact import redact
    c, root = workspace_client
    p = project(c, root)
    secret = '{"api_key":"dummy-sensitive-value","safe":"keep"}'
    assert json.loads(redact(secret)) == {"api_key": "****", "safe": "keep"}
    (root / "config.json").write_text(secret, encoding="utf-8")
    item = c.post(f"/api/v1/projects/{p['id']}/context", json={"kind": "file", "title": "Config", "path": "config.json"},
                  headers=HEADERS).json()
    t = task(c, p, context_ids=[item["id"]])
    assert "dummy-sensitive-value" not in c.get(f"/api/v1/tasks/{t['id']}/preview").text
    saved = c.post(f"/api/v1/projects/{p['id']}/prompts", json={"name": "No secret", "content": secret}, headers=HEADERS).json()
    assert "dummy-sensitive-value" not in c.get(f"/api/v1/prompts/{saved['id']}/versions").text


def test_continue_is_owned_and_remains_a_tracked_task(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    first = task(c, p)
    start(c, first)
    first = wait_task(c, first["id"], {"succeeded"})
    followup = task(c, p, objective="and again", continue_run_id=first["run_id"])
    start(c, followup)
    followup = wait_task(c, followup["id"], {"succeeded"})
    assert followup["run"]["session_id"] == first["run"]["session_id"]
    assert followup["run"]["parent_run_id"] == first["run_id"]
    assert followup["attempt_count"] == 1 and followup["run"]["autonomy"] == "off"
    other = root / "other"
    other.mkdir()
    p2 = project(c, other)
    r = c.post("/api/v1/tasks", json={"project_id": p2["id"], "objective": "cross project",
               "continue_run_id": first["run_id"]}, headers=HEADERS)
    assert r.status_code == 403


def test_unfilled_raw_prompt_variables_are_blocked(workspace_client):
    c, root = workspace_client
    p = project(c, root)
    r = c.post("/api/v1/tasks", json={"project_id": p["id"], "objective": "Do {{thing}}"}, headers=HEADERS)
    assert r.status_code == 400
