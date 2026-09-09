"""Installation host with immutable per-candidate ASGI applications.

The dispatcher never replaces global state: a child application and every task
it launches keep the same CandidateRuntime for their entire lifetime.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import re
import secrets
import time
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers

from app.candidates import CandidateRegistry
from app.candidate_runtime import CandidateRuntimeManager

STATIC = Path(__file__).parent / "static"


def candidate_info(record):
    return {"candidate_id": record.candidate_id, "display_name": record.display_name,
            "submission_mode": record.submission_mode}


def configure_scheduler(runtime, child):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app import scheduler as cycles
    from app.routers.scraping import start_scrape

    scheduler = AsyncIOScheduler()
    runtime.state.scheduler = scheduler

    async def scrape():
        # Same guard/progress as manual launches; never race another scrape.
        config = await runtime.state.bg_db.get_search_config() or {}
        if config.get("search_terms"):
            await start_scrape(child, force=False)

    async def scoring():
        if (runtime.state.scrape_progress or {}).get("active"):
            return
        await cycles.run_location_classification(runtime.state.bg_db, runtime.state.ai_client)
        await runtime.state.score_unscored(runtime.state.bg_db)

    async def enrichment():
        if not (runtime.state.scrape_progress or {}).get("active"):
            await cycles.run_enrichment_cycle(runtime.state.bg_db)

    async def reminders():
        await cycles.run_reminder_check(runtime.state.bg_db, runtime.state.embedding_client)

    async def embeddings():
        await cycles.run_job_embedding_cycle(runtime.state.bg_db, runtime.state.embedding_client)
        await cycles.run_context_embedding_cycle(runtime.state.bg_db, runtime.state.embedding_client)

    operations = [
        ("scrape_cycle", scrape, 6), ("scoring_cycle", scoring, 1),
        ("enrichment_cycle", enrichment, 2),
        ("maintenance_cycle", lambda: cycles.run_maintenance_cycle(runtime.state.bg_db), 24),
        ("reminder_check", reminders, 12),
        ("alert_check", lambda: cycles.run_alert_check(runtime.state.bg_db), 1),
        ("embedding_cycle", embeddings, 2),
    ]
    for name, operation, hours in operations:
        async def run(operation=operation):
            await runtime.state.spawn(operation())
        scheduler.add_job(run, "interval", hours=hours, id=name, max_instances=1, coalesce=True)
    # Email remains opt-in through each candidate's saved email settings.
    async def digest():
        await runtime.state.spawn(cycles.run_digest_cycle(runtime.state.bg_db))
    scheduler.add_job(digest, "cron", hour=8, id="digest_cycle")
    scheduler.start()


class CandidateDispatcher:
    def __init__(self, app, host):
        self.app, self.host = app, host

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        headers = Headers(scope=scope)
        origin = headers.get("origin")
        local_origin = f"{scope.get('scheme', 'http')}://{headers.get('host', '')}"
        extension = bool(origin and origin.startswith("chrome-extension://"))
        pairing = headers.get("x-careerpulse-pairing")
        # No cross-site API access or writes, including simple form requests.
        if origin and origin != local_origin and not (extension and pairing):
            return await JSONResponse({"detail": "Cross-origin access denied"}, 403)(scope, receive, send)
        match = re.fullmatch(r"/api/candidates/([^/]+)/(.*)", path)
        if match and match[2] != "pairing":
            candidate_id, suffix = match.groups()
            try:
                child = await self.host.state.get_child(candidate_id)
            except KeyError:
                return await JSONResponse({"detail": "Candidate not found"}, 404)(scope, receive, send)
            except FileNotFoundError:
                return await JSONResponse({"detail": "Candidate storage missing; recovery required"}, 409)(scope, receive, send)
            if extension or pairing:
                token_file = self.host.state.registry.get(candidate_id).directory / "browser" / "pairing-token"
                expected = token_file.read_text() if token_file.exists() else ""
                if not expected or not secrets.compare_digest(pairing or "", expected):
                    return await JSONResponse({"detail": "Browser pairing does not match candidate"}, 403)(scope, receive, send)
            child_scope = dict(scope)
            child_scope["path"] = "/" + suffix if suffix.startswith("ical/") else "/api/" + suffix
            child_scope["raw_path"] = child_scope["path"].encode()
            child_scope["root_path"] = ""
            child_scope["path_params"] = {"candidate_id": candidate_id}
            # Keep direct generation/settings requests visible to the stop script.
            writing = scope.get("method") not in {"GET", "HEAD", "OPTIONS"}
            child.state.in_flight += 1
            if writing:
                child.state.active_requests += 1
            try:
                return await child(child_scope, receive, send)
            finally:
                child.state.in_flight -= 1
                if writing:
                    child.state.active_requests -= 1
        management = re.fullmatch(r"/api/candidates/[^/]+", path)
        if path.startswith("/api/") and path not in {"/api/candidates", "/api/health", "/api/runtime/progress"} and not management and not (match and match[2] == "pairing"):
            return await JSONResponse({"detail": "Explicit candidate URL required"}, 409)(scope, receive, send)
        if extension:
            return await JSONResponse({"detail": "Use the paired candidate API"}, 403)(scope, receive, send)
        return await self.app(scope, receive, send)


def create_multi_app(data_root=None, testing=False):
    @asynccontextmanager
    async def lifespan(host):
        registry = CandidateRegistry(data_root)
        from app.installation_lock import InstallationLock
        installation_lock = InstallationLock(registry.root)
        manager = CandidateRuntimeManager(registry)
        host.state.registry = registry
        host.state.candidate_runtimes = manager
        children = {}
        lock = asyncio.Lock()

        async def get_child(candidate_id):
            async with lock:
                runtime = await manager.get(candidate_id)
                if candidate_id not in children:
                    from app.main import create_app
                    # testing=True prevents recursion and legacy lifespan is never run.
                    child = create_app(testing=True)
                    child.state = runtime.state
                    child.state.testing = testing
                    child.state.start_time = time.monotonic()
                    child.state.settings = SimpleNamespace(anthropic_api_key="")
                    children[candidate_id] = child
                    if not testing:
                        configure_scheduler(runtime, child)
                return children[candidate_id]

        host.state.get_child = get_child
        host.state.children = children
        host.state.lifecycle_lock = lock
        try:
            # Start every candidate's schedule even when no browser tab is open.
            for record in registry.list():
                await get_child(record.candidate_id)
            yield
        finally:
            try:
                await manager.close()
            finally:
                installation_lock.close()

    host = FastAPI(title="CareerPulse profiles", lifespan=lifespan)
    host.add_middleware(CandidateDispatcher, host=host)

    @host.get("/api/health")
    async def health():
        return {"status": "healthy", "db": "ok", "multi_profile": True,
                "candidate_count": len(host.state.registry.list())}

    @host.get("/api/runtime/progress")
    async def progress():
        states = []
        for record in host.state.registry.list():
            child = await host.state.get_child(record.candidate_id)
            state = child.state
            states.append({**candidate_info(record), "scrape": state.scrape_progress,
                           "score": state.scoring_progress,
                           "requests_active": state.active_requests,
                           "tasks_active": len(host.state.candidate_runtimes._runtimes[record.candidate_id]._tasks)})
        return {"candidates": states, "active": any(s["tasks_active"] or s["requests_active"] for s in states)}

    @host.get("/api/candidates")
    async def candidates():
        return [candidate_info(r) for r in host.state.registry.list()]

    @host.post("/api/candidates", status_code=201)
    async def create_candidate(request: Request):
        body = await request.json()
        name = body.get("display_name") if isinstance(body, dict) else None
        if not isinstance(name, str):
            raise HTTPException(400, "Display name required")
        try:
            record = await host.state.registry.create(name)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        await host.state.get_child(record.candidate_id)
        return candidate_info(record)

    @host.patch("/api/candidates/{candidate_id}")
    async def rename_candidate(candidate_id: str, request: Request):
        body = await request.json()
        name = body.get("display_name") if isinstance(body, dict) else None
        if not isinstance(name, str):
            raise HTTPException(400, "Display name required")
        async with host.state.lifecycle_lock:
            try:
                return candidate_info(host.state.registry.rename(candidate_id, name))
            except KeyError:
                raise HTTPException(404, "Candidate not found") from None
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc

    @host.delete("/api/candidates/{candidate_id}")
    async def delete_candidate(candidate_id: str, request: Request):
        body = await request.json()
        async with host.state.lifecycle_lock:
            try:
                record = host.state.registry.get(candidate_id)
            except KeyError:
                raise HTTPException(404, "Candidate not found") from None
            if not isinstance(body, dict) or body.get("confirm_name") != record.display_name:
                raise HTTPException(400, "Enter the profile name to confirm deletion")
            runtime = host.state.candidate_runtimes._runtimes.get(candidate_id)
            if runtime and (runtime.state.in_flight or runtime._tasks):
                raise HTTPException(409, "Profile is busy. Close its tabs and wait for background work to finish, then retry.")
            await host.state.candidate_runtimes.remove(candidate_id)
            host.state.children.pop(candidate_id, None)
            host.state.registry.delete(candidate_id)
            return {"ok": True}

    @host.post("/api/candidates/{candidate_id}/pairing")
    async def pairing(candidate_id: str):
        try:
            record = host.state.registry.get(candidate_id)
        except KeyError as exc:
            raise HTTPException(404, "Candidate not found") from exc
        token_file = record.directory / "browser" / "pairing-token"
        token_file.parent.mkdir(exist_ok=True)
        if not token_file.exists():
            token_file.write_text(secrets.token_urlsafe(32))
        return {**candidate_info(record), "token": token_file.read_text()}

    @host.get("/")
    async def home():
        return FileResponse(STATIC / "profiles.html")

    @host.get("/profiles/{candidate_id}/")
    async def profile_page(candidate_id: str):
        try:
            await host.state.get_child(candidate_id)
        except KeyError as exc:
            raise HTTPException(404, "Candidate not found") from exc
        return FileResponse(STATIC / "index.html")

    host.mount("/static", StaticFiles(directory=STATIC), name="static")
    return host
