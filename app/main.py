import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import time as _time
from datetime import datetime, timezone

from app.database import Database
from app.ai_client import AIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_ai_client(ai_settings: dict | None, env_key: str = "", allow_env_credentials: bool = True) -> AIClient | None:
    """Build an AIClient from DB settings or env fallback."""
    if ai_settings and ai_settings.get("provider"):
        provider = ai_settings["provider"]
        api_key = ai_settings.get("api_key", "")
        model = ai_settings.get("model", "")
        base_url = ai_settings.get("base_url", "")
        region = ai_settings.get("region", "")
        if provider == "bedrock":
            if not allow_env_credentials and not (api_key and base_url):
                return None
            return AIClient(provider, api_key=api_key, model=model,
                            base_url=base_url, region=region, allow_env_credentials=allow_env_credentials)
        if provider == "ollama":
            return AIClient(provider, model=model, base_url=base_url)
        if api_key:
            return AIClient(provider, api_key=api_key, model=model,
                            base_url=base_url, region=region)
    if env_key:
        return AIClient("anthropic", api_key=env_key)
    return None


async def _init_embedding_client(db):
    """Build an EmbeddingClient from saved DB settings, or None."""
    settings = await db.get_embedding_settings()
    if not settings or not settings.get("provider"):
        return None
    from app.embeddings import EmbeddingClient
    provider = settings["provider"]
    api_key = settings.get("api_key", "")
    model = settings.get("model", "")
    base_url = settings.get("base_url", "")
    dimensions = settings.get("dimensions", 256)
    if provider != "ollama" and not api_key:
        return None
    return EmbeddingClient(provider=provider, api_key=api_key, model=model,
                           base_url=base_url, dimensions=dimensions)


async def lifespan(app: FastAPI):
    db_path = app.state.db_path
    testing = getattr(app.state, "testing", False)
    os.makedirs(os.path.dirname(db_path) or "data", exist_ok=True)
    # Stale-state recovery: a crashed previous run must never leave active=true.
    app.state.scrape_progress = None
    app.state.scrape_task = None
    app.state.db = Database(db_path)
    await app.state.db.init()
    await app.state.db.migrate_resume_from_search_config()
    await app.state.db.migrate_normalize_posted_dates()

    # Separate DB connection for background tasks (scoring, scraping, enrichment)
    # so they don't block API request handling on the main connection.
    # In testing, share the same connection to avoid WAL visibility issues.
    if not testing:
        app.state.bg_db = Database(db_path)
        await app.state.bg_db.init()
    else:
        app.state.bg_db = app.state.db

    # Auto-dismiss stale job listings on startup
    if not testing:
        try:
            dismissed = await app.state.db.auto_dismiss_stale()
            if dismissed:
                logger.info(f"Startup: auto-dismissed {dismissed} stale jobs")
        except Exception:
            logger.exception("Startup auto-dismiss failed")

    if not testing:
        from app.config import Settings
        from app.scrapers import ALL_SCRAPERS
        from app.scheduler import run_scrape_cycle, run_enrichment_cycle, run_maintenance_cycle, run_reminder_check, run_digest_cycle, run_alert_check, run_job_embedding_cycle, run_context_embedding_cycle, run_location_classification

        settings = Settings()

        resume_text = ""
        if os.path.exists(settings.resume_path):
            with open(settings.resume_path) as f:
                resume_text = f.read()

        if not resume_text:
            config = await app.state.db.get_search_config()
            if config and config.get("resume_text"):
                resume_text = config["resume_text"]

        ai_settings = await app.state.db.get_ai_settings()
        client = _build_ai_client(ai_settings, settings.anthropic_api_key)

        candidate_focus = None
        search_config = await app.state.db.get_search_config()
        if search_config:
            candidate_focus = {
                "job_titles": search_config.get("job_titles", []),
                "seniority": search_config.get("seniority", ""),
                "summary": search_config.get("summary", ""),
                "key_skills": search_config.get("key_skills", []),
            }

        logger.info(f"Lifespan: client={'yes' if client else 'no'}, resume={len(resume_text)} chars")
        if client and resume_text:
            from app.matcher import JobMatcher
            from app.tailoring import Tailor
            app.state.matcher = JobMatcher(client, resume_text, candidate_focus=candidate_focus, candidate_profile=await app.state.db.get_user_profile(), require_evidence=True)
            app.state.tailor = Tailor(client, resume_text)
            logger.info("Matcher and Tailor initialized")
        else:
            app.state.matcher = None
            app.state.tailor = None
            logger.warning("Matcher NOT initialized - client=%s, resume=%d chars",
                           bool(client), len(resume_text))

        app.state.ai_client = client
        app.state.settings = settings

        app.state.embedding_client = await _init_embedding_client(app.state.db)

        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        scheduler = AsyncIOScheduler()

        async def scheduled_scrape():
            try:
                bg_db = app.state.bg_db
                config = await bg_db.get_search_config()
                terms = config["search_terms"] if config else []
                keys = await bg_db.get_scraper_keys()
                scrapers = [s(search_terms=terms, scraper_keys=keys) for s in ALL_SCRAPERS]
                await run_scrape_cycle(bg_db, scrapers, search_terms=terms, scraper_keys=keys)
            except Exception:
                logger.exception("Scheduled scrape failed")

        async def scheduled_enrichment():
            try:
                await run_enrichment_cycle(app.state.bg_db)
            except Exception:
                logger.exception("Scheduled enrichment failed")

        async def scheduled_scoring():
            try:
                await run_location_classification(app.state.bg_db, app.state.ai_client)
                await app.state.score_unscored(app.state.bg_db)
            except Exception:
                logger.exception("Scheduled scoring failed")

        async def scheduled_maintenance():
            try:
                await run_maintenance_cycle(app.state.bg_db)
            except Exception:
                logger.exception("Scheduled maintenance failed")

        async def scheduled_reminder_check():
            try:
                due = await run_reminder_check(app.state.bg_db, embedding_client=app.state.embedding_client)
                for r in due:
                    await app.state.bg_db.add_event(
                        r["job_id"], "reminder_due",
                        f"Follow-up reminder due for {r.get('company', 'unknown')}"
                    )
            except Exception:
                logger.exception("Scheduled reminder check failed")

        async def scheduled_digest():
            try:
                await run_digest_cycle(app.state.bg_db)
            except Exception:
                logger.exception("Scheduled digest failed")

        async def scheduled_alert_check():
            try:
                await run_alert_check(app.state.bg_db)
            except Exception:
                logger.exception("Scheduled alert check failed")

        async def scheduled_embedding():
            try:
                await run_job_embedding_cycle(app.state.bg_db, app.state.embedding_client)
                await run_context_embedding_cycle(app.state.bg_db, app.state.embedding_client)
            except Exception:
                logger.exception("Scheduled embedding failed")

        scheduler.add_job(
            scheduled_scrape, "interval",
            hours=settings.scrape_interval_hours,
            id="scrape_cycle",
        )
        scheduler.add_job(
            scheduled_enrichment, "interval",
            hours=2,
            id="enrichment_cycle",
        )
        scheduler.add_job(
            scheduled_scoring, "interval",
            hours=1,
            id="scoring_cycle",
        )
        scheduler.add_job(
            scheduled_maintenance, "interval",
            hours=24,
            id="maintenance_cycle",
        )
        scheduler.add_job(
            scheduled_reminder_check, "interval",
            hours=12,
            id="reminder_check",
        )
        scheduler.add_job(
            scheduled_digest, "cron",
            hour=8,
            id="digest_cycle",
        )
        scheduler.add_job(
            scheduled_alert_check, "interval",
            hours=1,
            id="alert_check",
        )
        scheduler.add_job(
            scheduled_embedding, "interval",
            hours=2,
            id="embedding_cycle",
        )
        scheduler.start()
        app.state.scheduler = scheduler
    else:
        app.state.matcher = None
        app.state.tailor = None
        app.state.ai_client = None
        app.state.embedding_client = None
        app.state.scheduler = None

    app.state.start_time = _time.monotonic()

    yield

    if getattr(app.state, "scheduler", None):
        app.state.scheduler.shutdown(wait=False)
    from app.browser_pool import shutdown_browser_pool
    await shutdown_browser_pool()
    bg_db = getattr(app.state, "bg_db", None)
    if bg_db and bg_db is not app.state.db:
        await bg_db.close()
    await app.state.db.close()


def create_app(db_path: str = "data/jobfinder.db", testing: bool = False,
               data_root: str | None = None) -> FastAPI:
    if data_root is not None or (not testing and os.environ.get("CAREERPULSE_MULTI_PROFILE") == "1"):
        from app.multi_profile import create_multi_app
        return create_multi_app(data_root, testing=testing)
    app = FastAPI(title="CareerPulse", lifespan=lifespan)
    app.state.db_path = db_path
    app.state.testing = testing

    from app.runtime_helpers import bind_runtime_helpers
    bind_runtime_helpers(app.state)

    # --- Register routers ---
    from app.routers import jobs, tailoring, pipeline, queue, contacts, analytics, settings, alerts, scraping, autofill, interviews, calendar
    app.include_router(jobs.router)
    app.include_router(tailoring.router)
    app.include_router(pipeline.router)
    app.include_router(queue.router)
    app.include_router(contacts.router)
    app.include_router(analytics.router)
    app.include_router(settings.router)
    app.include_router(alerts.router)
    app.include_router(scraping.router)
    app.include_router(autofill.router)
    app.include_router(interviews.router)
    app.include_router(calendar.router)

    # --- Static files ---
    if not testing:
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        if os.path.exists(static_dir):
            app.mount("/static", StaticFiles(directory=static_dir), name="static")

            @app.get("/")
            async def index():
                return FileResponse(os.path.join(static_dir, "index.html"))

    return app


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"****{key[-4:]}"
