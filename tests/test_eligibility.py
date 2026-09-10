from app.eligibility import evaluate_job


PROFILE = {"requires_sponsorship": "yes"}


def job(**overrides):
    result = {
        "title": "Platform Engineer",
        "description": "Full-time 12-month long-term project with H-1B sponsorship.",
        "salary_min": 130000,
        "salary_max": 160000,
    }
    result.update(overrides)
    return result


def test_policy_accepts_verified_full_time_job():
    result = evaluate_job(job(), PROFILE)
    assert result["status"] == "eligible"


def test_unknown_salary_requires_verification():
    result = evaluate_job(job(salary_min=None, salary_max=None), PROFILE)
    assert result["status"] == "verification_required"
    assert any("not listed" in reason for reason in result["reasons"])


def test_explicit_sponsorship_refusal_excludes_job():
    result = evaluate_job(job(description="Full-time 12-month project. No visa sponsorship."), PROFILE)
    assert result["status"] == "excluded"


def test_company_history_is_evidence_not_role_proof():
    result = evaluate_job(
        job(description="Full-time 12-month long-term project. Sponsorship policy not stated."),
        PROFILE,
        {"h1b_sponsorship_status": "reported"},
    )
    assert result["status"] == "verification_required"
    assert any("historical H-1B" in evidence for evidence in result["evidence"])


def test_excluded_role_cannot_enter_application_policy():
    result = evaluate_job(job(title="Sales Engineering Manager"), PROFILE)
    assert result["status"] == "excluded"


def test_hourly_thresholds_are_arrangement_specific():
    assert evaluate_job(job(description="W2 hourly 12-month project with H-1B sponsorship.", salary_min=75, salary_max=90), PROFILE)["status"] == "eligible"
    assert evaluate_job(job(description="C2C hourly 12-month project with H-1B sponsorship.", salary_min=69, salary_max=90), PROFILE)["status"] == "verification_required"
    assert evaluate_job(job(description="C2C hourly 12-month project with H-1B sponsorship.", salary_min=60, salary_max=69), PROFILE)["status"] == "excluded"
