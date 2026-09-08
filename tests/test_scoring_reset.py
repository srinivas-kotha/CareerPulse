async def test_reset_preserves_job_application_and_other_notifications(client, app):
    db = app.state.db
    job_id = await db.insert_job(title="Engineer", company="Example", url="https://example.com/job", description="Build APIs", location="US", salary_min=None, salary_max=None, posted_date=None, application_method="url", contact_email=None)
    await db.insert_score(job_id, 92, ["Old reason"], [], [])
    await db.upsert_application(job_id, status="applied")
    await db.insert_notification(job_id, "high_score", "Old score", "92")
    await db.insert_notification(job_id, "reminder", "Follow up", "Reminder")
    response = await client.post("/api/rescore-all")
    assert response.status_code == 200
    assert response.json()["cleared"] == 1
    assert await db.get_score(job_id) is None
    assert await db.get_job(job_id)
    assert (await db.get_application(job_id))["status"] == "applied"
    assert [n["type"] for n in await db.get_notifications()] == ["reminder"]


async def test_reset_refuses_to_race_active_scoring(client, app):
    async with app.state.scoring_lock:
        response = await client.post("/api/rescore-all")
    assert response.status_code == 409
