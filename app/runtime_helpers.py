"""Candidate-owned service helpers, shared with the legacy single-user app."""

import asyncio
import logging

from app.ai_client import AIClient

logger = logging.getLogger(__name__)


def bind_runtime_helpers(state):
    state.spawn = getattr(state, "spawn", asyncio.create_task)
    state.scoring_progress = None
    state.scrape_progress = None
    state.scrape_task = None
    state.scoring_lock = asyncio.Lock()
    state.notification_subscribers: list[asyncio.Queue] = []
    state.notification_lock = asyncio.Lock()
    state.queue_subscribers: list[asyncio.Queue] = []
    state.alert_threshold = 80

    # --- Shared helpers attached to state for router access ---

    async def _broadcast_notification(notification: dict):
        async with state.notification_lock:
            for queue in list(state.notification_subscribers):
                try:
                    queue.put_nowait(notification)
                except asyncio.QueueFull:
                    pass

    async def _check_high_score_alerts(db, job_id: int, score: int, job_title: str, company: str):
        if score >= state.alert_threshold:
            title = f"High score: {job_title}"
            message = f"{company} — Score {score}"
            notif_id = await db.insert_notification(job_id, "high_score", title, message)
            notif = {"id": notif_id, "job_id": job_id, "type": "high_score", "title": title, "message": message, "read": 0}
            await _broadcast_notification(notif)

    async def _score_unscored(db):
        async with state.scoring_lock:
            matcher = state.matcher
            if not matcher:
                logger.warning("Matcher not available, skipping scoring")
                return
            matcher.candidate_profile = await db.get_user_profile() or {}
            all_unscored = await db.get_unscored_jobs(limit=10000)
            total = len(all_unscored)
            if total == 0:
                return
            state.scoring_progress = {"scored": 0, "total": total, "active": True}
            scored = 0
            empty_batches = 0
            batch_size = 5
            try:
                for i in range(0, total, batch_size):
                    batch = all_unscored[i:i + batch_size]
                    results = await matcher.score_batch(batch)
                    if not results:
                        empty_batches += 1
                        if empty_batches >= 2:
                            logger.warning("Scoring stopped after consecutive batches produced no valid scores; check response validation and provider errors above")
                            break
                        continue
                    empty_batches = 0
                    for r in results:
                        job = await db.get_job(r["job_id"])
                        if job:
                            from app.eligibility import evaluate_job
                            eligibility = evaluate_job(job, matcher.candidate_profile, await db.get_company(job["company"]))
                            await db.set_job_eligibility(r["job_id"], eligibility)
                        await db.insert_score(
                            r["job_id"], r["score"], r["reasons"],
                            r["concerns"], r["keywords"],
                            role_match=r.get("role_match", True),
                        )
                        await asyncio.sleep(0)  # Yield between DB writes
                        if job:
                            await _check_high_score_alerts(db, r["job_id"], r["score"], job["title"], job["company"])
                    scored += len(results)
                    state.scoring_progress = {"scored": scored, "total": total, "active": True}
                    logger.info(f"Scored {scored}/{total} jobs")
                    # Yield to event loop between batches — give API requests time to process
                    await asyncio.sleep(0.5)
            finally:
                state.scoring_progress = {"scored": scored, "total": total, "active": False}
                logger.info(f"Scoring complete: {scored}/{total} jobs")

    async def _reinit_ai_services(client: AIClient | None, resume_text: str = ""):
        """Re-initialize matcher and tailor with new AI client."""
        state.ai_client = client
        if client and resume_text:
            from app.matcher import JobMatcher
            from app.tailoring import Tailor
            candidate_focus = None
            search_config = await state.db.get_search_config()
            if search_config:
                candidate_focus = {
                    "job_titles": search_config.get("job_titles", []),
                    "seniority": search_config.get("seniority", ""),
                    "summary": search_config.get("summary", ""),
                    "key_skills": search_config.get("key_skills", []),
                }
            state.matcher = JobMatcher(client, resume_text, candidate_focus=candidate_focus, candidate_profile=await state.db.get_user_profile(), require_evidence=True)
            state.tailor = Tailor(client, resume_text)
        else:
            state.matcher = None
            state.tailor = None

    async def _save_parsed_profile(db, profile_data: dict):
        """Save AI-parsed resume data into profile tables, merging with existing."""
        try:
            personal = profile_data.get("personal", {})
            if personal:
                clean = {k: v for k, v in personal.items() if v is not None}
                if clean:
                    existing = await db.get_user_profile() or {}
                    merged = {}
                    for k, v in clean.items():
                        existing_val = existing.get(k)
                        if not existing_val or existing_val == "":
                            merged[k] = v
                    if "first_name" in clean and "last_name" in clean:
                        if not existing.get("full_name"):
                            merged["full_name"] = f"{clean['first_name']} {clean['last_name']}"
                    if merged:
                        await db.save_user_profile(**merged)

            for key, endpoint in [
                ("work_history", "save_work_history"),
                ("education", "save_education"),
                ("certifications", "save_certification"),
                ("skills", "save_skill"),
                ("languages", "save_language"),
            ]:
                items = profile_data.get(key, [])
                if not items:
                    continue
                full = await db.get_full_profile()
                existing_items = full.get(key, [])
                if existing_items:
                    continue
                save_fn = getattr(db, endpoint)
                for item in items:
                    clean_item = {k: v for k, v in item.items() if v is not None}
                    if clean_item:
                        await save_fn(clean_item)

            logger.info("Parsed profile data saved from resume")
        except Exception as e:
            logger.error(f"Failed to save parsed profile: {e}")

    # Expose shared helpers on state for routers and lifespan
    state.score_unscored = _score_unscored
    state.reinit_ai_services = _reinit_ai_services
    state.save_parsed_profile = _save_parsed_profile
