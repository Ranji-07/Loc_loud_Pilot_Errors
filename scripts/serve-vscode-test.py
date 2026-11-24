"""Isolated VS Code/UI test backend. No real inference or commands.

Only the test runner's explicit file permission writes hello.txt in the selected
scratch workspace. Never point --workspace at a real project.
"""
import argparse
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from localpilot.agents.droid import DroidManager
from localpilot.config import Settings
from localpilot.main import create_app
from tests.test_agents import FakeSession, fake_models

parser = argparse.ArgumentParser()
parser.add_argument("--workspace", required=True, type=Path)
parser.add_argument("--data", required=True, type=Path)
parser.add_argument("--port", default=8767, type=int)
args = parser.parse_args()
if args.workspace.resolve() == ROOT or (args.workspace / ".git").exists():
    raise SystemExit("Use a scratch workspace, not a real repository")
args.workspace.mkdir(parents=True, exist_ok=True)
settings = Settings(port=args.port, repo_root=ROOT, data_dir=args.data, agent_workspaces=[args.workspace],
                    web_dist=ROOT / "apps/web/dist", droid_executable=sys.executable,
                    ollama_url="http://127.0.0.1:1", remote_ollama_url="http://127.0.0.1:2")
app = create_app(settings)
original = app.router.lifespan_context


async def models():
    rows = await fake_models()
    return [{**r, "name": "[TEST DOUBLE] " + r["name"]} for r in rows]


@asynccontextmanager
async def lifespan(a):
    async with original(a):
        a.state.droid = DroidManager(settings, a.state.db, session_factory=lambda **kw: FakeSession(write_files=True, **kw),
                                    models_loader=models)
        print(f"TEST BACKEND ONLY: scratch workspace {args.workspace}", flush=True)
        yield
        await a.state.droid.shutdown()


app.router.lifespan_context = lifespan
uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
