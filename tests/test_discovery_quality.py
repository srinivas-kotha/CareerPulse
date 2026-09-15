import asyncio
import json
from types import SimpleNamespace

import pytest

from app.database import Database
from app.discovery import availability_from_response, canonical_url, check_availability, quality_issues, same_listing
from app.runtime_helpers import bind_runtime_helpers
from app.scoring_evidence import excerpts, resolve_evidence
from app.scrapers.hackernews import parse_hiring_header


def listing(**changes):
    return dict(title="Backend Engineer", company="Example", location="Chicago, IL",
                description="Build Python APIs and maintain distributed services. " * 6,
                url="https://example.com/jobs/ONE", **changes)


@pytest.mark.parametrize("header", [
    "Example | Chicago, IL | Backend Engineer | Full-time",
    "Example | Backend Engineer | Chicago, IL | Full-time",
])
def test_hn_role_not_fixed_position(header):
    result = parse_hiring_header(header)
    assert result == {"company": "Example", "title": "Backend Engineer", "location": "Chicago, IL"}


def test_hn_ambiguous_header_is_not_invented():
    assert parse_hiring_header("Example | London, UK | Full-time") is None


@pytest.mark.parametrize("title", ["", "London, UK", "REMOTE (EMEA/APAC)", "Example ("])
def test_malformed_titles_need_review(title):
    assert quality_issues({**listing(), "title": title})


def test_tracking_dedup_preserves_identity():
    base = "https://example.com/jobs/ABC?id=123"
    assert canonical_url(base + "&utm_source=mail#apply") == canonical_url(base)
    assert canonical_url(base) != canonical_url(base.replace("ABC", "abc"))
    assert canonical_url(base) != canonical_url(base.replace("123", "124"))
    assert same_listing(listing(), {**listing(), "url": listing()["url"] + "?utm_source=board"})


@pytest.mark.parametrize("changes", [
    {"title": "Senior Backend Engineer"}, {"location": "Austin, TX"},
    {"url": "https://example.com/jobs/TWO"}, {"description": "Different work entirely"},
])
def test_distinct_requisitions_are_not_merged(changes):
    assert not same_listing(listing(), {**listing(), "url": "https://other.com/jobs/2", **changes})


def test_identical_cross_source_copy_can_merge():
    assert same_listing(listing(), {**listing(), "url": "https://board.com/jobs/2"})


@pytest.mark.parametrize("status,body,expected", [
    (404, "", "closed"), (410, "", "closed"), (403, "", "unknown"), (429, "", "unknown"),
    (503, "", "unknown"), (200, "<h1>Job no longer available</h1>", "closed"),
    (200, "<h1>Careers</h1>", "unknown"),
    (200, '<h1>Backend Engineer</h1><aside>Other job is closed</aside>', "unknown"),
])
def test_availability_is_conservative(status, body, expected):
    assert availability_from_response(status, body, listing())[0] == expected


def test_matching_structured_listing_expiry():
    def page(title, date):
        return '<script type="application/ld+json">' + json.dumps({"@type": "JobPosting", "title": title, "validThrough": date}) + '</script>'
    assert availability_from_response(200, page("Backend Engineer", "2099-01-01"), listing())[0] == "available"
    assert availability_from_response(200, page("Backend Engineer", "2020-01-01"), listing())[0] == "closed"
    assert availability_from_response(200, page("Other Engineer", "2020-01-01"), listing())[0] == "unknown"


async def test_availability_blocks_private_redirect(httpx_mock, monkeypatch):
    async def public(url):
        return "example.com" in url
    monkeypatch.setattr("app.discovery.public_url", public)
    httpx_mock.add_response(url=listing()["url"], status_code=302, headers={"location": "http://127.0.0.1/secret"})
    result = await check_availability(listing())
    assert result["status"] == "unknown"
    assert "public" in result["reason"]
    assert len(httpx_mock.get_requests()) == 1


async def test_dead_primary_does_not_hide_available_alternate(monkeypatch):
    from app.discovery import check_known_sources
    from unittest.mock import AsyncMock
    db = SimpleNamespace(get_sources=AsyncMock(return_value=[{'source_url': 'https://other.com/job'}]))
    async def check(job):
        return {'status': 'available' if 'other.com' in job['url'] else 'closed', 'reason': 'Synthetic', 'checked_at': 'now'}
    monkeypatch.setattr('app.discovery.check_availability', check)
    assert (await check_known_sources(db, {**listing(), 'id': 1}))['status'] == 'available'


async def test_truncated_model_response_is_job_local():
    from app.matcher import JobMatcher
    from unittest.mock import AsyncMock
    matcher = JobMatcher(SimpleNamespace(provider='ollama', chat=AsyncMock(side_effect=RuntimeError('Ollama response exceeded output token limit'))),
                         'Built Python APIs.', require_evidence=True)
    assert await matcher.score_job('Build Python APIs.') is None
    assert matcher.last_error_code == 'invalid_model_response'


def test_high_scores_reject_repeated_source_passage():
    from app.matcher import JobMatcher
    result = {'score': 80, 'role_match': True, 'reasons': [], 'concerns': [],
              'category_scores': {'role': 25, 'skills': 25, 'experience': 15, 'logistics': 15},
              'evidence': [{'job': 'Build Python APIs.', 'resume': 'Built Python APIs.'},
                           {'job': 'Build Python APIs.', 'resume': 'Maintained cloud services.'}]}
    with pytest.raises(ValueError, match='distinct excerpts'):
        JobMatcher._validate_evidence(result, 'Build Python APIs.', 'Built Python APIs. Maintained cloud services.')


def test_evidence_ids_copy_sources_and_reject_invalid_ids():
    job = excerpts("Build Python APIs. Maintain distributed services.")
    resume = excerpts("Built Python APIs. Maintained distributed services.")
    result = {"evidence": [{"job_id": 0, "resume_id": 0}]}
    resolve_evidence(result, job, resume)
    assert result["evidence"] == [{"job": "Build Python APIs.", "resume": "Built Python APIs."}]
    for pair in ({"job_id": -1, "resume_id": 0}, {"job_id": True, "resume_id": 0}, {"job_id": 0, "resume_id": 0, "job": "invented"}):
        with pytest.raises(ValueError):
            resolve_evidence({"evidence": [pair]}, job, resume)


@pytest.fixture
async def db(tmp_path):
    db = Database(str(tmp_path / "jobs.db"))
    await db.init()
    yield db
    await db.close()


async def add_job(db, index, **changes):
    job = {**listing(), "url": f"https://example.com/{index}", **changes}
    jid = await db.insert_job(**job, salary_min=None, salary_max=None, posted_date=None, application_method="url", contact_email=None)
    await db.set_job_location_region(jid, "US")
    return jid


async def test_audit_preserves_records_and_scores(db):
    first = await add_job(db, 1)
    # Simulate a historical tracking duplicate retained by an older version.
    cursor = await db.db.execute("""INSERT INTO jobs (title,company,location,description,url,dedup_hash,created_at,location_classified)
        SELECT title,company,location,description,url || '?utm_source=x','legacy-duplicate',created_at,location_classified FROM jobs WHERE id=?""", (first,))
    duplicate = cursor.lastrowid
    await db.db.commit()
    malformed = await add_job(db, 3, title="London, UK")
    await db.insert_score(first, 75, ["Synthetic"], [], [])
    result = await db.audit_discovery()
    assert result == {"checked": 3, "repaired": 0, "review": 1, "duplicates": 1}
    assert (await db.get_job(duplicate))["duplicate_of"] == first
    assert (await db.get_job(malformed))["dismissed"] == 0
    assert (await db.get_score(first))["match_score"] == 75
    assert len(await db.list_jobs()) == 3
    assert len(await db.list_jobs(include_review=False)) == 1
    assert await db.get_unscored_jobs() == []
    assert await db.audit_discovery() == result


async def test_failure_fairness_cooldown_and_manual_retry(db):
    first = await add_job(db, 1)
    later = await add_job(db, 2)
    await db.record_scoring_failure(first, "invalid_model_response")
    assert [j["id"] for j in await db.get_unscored_jobs()] == [later]
    for _ in range(2):
        await db.record_scoring_failure(first, "invalid_model_response")
    assert (await db.get_job(first))["scoring_review_required"] == 1
    await db.reset_scoring_retry(first)
    assert [j["id"] for j in await db.get_unscored_jobs()] == [later, first]
    assert await db.get_score(first) is None


async def test_provider_outage_stops_after_three_but_keeps_jobs(db):
    for i in range(5):
        await add_job(db, i)
    async def fail(batch):
        return []
    state = SimpleNamespace(matcher=SimpleNamespace(score_batch=fail, last_error_code="provider_error"))
    bind_runtime_helpers(state)
    await state.score_unscored(db)
    assert state.scoring_progress["status"] == "stopped"
    assert state.scoring_progress["attempted"] == 3
    assert len(await db.get_unscored_jobs()) == 2
    assert len(await db.list_jobs()) == 5


async def test_retry_state_survives_reopen(db):
    first = await add_job(db, 1)
    await db.record_scoring_failure(first, "invalid_model_response")
    await db.close()
    await db.init()
    assert (await db.get_job(first))["scoring_attempts"] == 1
    assert await db.get_unscored_jobs() == []


async def test_canonical_insert_retains_case_sensitive_requisitions(db):
    first = await add_job(db, "ABC")
    tracked = await add_job(db, "ABC?utm_source=mail")
    distinct = await add_job(db, "abc")
    assert first == tracked
    assert first != distinct


async def test_recovery_keeps_real_sponsorship_exclusion(db):
    jid = await add_job(db, 1)
    await db.insert_score(jid, 0, [], ["Not eligible: visa sponsorship is unavailable."], [])
    assert await db.clear_failed_scores() == 0
    assert (await db.get_score(jid))["match_score"] == 0


async def test_scoring_cancellation_preserves_saved_work(db):
    for i in range(2):
        await add_job(db, i)
    entered = asyncio.Event()
    async def score(batch):
        if batch[0]["id"] == 1:
            return [{"job_id": 1, "score": 50, "reasons": [], "concerns": [], "keywords": []}]
        entered.set()
        await asyncio.Event().wait()
    state = SimpleNamespace(matcher=SimpleNamespace(score_batch=score))
    bind_runtime_helpers(state)
    task = asyncio.create_task(state.score_unscored(db))
    await asyncio.wait_for(entered.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert state.scoring_progress["status"] == "interrupted"
    assert (await db.get_score(1))["match_score"] == 50
    assert await db.get_score(2) is None


async def test_quality_audit_and_availability_are_candidate_scoped(tmp_path, monkeypatch):
    from tests.test_multi_profile import installation, add_candidate
    async with installation(tmp_path) as (app, client):
        a, b = await add_candidate(client, 'A'), await add_candidate(client, 'B')
        ar = await app.state.get_child(a.rsplit('/', 1)[1])
        br = await app.state.get_child(b.rsplit('/', 1)[1])
        await add_job(ar.state.db, 1, title="London, UK")
        await add_job(br.state.db, 1, title="London, UK")
        assert (await client.post(a + '/discovery/audit')).status_code == 200
        assert (await client.get(a + '/discovery/health')).json()['quality_review'] == 1
        assert (await client.get(b + '/discovery/health')).json()['quality_review'] == 0
        assert (await client.get(a + '/jobs?include_stale=true')).json()['jobs'] == []
        assert len((await client.get(a + '/jobs?include_stale=true&include_review=true')).json()['jobs']) == 1
        async def closed(job):
            return {"status": "closed", "reason": "HTTP 410", "checked_at": "2026-09-14T00:00:00+00:00"}
        monkeypatch.setattr('app.discovery.check_availability', closed)
        assert (await client.post(a + '/jobs/1/availability')).json()['status'] == 'closed'
        assert (await br.state.db.get_job(1))['availability_status'] == 'unknown'
        assert (await client.post(a + '/jobs/999/availability')).status_code == 404
