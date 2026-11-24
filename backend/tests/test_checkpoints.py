import subprocess
import os
import sys
from types import SimpleNamespace

import pytest

from localpilot.agents.droid import AgentError, DroidManager
from localpilot.db import Database
from localpilot.models import AgentRun

from .test_agents import CreateFile, agent_client, wait_pending, wait_status
from .conftest import HEADERS


@pytest.fixture
def checkpoint_env(settings, tmp_path):
    root = tmp_path / "files"
    root.mkdir()
    settings.agent_workspaces = [root]
    settings.ensure_dirs()
    db = Database(settings.db_path)
    db.migrate()
    mgr = DroidManager(settings, db)
    with db.session() as s:
        s.add(AgentRun(id="run", prompt="x", model="test", cwd=str(root), status="succeeded"))
    yield mgr.checkpoints, root, db
    db.dispose()


def edited(path, before, after):
    cls = type("EditAction", (), {})
    action = cls()
    action.file_path, action.old_content, action.new_content = str(path), before, after
    action.tool_use = SimpleNamespace(id="t1")
    return action


def test_create_checkpoint_rollback_and_user_edit_guard(checkpoint_env):
    cp, root, db = checkpoint_env
    id = cp.prepare("run", "approval", str(root), [CreateFile(root)])
    cp.validate(id)
    file = root / "hello.txt"
    file.write_text("hi", encoding="utf-8")
    cp.capture("run", tool_use_id="t1")
    assert cp.list("run")[0]["status"] == "completed"
    file.write_text("user work", encoding="utf-8")
    with pytest.raises(AgentError, match="newer work"):
        cp.rollback(id, "user:vscode")
    assert file.read_text() == "user work"
    file.write_text("hi", encoding="utf-8")
    assert cp.rollback(id, "user:vscode")["status"] == "rolled_back"
    assert not file.exists()
    with pytest.raises(AgentError):
        cp.rollback(id, "user")


def test_edit_restore_original_without_git_reset(checkpoint_env):
    cp, root, db = checkpoint_env
    file = root / "a.txt"
    file.write_bytes(b"before\r\n")
    id = cp.prepare("run", "approval", str(root), [edited(file, "before\r\n", "after")])
    cp.validate(id)
    file.write_text("after", encoding="utf-8")
    cp.capture("run", tool_use_id="t1")
    cp.rollback(id, "user")
    assert file.read_bytes() == b"before\r\n"


def test_pending_changed_file_cannot_be_approved(checkpoint_env):
    cp, root, db = checkpoint_env
    id = cp.prepare("run", "approval", str(root), [CreateFile(root)])
    (root / "hello.txt").write_text("user wrote this", encoding="utf-8")
    with pytest.raises(AgentError, match="changed while approval"):
        cp.validate(id)


def test_preflight_blocks_outside_secrets_existing_create_and_stale_proposal(checkpoint_env):
    cp, root, db = checkpoint_env
    (root / "hello.txt").write_text("user", encoding="utf-8")
    with pytest.raises(AgentError, match="overwrite existing"):
        cp.prepare("run", "a", str(root), [CreateFile(root)])
    with pytest.raises(AgentError, match="before-content"):
        cp.prepare("run", "b", str(root), [edited(root / "hello.txt", "wrong", "new")])
    with pytest.raises(AgentError, match="outside"):
        cp.prepare("run", "c", str(root), [edited(root.parent / "a.txt", None, "new")])
    with pytest.raises(AgentError, match="Secret"):
        cp.prepare("run", "d", str(root), [edited(root / ".env", None, "new")])


def test_dirty_git_file_and_index_preserved(checkpoint_env):
    cp, root, db = checkpoint_env
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    file = root / "a.txt"
    file.write_text("user", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "a.txt"], check=True, capture_output=True)
    with pytest.raises(AgentError, match="uncommitted changes"):
        cp.prepare("run", "a", str(root), [edited(file, "user", "new")])
    r = subprocess.run(["git", "-C", str(root), "diff", "--cached", "--name-only"], capture_output=True, text=True)
    assert r.stdout.strip() == "a.txt" and file.read_text() == "user"


def test_active_run_blocks_rollback(checkpoint_env):
    cp, root, db = checkpoint_env
    id = cp.prepare("run", "approval", str(root), [CreateFile(root)])
    cp.validate(id)
    (root / "hello.txt").write_text("hi", encoding="utf-8")
    cp.capture("run", tool_use_id="t1")
    with db.session() as s:
        s.get(AgentRun, "run").status = "running"
    with pytest.raises(AgentError, match="Stop active"):
        cp.rollback(id, "user")


def test_boundary_rejection_uses_shared_approval_record(agent_client, settings, tmp_path):
    root = tmp_path / "files"
    root.mkdir()
    settings.agent_workspaces = [root]
    (root / "hello.txt").write_text("user work", encoding="utf-8")
    run = agent_client.post("/api/v1/agents/runs", json={"prompt": "make a file"}, headers=HEADERS).json()
    ap = wait_pending(agent_client)
    assert "overwrite existing" in ap["details"]["checkpoint_error"]
    assert agent_client.post(f"/api/v1/approvals/{ap['id']}/decide", json={"decision": "approve"},
                             headers=HEADERS).status_code == 409
    assert agent_client.get(f"/api/v1/approvals/{ap['id']}").json()["status"] == "pending"
    agent_client.post(f"/api/v1/approvals/{ap['id']}/decide", json={"decision": "deny"}, headers=HEADERS)
    assert wait_status(agent_client, run["id"], {"interrupted"})["status"] == "interrupted"
    assert (root / "hello.txt").read_text() == "user work"


def test_unverified_post_image_never_becomes_rollback_ready(checkpoint_env):
    cp, root, db = checkpoint_env
    file = root / "a.txt"
    file.write_text("before", encoding="utf-8")
    id = cp.prepare("run", "approval", str(root), [edited(file, "before", "expected")])
    cp.validate(id)
    file.write_text("my newer edits", encoding="utf-8")
    cp.capture("run", tool_use_id="t1")
    cp.capture("run", finished=True)
    assert cp.list("run")[0]["status"] == "unavailable"
    with pytest.raises(AgentError, match="not ready"):
        cp.rollback(id, "user")
    assert file.read_text() == "my newer edits"


def test_wrong_tool_result_cannot_verify_post_image(checkpoint_env):
    cp, root, db = checkpoint_env
    id = cp.prepare("run", "approval", str(root), [CreateFile(root)])
    cp.validate(id)
    (root / "hello.txt").write_text("hi", encoding="utf-8")
    cp.capture("run", tool_use_id="different")
    assert cp.list("run")[0]["status"] == "approved"
    cp.capture("run", tool_use_id="t1")
    assert cp.list("run")[0]["status"] == "completed"


def test_junction_retarget_is_rejected(checkpoint_env):
    cp, root, db = checkpoint_env
    a, b, link = root / "a", root / "b", root / "link"
    a.mkdir()
    b.mkdir()
    for directory in (a, b):
        (directory / "file.txt").write_text("before", encoding="utf-8")
    def make_link(target):
        if sys.platform == "win32":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=True)
        else:
            link.symlink_to(target, target_is_directory=True)
    make_link(a)
    id = cp.prepare("run", "approval", str(root), [edited(link / "file.txt", "before", "new")])
    os.rmdir(link) if sys.platform == "win32" else link.unlink()
    make_link(b)
    try:
        with pytest.raises(AgentError, match="path target changed"):
            cp.validate(id)
        assert (b / "file.txt").read_text() == "before"
    finally:
        os.rmdir(link) if sys.platform == "win32" else link.unlink()


def test_ignored_user_file_is_not_git_clean(checkpoint_env):
    cp, root, db = checkpoint_env
    subprocess.run(["git", "init", str(root)], capture_output=True, check=True)
    (root / ".gitignore").write_text("notes.txt\n", encoding="utf-8")
    file = root / "notes.txt"
    file.write_text("my notes", encoding="utf-8")
    with pytest.raises(AgentError, match="uncommitted changes"):
        cp.prepare("run", "a", str(root), [edited(file, "my notes", "new")])
    assert file.read_text() == "my notes"


def test_quoted_json_secret_is_not_checkpointed(checkpoint_env):
    cp, root, db = checkpoint_env
    file = root / "config.json"
    file.write_text('{"api_key":"dummy-sensitive-value"}', encoding="utf-8")
    with pytest.raises(AgentError, match="secret contents"):
        cp.prepare("run", "a", str(root), [edited(file, None, "{}")])


def test_multifile_rollback_preflight_and_partial_retry(checkpoint_env, monkeypatch):
    cp, root, db = checkpoint_env
    folder = root / "sub"
    folder.mkdir()
    old = folder / "old.txt"
    new = root / "new.txt"
    old.write_text("original", encoding="utf-8")
    action = type("ApplyPatchAction", (), {})()
    action.tool_use = SimpleNamespace(id="t1")
    action.files = [SimpleNamespace(file_path=str(new), operation="create", new_content="new", old_content=None, move_to=None),
                    SimpleNamespace(file_path=str(old), operation="delete", new_content=None, old_content="original", move_to=None)]
    id = cp.prepare("run", "approval", str(root), [action])
    cp.validate(id)
    old.unlink()
    new.write_text("new", encoding="utf-8")
    folder.rmdir()
    cp.capture("run", tool_use_id="t1")
    with pytest.raises(AgentError, match="parent directory"):
        cp.rollback(id, "user")
    assert new.read_text() == "new"
    folder.mkdir()
    original_replace = os.replace
    def fail_replace(*args):
        raise OSError("injected write failure")
    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(AgentError, match="partially applied"):
        cp.rollback(id, "user")
    assert cp.list("run")[0]["status"] == "rollback_partial" and not new.exists()
    monkeypatch.setattr(os, "replace", original_replace)
    assert cp.rollback(id, "user")["status"] == "rolled_back"
    assert old.read_text() == "original"
