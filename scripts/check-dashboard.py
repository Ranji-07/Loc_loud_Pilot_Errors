"""Browser checks against the built dashboard and an isolated test backend.

Run: backend\\.venv\\Scripts\\python scripts\\check-dashboard.py
No paid model calls or commands run: Droid uses the backend test double.
"""
from __future__ import annotations

import base64
import asyncio
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import asynccontextmanager

import httpx
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from localpilot.agents.droid import DroidManager
from localpilot.config import Settings
from localpilot.main import create_app
from fastapi.responses import JSONResponse
from tests.test_agents import FakeSession, fake_models

EXE = shutil.which("agent-browser")
SESSION = os.environ.get("AGENT_BROWSER_SESSION", "localpilot-ui-regression")
BASE = "http://127.0.0.1:8766"


def browser(*args: str) -> dict:
    print(f"Browser: {args[0]}", flush=True)
    # The browser daemon inherits stdout on Windows; a pipe can stay open after the CLI exits.
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
        result = subprocess.run([EXE, "--session", SESSION, *args, "--json"], stdout=output,
                                stderr=output, timeout=45)
        output.seek(0)
        content = output.read()
    lines = [line for line in content.splitlines() if line.startswith("{")]
    data = json.loads(lines[-1]) if lines else {}
    if result.returncode or not data.get("success"):
        raise AssertionError(f"Browser command failed {args[0]}: {content}")
    return data.get("data", {})


def evaluate(code: str):
    return browser("eval", "-b", base64.b64encode(code.encode()).decode())


def check(code: str):
    evaluate(f"(() => {{ if (!({code})) throw new Error('UI assertion failed'); return true; }})()")


def go(route: str, title: str):
    browser("open", f"{BASE}/?ui-check={time.monotonic_ns()}#/{route}")
    browser("wait", "--text", title)


def main():
    if not EXE:
        raise RuntimeError("agent-browser is required")
    passed = []
    with tempfile.TemporaryDirectory(prefix="localpilot-ui-") as temp:
        settings = Settings(port=8766, repo_root=ROOT, data_dir=Path(temp), web_dist=ROOT / "apps/web/dist",
                            ollama_url="http://127.0.0.1:1", remote_ollama_url="http://127.0.0.1:2",
                            droid_executable=sys.executable)
        app = create_app(settings)
        app.state.ui_fail_path = None

        @app.middleware("http")
        async def test_failure(request, call_next):
            if request.url.path == app.state.ui_fail_path:
                return JSONResponse({"error": "Test service unavailable"}, status_code=503)
            return await call_next(request)
        original = app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(a):
            async with original(a):
                a.state.droid = DroidManager(settings, a.state.db, session_factory=lambda **kw: FakeSession(**kw),
                                            models_loader=fake_models)
                yield
                await a.state.droid.shutdown()

        app.router.lifespan_context = lifespan
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8766, log_level="error"))
        # The test double needs no async subprocesses; Selector avoids Proactor's threaded shutdown race.
        loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
        thread = threading.Thread(target=lambda: asyncio.run(server.serve(), loop_factory=loop_factory), daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.1)
            if not server.started:
                raise RuntimeError("Test backend did not start")
            go("prompts", "Prompt Studio")
            browser("wait", "--fn", "!!document.querySelector('#prompt-model')?.value")
            browser("fill", "#prompt-editor", "Say {{word}}")
            browser("wait", "--text", "Fill in: word")
            check("document.querySelector('button.btn-primary').disabled")
            browser("find", "label", "word", "fill", "hello")
            browser("wait", "--text", "Say hello")
            check("!document.querySelector('button.btn-primary').disabled")
            browser("find", "role", "button", "click", "--name", "Run with Droid")
            browser("wait", "--url", "**/agents/runs/*")
            browser("wait", "--text", "Run finished: succeeded")
            check("document.querySelector('#main').innerText.includes('done')")
            passed.append("Prompt variables, missing value guard, strict run, streamed result")
            browser("find", "role", "button", "click", "--name", "Retry", "--exact")
            browser("wait", "--text", "Run finished: succeeded")
            with httpx.Client(base_url=BASE) as client:
                runs = client.get("/api/v1/agents/runs").json()
                assert len(runs) == 2 and all(r["autonomy"] == "off" for r in runs)
            passed.append("Retry creates a separate run using the existing API")
            browser("find", "label", "Follow-up message", "fill", "again")
            browser("find", "role", "button", "click", "--name", "Continue", "--exact")
            browser("wait", "--text", "Run finished: succeeded")
            with httpx.Client(base_url=BASE) as client:
                runs = client.get("/api/v1/agents/runs").json()
                assert runs[0]["parent_run_id"] and runs[0]["session_id"] == runs[1]["session_id"]
            passed.append("Continue resumes the session")
            for outcome in ("Deny", "Approve once"):
                go("prompts", "Prompt Studio")
                browser("wait", "--fn", "!!document.querySelector('#prompt-model')?.value")
                browser("fill", "#prompt-editor", "make a file")
                browser("find", "role", "button", "click", "--name", "Run with Droid")
                browser("wait", "--text", "Create file hello.txt")
                go("decisions", "Waiting for you")
                browser("find", "role", "button", "click", "--name", outcome, "--exact")
                browser("wait", "--text", "Nothing is waiting for approval")
                go("history", "History")
                browser("wait", "--fn", "!document.querySelector('#main [role=status]')")
                check(f"document.querySelector('#main').innerText.includes('approval.{'denied' if outcome == 'Deny' else 'approved'}')")
                passed.append(f"Shared approval {outcome} outcome appears in History")
            go("settings", "Search settings")
            browser("find", "label", "Search settings", "fill", "approval timeout")
            browser("wait", "--text", "approval timeout seconds")
            check("!document.querySelector('#main').innerText.includes('aws region')")
            browser("select", "#main select", "light")
            check("document.documentElement.dataset.theme === 'light' && localStorage.getItem('localpilot.theme') === 'light'")
            browser("open", f"{BASE}/#/settings")
            browser("wait", "--text", "Search settings")
            check("document.documentElement.dataset.theme === 'light'")
            passed.append("Settings search, theme persistence; backend remains read-only")
            go("history", "History")
            browser("wait", "--fn", "!document.querySelector('#main [role=status]')")
            browser("find", "label", "Search action or target", "fill", "no-such-event")
            browser("find", "role", "button", "click", "--name", "Apply filters")
            browser("wait", "--text", "No matching events")
            browser("find", "role", "button", "click", "--name", "Clear", "--exact")
            browser("wait", "--fn", "document.querySelectorAll('[data-event-id]').length > 0")
            passed.append("History filtering, empty state and clear")
            with httpx.Client(base_url=BASE) as client:
                from localpilot import audit
                for i in range(60):
                    audit.record(app.state.db, "ui.pagination", f"row-{i}")
            go("history", "History")
            browser("wait", "--fn", "document.querySelectorAll('[data-event-id]').length === 25")
            first = evaluate("Array.from(document.querySelectorAll('[data-event-id]'), n=>n.dataset.eventId)")["result"]
            browser("find", "role", "button", "click", "--name", "Older", "--exact")
            browser("wait", "--text", "Page 2")
            browser("wait", "--fn", "document.querySelectorAll('[data-event-id]').length === 25")
            second = evaluate("Array.from(document.querySelectorAll('[data-event-id]'), n=>n.dataset.eventId)")["result"]
            assert not set(first) & set(second)
            browser("find", "role", "button", "click", "--name", "Newer", "--exact")
            browser("wait", "--text", "Page 1")
            passed.append("History cursor paging, 25 rows, no overlap, newer page recovery")
            for page, endpoint, title in (("settings", "/api/v1/settings", "Settings"),
                                          ("history", "/api/v1/audit", "History"),
                                          ("models", "/api/v1/models", "Models")):
                app.state.ui_fail_path = endpoint
                go(page, title)
                browser("wait", "--text", "Test service unavailable")
                app.state.ui_fail_path = None
                browser("find", "role", "button", "click", "--name", "Retry", "--exact")
                browser("wait", "--fn", "!document.querySelector('#main [role=alert]') && !document.querySelector('#main [role=status]')")
            passed.append("Settings, History and Models API errors show Retry and recover")
            go("agent", "Agents")
            browser("focus", "[role=tab][aria-selected=true]")
            browser("press", "ArrowRight")
            browser("wait", "--url", "**/agents/performance")
            browser("press", "End")
            browser("wait", "--url", "**/agents/permissions")
            passed.append("Legacy agent link and keyboard tab arrows / End")
            errors = browser("errors")
            check("document.querySelector('h1').textContent === 'Agents'")
            if errors.get("errors"):
                raise AssertionError(errors)
            print(json.dumps({"passed": len(passed), "checks": passed}, indent=2), flush=True)
        finally:
            browser("close")
            server.should_exit = True
            thread.join(timeout=10)
            logging.shutdown()


if __name__ == "__main__":
    main()
