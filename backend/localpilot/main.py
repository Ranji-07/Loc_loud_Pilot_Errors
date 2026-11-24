from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, audit
from .agents.droid import AgentError, DroidManager
from .agents.routes import router as agents_router
from .api import router
from .config import Settings, get_settings
from .db import Database
from .logging_setup import configure_logging
from .policy import CommandPolicy
from .runbooks.engine import RunbookEngine, RunbookError
from .runbooks.schema import load_runbooks
from .workspace import Workspace
from .workspace_routes import router as workspace_router

log = logging.getLogger("localpilot")

CLIENT_HEADER = "x-localpilot-client"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_dirs()
        configure_logging(settings.log_dir, settings.log_level)
        db = Database(settings.db_path)
        db.migrate()
        books = load_runbooks(settings.runbooks_dir, settings)
        engine = RunbookEngine(settings, db, CommandPolicy(settings.repo_root), books)
        recovered = engine.recover()
        droid = DroidManager(settings, db)
        interrupted = droid.recover()
        app.state.settings, app.state.db, app.state.engine, app.state.droid = settings, db, engine, droid
        workspace = Workspace(db, lambda: app.state.droid)
        workspace.recover()
        app.state.workspace = workspace
        workspace.worker = asyncio.create_task(workspace.run_queue())
        audit.record(db, "server.started", f"{settings.host}:{settings.port}", actor="system",
                     version=__version__, runbooks=len(books), recovered_steps=recovered, interrupted_agent_runs=interrupted)
        log.info("LocalPilot started", extra={"port": settings.port, "data_dir": str(settings.data_dir)})
        yield
        await workspace.shutdown()
        await droid.shutdown()
        engine.shutdown()
        audit.record(db, "server.stopped", f"{settings.host}:{settings.port}", actor="system")
        db.dispose()

    app = FastAPI(title="LocalPilot", version=__version__, lifespan=lifespan)

    allowed_hosts = {f"127.0.0.1:{settings.port}", f"localhost:{settings.port}", "testserver",
                     "127.0.0.1:5173", "localhost:5173"}
    allowed_origins = {f"http://{h}" for h in allowed_hosts}

    @app.middleware("http")
    async def local_only_guard(request: Request, call_next):
        # Host check blocks DNS-rebinding; the custom header on state-changing calls forces a CORS
        # preflight (which this server never approves), so other websites cannot drive the API.
        host = request.headers.get("host", "")
        if host not in allowed_hosts and not settings.allow_non_loopback_bind:
            return JSONResponse({"error": "Host not allowed"}, status_code=421)
        if request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin not in allowed_origins and not urlparse(origin).scheme.startswith("vscode"):
                return JSONResponse({"error": "Origin not allowed"}, status_code=403)
            if request.headers.get(CLIENT_HEADER) != "1":
                return JSONResponse({"error": f"Missing {CLIENT_HEADER} header"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(RunbookError)
    async def runbook_error(_req: Request, exc: RunbookError):
        return JSONResponse({"error": str(exc), "detail": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(AgentError)
    async def agent_error(_req: Request, exc: AgentError):
        return JSONResponse({"error": str(exc)}, status_code=exc.status_code)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "version": __version__}

    app.include_router(router)
    app.include_router(agents_router)
    app.include_router(workspace_router)

    if settings.web_dist and (settings.web_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=settings.web_dist, html=True), name="web")
    return app


def run() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run(create_app(s), host=s.host, port=s.port, log_config=None)


if __name__ == "__main__":
    run()
