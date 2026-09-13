import pytest
from app.eligibility import evaluate_job, normalize_policy, review_fingerprint


def profile(**rules):
    return {"requires_sponsorship": "yes", "eligibility_policy": normalize_policy({
        "confirmed": True, "currency": "USD", "annual_min": 100000,
        "w2_hourly_min": 50, "c2c_hourly_min": 60, **rules})}


def job(**values):
    return {"id": 1, "title": "Platform Engineer", "location": "Remote",
            "description": "Full-time role with visa sponsorship available.",
            "compensation_period": "annual", "salary_currency": "USD",
            "salary_min": 110000, "salary_max": 140000, **values}


@pytest.mark.parametrize("changes,expected", [
    ({}, "eligible"),
    ({"salary_min": None, "salary_max": None}, "verification_required"),
    ({"salary_min": 80000, "salary_max": 90000}, "excluded"),
    ({"salary_min": 90000, "salary_max": 110000}, "verification_required"),
    ({"salary_min": None}, "verification_required"),
    ({"salary_currency": "CAD"}, "verification_required"),
    ({"salary_currency": ""}, "verification_required"),
    ({"compensation_period": "monthly"}, "verification_required"),
    ({"salary_min": 150000}, "verification_required"),
    ({"description": "No visa sponsorship"}, "excluded"),
    ({"description": "Sponsorship not stated"}, "verification_required"),
    ({"description": "Full-time visa sponsorship available; work with data scientists"}, "eligible"),
])
def test_rules(changes, expected):
    assert evaluate_job(job(**changes), profile())["status"] == expected


def test_fresh_profiles_have_no_personal_rules_and_require_confirmation():
    p = normalize_policy({})
    assert p["annual_min"] is None and p["excluded_titles"] == []
    assert evaluate_job(job(), {})["status"] == "verification_required"
    assert evaluate_job(job(), {"eligibility_policy": {"confirmed": True}})["status"] == "verification_required"
    assert evaluate_job(job(), {"requires_sponsorship": "no", "eligibility_policy": {"confirmed": True}})["status"] == "eligible"


def test_title_exclusion_does_not_match_incidental_description():
    p = profile(excluded_titles=["data scientist"])
    assert evaluate_job(job(description="Visa sponsorship available. Work alongside a data scientist."), p)["status"] == "eligible"
    assert evaluate_job(job(title="Senior Data Scientist"), p)["status"] == "excluded"


def test_contract_duration_is_not_applied_to_full_time():
    p = profile(min_contract_months=9)
    assert evaluate_job(job(), p)["status"] == "eligible"
    assert evaluate_job(job(compensation_type="w2", description="6 month contract, visa sponsorship available"), p)["status"] == "excluded"
    assert evaluate_job(job(compensation_type="w2", description="Long term contract, visa sponsorship available"), p)["status"] == "verification_required"


def test_hourly_rules_are_separate():
    hourly = job(compensation_period="hourly", compensation_type="w2", salary_min=55, salary_max=55)
    assert evaluate_job(hourly, profile())["status"] == "eligible"
    assert evaluate_job({**hourly, "compensation_type": "c2c"}, profile())["status"] == "excluded"
    assert evaluate_job({**hourly, "compensation_type": ""}, profile())["status"] == "verification_required"


def test_remote_headquarters_and_relocation():
    p = profile(excluded_locations=["California"], allowed_work_types=["remote"])
    assert evaluate_job(job(description="Headquarters in California. Visa sponsorship available."), p)["status"] == "eligible"
    assert evaluate_job(job(location="Remote - California"), p)["status"] == "excluded"
    assert evaluate_job(job(location="Hybrid - Example City"), p)["status"] == "excluded"
    assert evaluate_job(job(description="Remote within the US. Visa sponsorship available."), p)["status"] == "verification_required"
    assert evaluate_job(job(description="Must relocate. Visa sponsorship available."), {**p, "willing_to_relocate": "no"})["status"] == "excluded"


def test_review_is_bound_to_facts_and_cannot_override_exclusion():
    p = profile()
    j = job(salary_min=None, salary_max=None)
    j.update(eligibility_override_status="eligible", eligibility_review_note="Verified employer offer meets the minimum.",
             eligibility_review_fingerprint=review_fingerprint(j, p))
    assert evaluate_job(j, p)["status"] == "eligible"
    assert evaluate_job(j, profile(annual_min=120000))["status"] == "verification_required"
    changed = {**j, "salary_min": 100, "salary_max": 100}
    changed["eligibility_review_fingerprint"] = review_fingerprint(changed, p)
    assert evaluate_job(changed, p)["status"] == "excluded"
    assert evaluate_job({**j, "description": "Changed listing"}, p)["status"] == "verification_required"


@pytest.mark.parametrize("policy", [{"annual_min": -1}, {"annual_min": float("nan")},
    {"confirmed": "yes"}, {"currency": "dollars"}, {"excluded_titles": [""]},
    {"allowed_work_types": ["anything"]}, {"candidate_id": "other"}])
def test_invalid_policies_fail(policy):
    with pytest.raises(ValueError):
        normalize_policy(policy)
