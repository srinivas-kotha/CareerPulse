import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.matcher import JobMatcher


@pytest.mark.parametrize("description", [
    "Applicants must be authorized to work for any employer in the U.S. without sponsorship.",
    "We are unable to provide sponsorship for work visas of any kind at the time of hire, or at any point during employment.",
    "Visa sponsorship is not available.",
    "We do not offer visa sponsorship.",
    "We cannot sponsor work visas.",
    "No visa sponsorship.",
    "<p>We will not <b>provide</b> employment visa sponsorship.</p>",
])
async def test_sponsorship_conflict_bypasses_ai(description):
    client = MagicMock(chat=AsyncMock())
    matcher = JobMatcher(client, "Azure developer", candidate_profile={"requires_sponsorship": "yes"}, require_evidence=True)
    result = await matcher.score_job(description)
    assert result["score"] == 0
    assert "requires sponsorship" in result["concerns"][0]
    client.chat.assert_not_called()


@pytest.mark.parametrize("profile,description", [
    ({"requires_sponsorship": "no"}, "We cannot sponsor work visas."),
    ({}, "No visa sponsorship."),
    ({"requires_sponsorship": "yes"}, "Visa sponsorship is available."),
    ({"requires_sponsorship": "yes"}, "We welcome applicants who require sponsorship."),
    ({"requires_sponsorship": "yes"}, "Senior Azure developer."),
])
async def test_no_conflict_is_not_rejected(profile, description):
    client = MagicMock(chat=AsyncMock(return_value=json.dumps({"score": 60, "role_match": True, "reasons": [], "concerns": [], "keywords": []})))
    matcher = JobMatcher(client, "Azure developer", candidate_profile=profile)
    assert (await matcher.score_job(description))["score"] == 60
    client.chat.assert_awaited_once()


async def test_role_mismatch_cap_is_enforced_in_code():
    client = MagicMock(chat=AsyncMock(return_value=json.dumps({"score": 92, "role_match": False, "reasons": [], "concerns": [], "keywords": []})))
    result = await JobMatcher(client, "Azure developer").score_job("Technical alliances")
    assert result["score"] == 50


def response():
    return {"score": 92, "role_match": True, "reasons": [], "concerns": [], "keywords": [],
            "category_scores": {"role": 30, "skills": 25, "experience": 18, "logistics": 17},
            "evidence": [{"job": "Build .NET APIs", "resume": "Built .NET APIs"},
                         {"job": "Azure development", "resume": "Azure development"}]}


async def test_breakdown_is_calculated_and_evidence_saved():
    client = MagicMock(chat=AsyncMock(return_value=json.dumps(response())))
    result = await JobMatcher(client, "Built .NET APIs. Azure development.", require_evidence=True).score_job("Build .NET APIs. Azure development.")
    assert result["score"] == 90
    assert "role 30/30" in result["reasons"][0]
    assert any('Resume: "Built .NET APIs"' in r for r in result["reasons"])


@pytest.mark.parametrize("fault", ["wrong_job", "wrong_resume", "no_evidence", "no_breakdown"])
async def test_ungrounded_high_score_is_left_unscored(fault):
    data = response()
    if fault == "wrong_job":
        data["evidence"][0]["job"] = "B2B growth marketing"
    elif fault == "wrong_resume":
        data["evidence"][0]["resume"] = "AWS technical alliances"
    elif fault == "no_evidence":
        data["evidence"] = []
    else:
        data.pop("category_scores")
    client = MagicMock(chat=AsyncMock(return_value=json.dumps(data)))
    result = await JobMatcher(client, "Built .NET APIs. Azure development.", require_evidence=True).score_job("Build .NET APIs. Azure development.")
    assert result is None


async def test_invalid_evidence_gets_one_grounded_correction():
    bad = response()
    bad["evidence"][0]["resume"] = "Invented experience"
    client = MagicMock(chat=AsyncMock(side_effect=[json.dumps(bad), json.dumps(response())]))
    result = await JobMatcher(client, "Built .NET APIs. Azure development.", require_evidence=True).score_job("Build .NET APIs. Azure development.")
    assert result["score"] == 90
    assert client.chat.await_count == 2
    assert "contiguous verbatim excerpts" in client.chat.call_args.args[0]
    assert all("Invented experience" not in reason for reason in result["reasons"])


async def test_invalid_evidence_retry_is_bounded():
    bad = response()
    bad["evidence"][0]["resume"] = "Invented experience"
    client = MagicMock(chat=AsyncMock(return_value=json.dumps(bad)))
    result = await JobMatcher(client, "Built .NET APIs. Azure development.", require_evidence=True).score_job("Build .NET APIs. Azure development.")
    assert result is None
    assert client.chat.await_count == 2
