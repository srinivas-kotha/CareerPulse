import asyncio
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock
from types import SimpleNamespace

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from app.candidates import CandidateRegistry
from app.candidate_runtime import CandidateRuntimeManager, require_candidate_runtime


async def test_runtime_services_and_inflight_worker_keep_original_identity(tmp_path):
    registry = CandidateRegistry(tmp_path)
    first = await registry.create("First")
    second = await registry.create("Second")
    async with CandidateRuntimeManager(registry) as manager:
        a, again, b = await asyncio.gather(manager.get(first.candidate_id),
                                         manager.get(first.candidate_id),
                                         manager.get(second.candidate_id))
        assert a is again and a is not b
        assert a.state.db is not a.state.bg_db
        assert a.state.scoring_lock is not b.state.scoring_lock
        assert a.state.notification_subscribers is not b.state.notification_subscribers
        assert a.state.queue_subscribers is not b.state.queue_subscribers
        assert a.state.ai_client is b.state.ai_client is None
        with pytest.raises(FrozenInstanceError):
            a.context = b.context
        entered, release = asyncio.Event(), asyncio.Event()

        async def operation(owner):
            entered.set()
            await release.wait()
            await owner.state.bg_db.save_user_profile(full_name="First worker result")
            return owner.candidate_id

        task = a.start_task(operation)
        await entered.wait()
        await b.state.db.save_user_profile(full_name="Second request")
        release.set()
        assert await task == first.candidate_id
        assert (await a.state.db.get_user_profile())["full_name"] == "First worker result"
        assert (await b.state.db.get_user_profile())["full_name"] == "Second request"
        a.state.browser_pool.save_cookies("example.invalid", [{"name": "test", "value": "a"}])
        assert b.state.browser_pool._load_cookies("example.invalid") == []
        assert a.state.browser_pool._load_cookies("example.invalid")[0]["value"] == "a"


async def test_runtime_shutdown_cancels_worker_before_closing_connections(tmp_path):
    registry = CandidateRegistry(tmp_path)
    record = await registry.create("Example")
    manager = CandidateRuntimeManager(registry)
    runtime = await manager.get(record.candidate_id)
    entered = asyncio.Event()
    cleanup = []

    async def worker(owner):
        try:
            entered.set()
            await asyncio.Event().wait()
        finally:
            # Cancellation cleanup still has a usable candidate connection.
            await owner.state.bg_db.save_user_profile(full_name="Cleanup")
            cleanup.append(True)

    task = runtime.start_task(worker)
    await entered.wait()
    await manager.close()
    assert task.cancelled() and cleanup == [True]
    with pytest.raises(RuntimeError, match="closing"):
        runtime.start_task(worker)
    with pytest.raises(RuntimeError, match="closed"):
        await manager.get(record.candidate_id)
    async with registry.context(record.candidate_id) as context:
        assert (await context.db.get_user_profile())["full_name"] == "Cleanup"


async def test_scoring_and_notifications_stay_with_launching_candidate(tmp_path):
    registry = CandidateRegistry(tmp_path)
    first, second = await registry.create("A"), await registry.create("B")
    async with CandidateRuntimeManager(registry) as manager:
        a, b = await manager.get(first.candidate_id), await manager.get(second.candidate_id)
        job = dict(title="Platform Engineer", company="Example", location="Remote",
                   salary_min=None, salary_max=None, description="Synthetic listing",
                   url="https://example.invalid/role", posted_date=None,
                   application_method="url", contact_email=None)
        job_a = await a.state.db.insert_job(**job)
        job_b = await b.state.db.insert_job(**job)
        await a.state.db.db.execute("UPDATE jobs SET location_classified = 1 WHERE id = ?", (job_a,))
        await a.state.db.db.commit()
        a_notifications, b_notifications = asyncio.Queue(), asyncio.Queue()
        a.state.notification_subscribers.append(a_notifications)
        b.state.notification_subscribers.append(b_notifications)
        entered, release = asyncio.Event(), asyncio.Event()

        async def score(batch):
            entered.set()
            await release.wait()
            return [{"job_id": job_a, "score": 90, "reasons": ["Synthetic"],
                     "concerns": [], "keywords": []}]

        a.state.matcher = SimpleNamespace(score_batch=score)
        task = a.start_task(lambda owner: owner.state.score_unscored(owner.state.bg_db))
        await asyncio.wait_for(entered.wait(), timeout=5)
        # A settings change for the visible B profile cannot rebind A's work.
        await b.state.reinit_ai_services(None)
        release.set()
        await task
        assert (await a.state.db.get_score(job_a))["match_score"] == 90
        assert await b.state.db.get_score(job_b) is None
        assert a_notifications.qsize() == 1 and b_notifications.empty()
        assert a.state.scoring_progress["active"] is False
        assert b.state.scoring_progress is None


async def test_request_dependency_has_no_legacy_fallback(tmp_path):
    registry = CandidateRegistry(tmp_path)
    a = await registry.create("A")
    b = await registry.create("B")
    async with CandidateRuntimeManager(registry) as manager:
        app = FastAPI()
        app.state.candidate_runtimes = manager
        app.state.db = object()  # Must never be selected by scoped requests.

        @app.get("/api/candidates/{candidate_id}/identity")
        @app.get("/api/identity")
        async def identity(runtime=Depends(require_candidate_runtime)):
            return {"candidate_id": runtime.candidate_id}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            results = await asyncio.gather(*[
                client.get(f"/api/candidates/{r.candidate_id}/identity") for r in (a, b)])
            assert [r.json()["candidate_id"] for r in results] == [a.candidate_id, b.candidate_id]
            assert (await client.get("/api/candidates/default/identity")).status_code == 404
            assert (await client.get("/api/identity")).status_code == 400
        assert len(manager._runtimes) == 2


async def test_failed_initialization_closes_connections_and_can_retry(tmp_path, monkeypatch):
    registry = CandidateRegistry(tmp_path)
    record = await registry.create("Example")
    async with CandidateRuntimeManager(registry) as manager:
        with monkeypatch.context() as scoped:
            scoped.setattr("app.main._init_embedding_client", AsyncMock(side_effect=RuntimeError("startup")))
            with pytest.raises(RuntimeError, match="startup"):
                await manager.get(record.candidate_id)
        assert manager._runtimes == {}
        assert (await manager.get(record.candidate_id)).candidate_id == record.candidate_id


@pytest.mark.parametrize("domain", ["../other", "x/y", "x\\y", "C:other"])
async def test_candidate_cookie_paths_cannot_escape(tmp_path, domain):
    registry = CandidateRegistry(tmp_path)
    record = await registry.create("Example")
    async with CandidateRuntimeManager(registry) as manager:
        runtime = await manager.get(record.candidate_id)
        with pytest.raises(ValueError):
            runtime.state.browser_pool.save_cookies(domain, [])

@pytest.mark.parametrize("failure", [False, True])
async def test_bounded_scoring_preserves_unsampled_jobs_and_reports_failures(tmp_path, failure):
    registry = CandidateRegistry(tmp_path)
    record = await registry.create("Synthetic")
    async with CandidateRuntimeManager(registry) as manager:
        runtime = await manager.get(record.candidate_id)
        db = runtime.state.db
        for i in range(5):
            jid = await db.insert_job(title="Engineer", company="Example", location="Remote",
                salary_min=None, salary_max=None, description="Build Python services",
                url=f"https://example.invalid/{i}", posted_date=None,
                application_method="url", contact_email=None)
            await db.set_job_location_region(jid, "US")
        async def score(batch):
            return [] if failure else [{"job_id": batch[0]["id"], "score": 60,
                "reasons": ["Synthetic"], "concerns": [], "keywords": []}]
        runtime.state.matcher = SimpleNamespace(score_batch=score, last_error_code="invalid_model_response")
        await runtime.state.score_unscored(db, limit=4 if failure else 2)
        progress = runtime.state.scoring_progress
        assert progress["active"] is False
        assert progress["attempted"] == (3 if failure else 2)
        assert progress["failed"] == (3 if failure else 0)
        assert progress["status"] == ("stopped" if failure else "completed")
        assert len(await db.get_unscored_jobs(limit=20)) == (5 if failure else 3)
        assert await db.get_score(5) is None
        if failure:
            assert progress["last_error"] == "invalid_model_response"
        else:
            assert (await db.get_score(1))["match_score"] == 60
        # An empty rerun must replace the old outcome rather than leave stale progress.
        runtime.state.matcher = None
        await runtime.state.score_unscored(db, limit=1)
        assert runtime.state.scoring_progress["status"] == "skipped"
        assert runtime.state.scoring_progress["total"] == 0
