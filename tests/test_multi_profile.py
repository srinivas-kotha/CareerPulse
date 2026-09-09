import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.candidates import CandidateRegistry


@asynccontextmanager
async def installation(root):
    app = create_app(data_root=str(root), testing=True)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            yield app, client


async def add_candidate(client, name):
    result = await client.post('/api/candidates', json={'display_name': name})
    assert result.status_code == 201, result.text
    return '/api/candidates/' + result.json()['candidate_id']


async def test_rename_and_delete_full_profile_preserves_other_candidate(tmp_path):
    async with installation(tmp_path) as (app, client):
        a = await add_candidate(client, 'Primary profile')
        b = await add_candidate(client, 'Other')
        candidate_id = a.rsplit('/', 1)[1]
        record = app.state.registry.get(candidate_id)
        (record.directory / 'artifacts' / 'resume.txt').write_text('Synthetic resume')
        assert (await client.post(a + '/pairing')).status_code == 200
        assert (await client.patch(a, json={'display_name': ' '})).status_code == 400
        result = await client.patch(a, json={'display_name': ' Renamed '})
        assert result.json()['display_name'] == 'Renamed'
        assert result.json()['candidate_id'] == candidate_id
        bad = await client.request('DELETE', a, json={'confirm_name': 'Primary profile'})
        assert bad.status_code == 400
        assert record.directory.exists()
        runtime = app.state.candidate_runtimes._runtimes[candidate_id]
        runtime.state.in_flight += 1
        busy = await client.request('DELETE', a, json={'confirm_name': 'Renamed'})
        assert busy.status_code == 409
        runtime.state.in_flight -= 1
        denied = await client.request('DELETE', a, json={'confirm_name': 'Renamed'},
                                      headers={'Origin': 'https://evil.invalid'})
        assert denied.status_code == 403
        result = await client.request('DELETE', a, json={'confirm_name': 'Renamed'})
        assert result.status_code == 200, result.text
        assert not record.directory.exists()
        assert candidate_id not in app.state.candidate_runtimes._runtimes
        assert (await client.get(a + '/profile')).status_code == 404
        assert (await client.post(a + '/pairing')).status_code == 404
        assert (await client.get('/profiles/' + candidate_id + '/')).status_code == 404
        assert (await client.get(b + '/profile')).status_code == 200
    async with installation(tmp_path) as (_, client):
        assert [r['display_name'] for r in (await client.get('/api/candidates')).json()] == ['Other']
        assert (await client.request('DELETE', b, json={'confirm_name': 'Other'})).status_code == 200
        assert (await client.get('/api/candidates')).json() == []


async def test_rename_persists_and_delete_rejects_background_work(tmp_path):
    async with installation(tmp_path) as (app, client):
        base = await add_candidate(client, 'Primary profile')
        assert (await client.patch(base, json={'display_name': 'My profile'})).status_code == 200
        runtime = app.state.candidate_runtimes._runtimes[base.rsplit('/', 1)[1]]
        release = asyncio.Event()
        task = runtime.start_task(lambda _: release.wait())
        assert (await client.request('DELETE', base, json={'confirm_name': 'My profile'})).status_code == 409
        release.set()
        await task
    async with installation(tmp_path) as (_, client):
        assert (await client.get('/api/candidates')).json()[0]['display_name'] == 'My profile'


async def test_concurrent_profiles_same_job_ids_and_restart(tmp_path):
    async with installation(tmp_path) as (app, client):
        a, b = await asyncio.gather(add_candidate(client, 'First'), add_candidate(client, 'Second'))
        await asyncio.gather(client.post(a + '/profile', json={'full_name': 'First person'}),
                             client.post(b + '/profile', json={'full_name': 'Second person'}))
        for base, title in [(a, 'First role'), (b, 'Second role')]:
            response = await client.post(base + '/jobs/save-external', json={
                'title': title, 'company': 'Example', 'url': 'https://example.invalid/job',
                'description': title})
            assert response.status_code == 200, response.text
            assert response.json()['job_id'] == 1
        assert (await client.get(a + '/jobs/1')).json()['title'] == 'First role'
        assert (await client.get(b + '/jobs/1')).json()['title'] == 'Second role'
        assert (await client.post(a + '/jobs/1/dismiss')).status_code == 200
        assert not (await client.get(b + '/jobs/1')).json()['dismissed']
        assert (await client.get('/api/jobs/1')).status_code == 409
        assert (await client.get('/api/profile')).status_code == 409
    async with installation(tmp_path) as (_, client):
        assert (await client.get(a + '/profile')).json()['full_name'] == 'First person'
        assert (await client.get(b + '/profile')).json()['full_name'] == 'Second person'


async def test_background_job_remains_owned_during_other_profile_requests(tmp_path):
    async with installation(tmp_path) as (app, client):
        a, b = await add_candidate(client, 'First'), await add_candidate(client, 'Second')
        first = await app.state.get_child(a.rsplit('/', 1)[1])
        second = await app.state.get_child(b.rsplit('/', 1)[1])
        entered, release = asyncio.Event(), asyncio.Event()

        async def score(description):
            entered.set()
            await release.wait()
            return {'score': 42, 'reasons': ['Owned'], 'concerns': [], 'keywords': []}

        first.state.matcher = type('Matcher', (), {'score_job': staticmethod(score)})()
        payload = {'title': 'Example', 'company': 'Example', 'description': 'Example job',
                   'url': 'https://example.invalid/1'}
        await client.post(a + '/jobs/save-external', json=payload)
        await entered.wait()
        await client.post(b + '/jobs/save-external', json=payload)
        assert (await client.get('/api/runtime/progress')).json()['active']
        release.set()
        runtime = app.state.candidate_runtimes._runtimes[first.state.candidate_id]
        await asyncio.gather(*runtime._tasks)
        assert (await first.state.db.get_score(1))['match_score'] == 42
        assert await second.state.db.get_score(1) is None
        assert first.state.browser_pool is not second.state.browser_pool


async def test_pairing_unknown_candidates_and_origins_fail_closed(tmp_path):
    async with installation(tmp_path) as (app, client):
        a, b = await add_candidate(client, 'First'), await add_candidate(client, 'Second')
        token = (await client.post(a + '/pairing')).json()['token']
        headers = {'Origin': 'chrome-extension://example', 'X-CareerPulse-Pairing': token}
        assert (await client.get(a + '/profile', headers=headers)).status_code == 200
        assert (await client.get(b + '/profile', headers=headers)).status_code == 403
        assert (await client.get(a + '/profile', headers={'Origin': 'chrome-extension://example'})).status_code == 403
        assert (await client.post(b + '/profile', json={'full_name': 'bad'}, headers={'Origin': 'https://evil.invalid'})).status_code == 403
        assert (await client.get('/api/candidates/not-an-id/profile')).status_code == 404
        assert (await client.post(b + '/pairing', headers=headers)).status_code == 403


async def test_candidate_uploads_downloads_and_calendar_tokens(tmp_path):
    async with installation(tmp_path) as (app, client):
        a, b = await add_candidate(client, 'First'), await add_candidate(client, 'Second')
        for base, text in [(a, b'First candidate resume'), (b, b'Second candidate resume')]:
            result = await client.post(base + '/resume/upload', files={'file': ('resume.txt', text, 'text/plain')})
            assert result.status_code == 200, result.text
        assert 'First candidate' in (await client.get(a + '/search-config')).json()['resume_text']
        assert 'Second candidate' in (await client.get(b + '/search-config')).json()['resume_text']
        token = (await client.get(a + '/calendar/token')).json()['token']
        assert (await client.get(a + '/calendar.ics', params={'token': token})).status_code == 200
        assert (await client.get(b + '/calendar.ics', params={'token': token})).status_code == 401
        assert (await client.get(a + '/export/csv')).status_code == 200
        assert (await client.get(a + '/jobs/99/resume.pdf')).status_code == 404


async def test_scheduler_starts_for_all_candidates_without_ui(tmp_path):
    registry = CandidateRegistry(tmp_path)
    a, b = await registry.create('A'), await registry.create('B')
    app = create_app(data_root=str(tmp_path))
    async with app.router.lifespan_context(app):
        first = await app.state.get_child(a.candidate_id)
        second = await app.state.get_child(b.candidate_id)
        assert first.state.scheduler.running and second.state.scheduler.running
        assert first.state.scheduler is not second.state.scheduler
        assert len(first.state.scheduler.get_jobs()) == 8
        assert first.state.ai_client is None and second.state.ai_client is None
        # Execute the actual scheduled callback; its work must use the owner DB.
        first.state.score_unscored = AsyncMock()
        await first.state.scheduler.get_job('scoring_cycle').func()
        first.state.score_unscored.assert_awaited_once_with(first.state.bg_db)


async def test_profile_pages_and_empty_profile_validation(tmp_path):
    async with installation(tmp_path) as (_, client):
        assert (await client.get('/')).status_code == 200
        assert (await client.post('/api/candidates', json={'display_name': ' '})).status_code == 400
        base = await add_candidate(client, '<script>Example</script>')
        page = await client.get('/profiles/' + base.rsplit('/', 1)[1] + '/')
        assert page.status_code == 200
        assert 'profile-scope.js' in page.text
        assert 'plausible' not in page.text


async def test_migration_cutover_preserves_data_and_rollback_copy(tmp_path):
    from app.database import Database
    from app.candidates import backup_database
    from app.legacy_migration import migrate_legacy_copy, restore_migration_copy
    import sqlite3
    source = tmp_path / 'legacy.db'
    db = Database(str(source))
    await db.init()
    await db.save_user_profile(full_name='Preserved person')
    await db.save_ai_settings('ollama', '', 'synthetic-model', 'http://localhost:11434')
    await db.save_search_config('Preserved resume', ['engineer'], ['Engineer'], ['Python'])
    await db.close()
    snapshot = backup_database(source, tmp_path / 'snapshot.db')
    registry = CandidateRegistry(tmp_path / 'installation')
    record = migrate_legacy_copy(registry, snapshot, 'Imported')
    base = '/api/candidates/' + record.candidate_id
    async with installation(registry.root) as (_, client):
        assert (await client.get(base + '/profile')).json()['full_name'] == 'Preserved person'
        assert (await client.get(base + '/resumes')).json()['resumes']
        fresh = await add_candidate(client, 'Fresh')
        assert not (await client.get(fresh + '/profile')).json().get('full_name')
        assert not (await client.get(fresh + '/ai-settings')).json().get('provider')
        await client.post(base + '/profile', json={'full_name': 'Updated in candidate'})
    restore = restore_migration_copy(record.directory, tmp_path / 'restored')
    with sqlite3.connect(source) as conn:
        assert conn.execute('SELECT full_name FROM user_profile').fetchone()[0] == 'Preserved person'
    assert restore.exists()


async def test_installation_lock_prevents_duplicate_schedulers(tmp_path):
    async with installation(tmp_path):
        with pytest.raises(RuntimeError, match='already running'):
            async with installation(tmp_path):
                pass
    async with installation(tmp_path):
        pass


async def test_missing_storage_never_creates_an_empty_profile(tmp_path):
    registry = CandidateRegistry(tmp_path)
    record = await registry.create('Missing')
    record.db_path.unlink()
    with pytest.raises(FileNotFoundError):
        async with installation(tmp_path):
            pass
    assert not record.db_path.exists()


async def test_candidate_does_not_inherit_environment_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv('JOBFINDER_ANTHROPIC_API_KEY', 'not-a-real-key')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'not-a-real-aws-key')
    async with installation(tmp_path) as (app, client):
        base = await add_candidate(client, 'Empty')
        result = await client.post(base + '/ai-settings', json={'provider': 'bedrock'})
        assert result.status_code == 200
        child = await app.state.get_child(base.rsplit('/', 1)[1])
        assert child.state.ai_client is None
        tested = await client.post(base + '/ai-settings/test', json={'provider': 'bedrock'})
        assert not tested.json()['ok']
        assert 'shared AWS credentials are disabled' in tested.json()['error']


async def test_stop_guard_sees_inflight_candidate_request(tmp_path):
    async with installation(tmp_path) as (app, client):
        base = await add_candidate(client, 'Request owner')
        child = await app.state.get_child(base.rsplit('/', 1)[1])
        entered, release = asyncio.Event(), asyncio.Event()
        original = child.state.db.save_user_profile

        async def slow_save(**fields):
            entered.set()
            await release.wait()
            await original(**fields)

        child.state.db.save_user_profile = slow_save
        writing = asyncio.create_task(client.post(base + '/profile', json={'full_name': 'Saved'}))
        await entered.wait()
        progress = (await client.get('/api/runtime/progress')).json()
        assert progress['active'] and progress['candidates'][0]['requests_active'] == 1
        release.set()
        assert (await writing).status_code == 200
        assert not (await client.get('/api/runtime/progress')).json()['active']


async def test_scheduled_scrape_respects_source_due_times(tmp_path, monkeypatch):
    from app.routers import scraping
    registry = CandidateRegistry(tmp_path)
    record = await registry.create('Scheduled')
    app = create_app(data_root=str(tmp_path))
    async with app.router.lifespan_context(app):
        child = await app.state.get_child(record.candidate_id)
        await child.state.db.save_search_config('Resume', ['engineer'], ['Engineer'], ['Python'])
        launch = AsyncMock()
        monkeypatch.setattr(scraping, 'start_scrape', launch)
        # Configure a fresh scheduler so its import captures the stubbed boundary.
        child.state.scheduler.shutdown(wait=False)
        from app.multi_profile import configure_scheduler
        configure_scheduler(app.state.candidate_runtimes._runtimes[record.candidate_id], child)
        await child.state.scheduler.get_job('scrape_cycle').func()
        launch.assert_awaited_once_with(child, force=False)
