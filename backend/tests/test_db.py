from __future__ import annotations

from sqlalchemy import inspect, select

from localpilot.db import Database
from localpilot.models import StepRun, RunbookRun
from localpilot.policy import CommandPolicy
from localpilot.runbooks.engine import RunbookEngine
from localpilot.runbooks.schema import load_runbooks


def test_migrate_creates_tables_and_is_idempotent(tmp_path):
    db = Database(tmp_path / "x.db")
    db.migrate()
    db.migrate()
    names = set(inspect(db.engine).get_table_names())
    assert {"runbook_runs", "step_runs", "audit_events", "model_calls", "usage_snapshots", "alembic_version"} <= names
    db.dispose()


def test_recover_marks_running_steps_interrupted(tmp_path, settings):
    db = Database(tmp_path / "y.db")
    db.migrate()
    with db.session() as s:
        s.add(RunbookRun(id="r1", runbook_id="test-book"))
        s.flush()
        s.add(StepRun(run_id="r1", step_id="hello", status="running"))
    eng = RunbookEngine(settings, db, CommandPolicy(settings.repo_root), load_runbooks(settings.runbooks_dir, settings))
    assert eng.recover() == 1
    with db.session() as s:
        assert s.scalars(select(StepRun)).one().status == "interrupted"
    db.dispose()


def test_cwd_must_stay_in_repo(tmp_path, settings):
    import pytest
    (tmp_path / "bad.yaml").write_text(
        "id: bad\ntitle: t\nsummary: s\nsteps:\n  - {id: a, title: a, explain: a, command: git status, cwd: ../..}\n")
    with pytest.raises(ValueError, match="inside the repository"):
        load_runbooks(tmp_path, settings)


def test_shipped_runbooks_load(settings):
    from localpilot.config import REPO_ROOT
    books = load_runbooks(REPO_ROOT / "config" / "runbooks", settings)
    assert {"local-setup", "vscode-extension", "aws-gpu-trial", "litellm-gateway"} <= set(books)
    for rb in books.values():
        for st in rb.steps:
            assert "{" not in st.command or "}" not in st.command.split("{", 1)[1][:20], f"{rb.id}/{st.id} unresolved placeholder"
