import asyncio
from unittest.mock import AsyncMock

from tests.test_multi_profile import installation, add_candidate


async def seed(client, base, minimum):
    response = await client.post(base + '/profile', json={
        'full_name': base.rsplit('/', 1)[1], 'requires_sponsorship': 'no',
        'eligibility_policy': {'confirmed': True, 'currency': 'USD', 'annual_min': minimum}})
    assert response.status_code == 200, response.text
    response = await client.post(base + '/jobs/save-external', json={
        'title': 'Synthetic Engineer', 'company': 'Example',
        'url': 'https://example.invalid/same-requisition', 'description': 'Full-time role',
        'salary_min': 110000, 'salary_max': 110000})
    assert response.status_code == 200, response.text
    return response.json()['job_id']


async def test_different_rules_same_job_review_and_restart(tmp_path):
    async with installation(tmp_path) as (app, client):
        a, b = await add_candidate(client, 'First'), await add_candidate(client, 'Second')
        ja, jb = await seed(client, a, 100000), await seed(client, b, 120000)
        assert ja == jb
        assert (await client.get(a + f'/jobs/{ja}/eligibility')).json()['status'] == 'eligible'
        assert (await client.get(b + f'/jobs/{jb}/eligibility')).json()['status'] == 'excluded'
        assert (await client.post(b + f'/jobs/{jb}/eligibility/review', json={
            'status': 'eligible', 'note': 'This must not bypass a hard exclusion.'})).status_code == 409
        queued = await client.post(a + '/queue/add', json={'job_id': ja})
        assert queued.status_code == 200, queued.text
        assert (await client.post(b + '/queue/add', json={'job_id': jb})).status_code == 409
        assert (await client.get(b + '/queue')).json()['queue'] == []
        policy_a = (await client.get(a + '/profile')).json()['eligibility_policy_version']
        await client.post(b + '/profile', json={'eligibility_policy': {'confirmed': True}})
        assert (await client.get(a + '/profile')).json()['eligibility_policy_version'] == policy_a
    async with installation(tmp_path) as (_, client):
        assert (await client.get(a + '/profile')).json()['eligibility_policy']['annual_min'] == 100000
        assert (await client.get(b + '/profile')).json()['eligibility_policy']['annual_min'] is None
        assert len((await client.get(a + '/queue')).json()['queue']) == 1
        assert (await client.get(b + '/queue')).json()['queue'] == []


async def test_reviews_expire_and_queued_work_rechecks_policy(tmp_path):
    async with installation(tmp_path) as (app, client):
        a = await add_candidate(client, 'First')
        j = await seed(client, a, 100000)
        child = await app.state.get_child(a.rsplit('/', 1)[1])
        await child.state.db.db.execute("UPDATE jobs SET salary_min = NULL, salary_max = NULL WHERE id = ?", (j,))
        await child.state.db.db.commit()
        review = a + f'/jobs/{j}/eligibility/review'
        assert (await client.post(review, json={'status': 'eligible'})).status_code == 422
        assert (await client.post(review, json={'status': 'eligible', 'note': 'Employer confirmed the offered amount meets policy.'})).status_code == 200
        q = (await client.post(a + '/queue/add', json={'job_id': j})).json()['queue_id']
        assert (await client.post(a + f'/queue/{q}/approve')).status_code == 200
        await client.post(a + '/profile', json={'eligibility_policy': {
            'confirmed': True, 'currency': 'USD', 'annual_min': 120000}})
        assert (await client.get(a + f'/jobs/{j}/eligibility')).json()['status'] == 'verification_required'
        assert (await client.post(a + f'/queue/{q}/approve')).status_code == 409
        assert (await client.get(a + '/queue?status=approved')).json()['queue'] == []
        assert (await client.post(a + f'/queue/{q}/fill-status', json={'status': 'filling'})).status_code == 409
        child.state.tailor = type('Tailor', (), {'prepare': AsyncMock()})()
        await child.state.db.update_queue_status(q, 'queued')
        result = await client.post(a + '/queue/prepare-all')
        assert result.json()['failed'] == 1
        child.state.tailor.prepare.assert_not_awaited()


async def test_materials_settings_notifications_and_concurrent_work_stay_owned(tmp_path):
    async with installation(tmp_path) as (app, client):
        a, b = await add_candidate(client, 'First'), await add_candidate(client, 'Second')
        children = [await app.state.get_child(base.rsplit('/', 1)[1]) for base in (a, b)]
        for index, (base, child) in enumerate(zip((a, b), children)):
            await seed(client, base, 100000)
            assert (await client.post(base + '/resume/upload', files={'file': (
                'resume.txt', f'Synthetic candidate {index} resume text'.encode(), 'text/plain')})).status_code == 200
            assert (await client.post(base + '/search-config/terms', json={'search_terms': [f'role {index}']})).status_code == 200
            await child.state.db.insert_notification(1, 'test', f'Only {index}', 'Synthetic')
            child.state.tailor = type('Tailor', (), {'prepare': AsyncMock(return_value={
                'tailored_resume': f'Synthetic material {index}', 'cover_letter': f'Letter {index}'})})()
            assert (await client.post(base + '/queue/add', json={'job_id': 1})).status_code == 200
        results = await asyncio.gather(*(client.post(base + '/queue/prepare-all') for base in (a, b)))
        assert [r.json()['prepared'] for r in results] == [1, 1]
        for index, (base, child) in enumerate(zip((a, b), children)):
            application = await child.state.db.get_application(1)
            assert application['tailored_resume'] == f'Synthetic material {index}'
            assert (await child.state.db.get_notifications())[0]['title'] == f'Only {index}'
            config = (await client.get(base + '/search-config')).json()
            assert config['search_terms'] == [f'role {index}']
            assert f'candidate {index}' in config['resume_text']
        children[0].state.scoring_progress = {'active': True, 'scored': 3}
        assert children[1].state.scoring_progress is None
        assert children[0].state.notification_subscribers is not children[1].state.notification_subscribers
        # Clearing one candidate does not affect the other's prepared application.
        await children[0].state.db.clear_jobs()
        assert await children[0].state.db.get_job(1) is None
        assert (await children[1].state.db.get_application(1))['tailored_resume'] == 'Synthetic material 1'


async def test_invalid_policy_rejected_without_changing_other_fields(tmp_path):
    async with installation(tmp_path) as (_, client):
        a = await add_candidate(client, 'First')
        await client.post(a + '/profile', json={'full_name': 'Original'})
        result = await client.post(a + '/profile', json={'full_name': 'Changed', 'eligibility_policy': {'annual_min': -5}})
        assert result.status_code == 422
        assert (await client.get(a + '/profile')).json()['full_name'] == 'Original'


async def test_resume_output_and_form_learning_cannot_set_policy(tmp_path):
    async with installation(tmp_path) as (app, client):
        a = await add_candidate(client, 'First')
        child = await app.state.get_child(a.rsplit('/', 1)[1])
        await child.state.save_parsed_profile(child.state.db, {'personal': {
            'first_name': 'Example', 'last_name': 'Person',
            'requires_sponsorship': 'no', 'eligibility_policy': {'confirmed': True}}})
        profile = (await client.get(a + '/profile')).json()
        assert profile['full_name'] == 'Example Person'
        assert not profile.get('requires_sponsorship')
        assert not profile['eligibility_policy'].get('confirmed')
        await client.post(a + '/profile/learn', json={'new_data': {
            'phone': '555-0100', 'eligibility_policy': {'confirmed': True}}})
        profile = (await client.get(a + '/profile')).json()
        assert profile['phone'] == '555-0100'
        assert not profile['eligibility_policy'].get('confirmed')
