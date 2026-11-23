from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from localpilot.config import REPO_ROOT, Settings
from localpilot.main import create_app

TEST_RUNBOOK = """
id: test-book
title: Test book
summary: Steps used by the test suite
order: 1
steps:
  - id: hello
    title: Say hello
    explain: prints hello
    command: '{python} -c "print(''hello from step'')"'
    check: '{python} -c "print(''verified'')"'
  - id: fail
    title: Fails
    explain: exits 3
    command: '{python} -c "import sys; sys.exit(3)"'
  - id: slow
    title: Slow
    explain: prints numbers for a while
    command: '{python} -c "import time; [print(i, flush=True) or time.sleep(0.2) for i in range(200)]"'
    long_running: true
  - id: secret
    title: Prints a secret
    explain: output must be redacted
    command: '{python} -c "print(''key AKIAABCDEFGHIJKLMNOP end'')"'
  - id: quota
    title: High risk
    explain: needs confirmation
    command: aws ec2 run-instances --dry-run --image-id ami-0
  - id: optional-one
    title: Optional
    explain: optional
    command: '{python} --version'
    optional: true
"""

HEADERS = {"x-localpilot-client": "1"}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    books = tmp_path / "runbooks"
    books.mkdir()
    (books / "test.yaml").write_text(TEST_RUNBOOK, encoding="utf-8")
    return Settings(data_dir=tmp_path / "data", runbooks_dir=books, web_dist=tmp_path / "no-web",
                    repo_root=REPO_ROOT, ollama_url="http://127.0.0.1:1", remote_ollama_url="http://127.0.0.1:2")


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as c:
        yield c


def wait_done(client: TestClient, run_id: str, step_id: str, timeout: float = 30) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = client.get(f"/api/v1/runs/{run_id}/steps/{step_id}/output").json()
        if out["done"]:
            return out
        time.sleep(0.1)
    raise AssertionError("step did not finish")


def step_of(run: dict, step_id: str) -> dict:
    return next(s for s in run["steps"] if s["id"] == step_id)
