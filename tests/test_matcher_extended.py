import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.matcher import JobMatcher


SAMPLE_RESUME = "Senior Engineer, 10 years, AWS, Python, K8s"


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.provider = "test"
    client.base_url = "http://localhost"
    client.chat = AsyncMock()
    return client


def _make_response(score=75, reasons=None, concerns=None, keywords=None):
    return json.dumps({
        "score": score,
        "reasons": reasons or ["Good match"],
        "concerns": concerns or [],
        "keywords": keywords or ["python"],
    })


async def test_score_job_with_resume_override(mock_client):
    mock_client.chat = AsyncMock(return_value=_make_response(90))
    matcher = JobMatcher(mock_client, SAMPLE_RESUME)
    result = await matcher.score_job("DevOps role", resume_text="Custom resume text")
    assert result["score"] == 90
    prompt = mock_client.chat.call_args[0][0]
    assert "Custom resume text" in prompt
    assert SAMPLE_RESUME not in prompt


async def test_score_job_connection_error(mock_client):
    mock_client.chat = AsyncMock(side_effect=Exception("Connection refused"))
    matcher = JobMatcher(mock_client, SAMPLE_RESUME)
    result = await matcher.score_job("Some job")
    assert result is None  # Transient errors return None


async def test_score_job_circuit_breaker_error(mock_client):
    mock_client.chat = AsyncMock(side_effect=Exception("circuit breaker open"))
    matcher = JobMatcher(mock_client, SAMPLE_RESUME)
    result = await matcher.score_job("Some job")
    assert result is None  # Transient errors return None


async def test_score_job_empty_description(mock_client):
    mock_client.chat = AsyncMock(return_value=_make_response(10))
    matcher = JobMatcher(mock_client, SAMPLE_RESUME)
    result = await matcher.score_job("")
    assert "score" in result


async def test_score_batch_isolates_job_prompts(mock_client):
    mock_client.chat.side_effect = [_make_response(80), _make_response(60)]
    matcher = JobMatcher(mock_client, SAMPLE_RESUME)
    results = await matcher.score_batch([{"id": 10, "description": "job A"}, {"id": 20, "description": "job B"}])
    assert [(r["job_id"], r["score"]) for r in results] == [(10, 80), (20, 60)]
    assert "job B" not in mock_client.chat.call_args_list[0].args[0]
    assert "job A" not in mock_client.chat.call_args_list[1].args[0]


async def test_missing_result_never_shifts_job_identity(mock_client):
    mock_client.chat.side_effect = [ValueError("AI failed"), _make_response(60)]
    matcher = JobMatcher(mock_client, SAMPLE_RESUME)
    results = await matcher.score_batch([{"id": 10, "description": "job A"}, {"id": 20, "description": "job B"}])
    assert [(r["job_id"], r["score"]) for r in results] == [(20, 60)]


async def test_array_response_is_not_assigned_to_any_job(mock_client):
    mock_client.chat.return_value = json.dumps([{"job_index": 1, "score": 92}])
    matcher = JobMatcher(mock_client, SAMPLE_RESUME)
    assert await matcher.score_batch([{"id": 10, "description": "job A"}]) == []


async def test_batch_score_individual_with_delay(mock_client):
    mock_client.chat = AsyncMock(return_value=_make_response(70))
    matcher = JobMatcher(mock_client, SAMPLE_RESUME)
    jobs = [{"id": 1, "description": "a"}, {"id": 2, "description": "b"}]
    results = await matcher.batch_score(jobs, delay=0)
    assert len(results) == 2
    assert mock_client.chat.call_count == 2
