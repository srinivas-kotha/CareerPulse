"""Deterministic candidate-policy checks kept separate from AI fit scoring."""

import re


POLICY_VERSION = "srini-2026-09-09-v1"
FULL_TIME_MIN = 130_000
FULL_TIME_RELOCATION_MIN = 150_000
W2_HOURLY_MIN = 75
C2C_HOURLY_MIN = 70
HOURLY_RELOCATION_MIN = 80
MIN_PROJECT_MONTHS = 12

EXCLUDED_ROLE_TERMS = (
    "sales engineer", "sales engineering", "management", "director",
    "data scientist", "data analyst", "data engineer", "analytics engineer",
    "machine learning", "ml engineer", "marketing", "recruiter",
)


def _text(job: dict) -> str:
    return " ".join(str(job.get(key) or "") for key in ("title", "description")).lower()


def _salary(job: dict) -> tuple[int | None, int | None]:
    return job.get("salary_min"), job.get("salary_max")


def _sponsorship_state(description: str) -> str:
    text = description.lower()
    refusal = (
        r"no visa sponsorship", r"without sponsorship", r"sponsorship is not",
        r"cannot sponsor", r"can't sponsor", r"will not sponsor",
        r"do not sponsor", r"does not sponsor", r"unable to sponsor",
        r"us citizens only", r"must be a us citizen", r"permanent residents only",
    )
    positive = (
        r"will sponsor", r"visa sponsorship available", r"sponsor h-?1b",
        r"h-?1b sponsorship", r"sponsorship provided",
    )
    if any(re.search(pattern, text) for pattern in refusal):
        return "refused"
    if any(re.search(pattern, text) for pattern in positive):
        return "confirmed"
    return "unknown"


def evaluate_job(job: dict, profile: dict | None = None, company: dict | None = None) -> dict:
    """Return eligibility state and human-readable reasons for a job.

    Unknown compensation, sponsorship, duration, and company history are review
    states. Historical H-1B sponsorship can support review but never proves this
    specific requisition sponsors.
    """
    profile = profile or {}
    override = str(job.get("eligibility_override_status") or "").strip().lower()
    if override in {"eligible", "excluded", "verification_required"}:
        return {"status": override, "reasons": ["Manually reviewed by candidate"],
                "evidence": [], "policy_version": POLICY_VERSION}
    text = _text(job)
    reasons: list[str] = []
    evidence: list[str] = []
    excluded = any(term in text for term in EXCLUDED_ROLE_TERMS)
    if excluded:
        reasons.append("Role is excluded by candidate policy")

    requires_sponsorship = str(profile.get("requires_sponsorship", "")).lower() in {"yes", "true", "1"}
    sponsorship = _sponsorship_state(str(job.get("description") or ""))
    if requires_sponsorship and sponsorship == "refused":
        return {"status": "excluded", "reasons": reasons + ["Employer explicitly refuses required H-1B sponsorship"],
                "evidence": evidence, "policy_version": POLICY_VERSION}
    if requires_sponsorship:
        if sponsorship == "confirmed":
            evidence.append("Job description states sponsorship is available")
        else:
            reasons.append("Job-specific H-1B sponsorship is not confirmed")
            if company and company.get("h1b_sponsorship_status") == "reported":
                evidence.append("Company has historical H-1B sponsorship records; this does not prove this role sponsors")
            else:
                reasons.append("No verified historical H-1B company evidence is stored")

    minimum = FULL_TIME_MIN
    min_type = "full-time base salary"
    title = str(job.get("title") or "").lower()
    description = str(job.get("description") or "").lower()
    hourly = job.get("compensation_period") == "hourly" or bool(re.search(r"\$?\s*\d[\d,]*(?:\.\d+)?\s*/\s*(?:hr|hour)|hourly|per hour", description))
    c2c = str(job.get("compensation_type") or "").lower() == "c2c" or "c2c" in text or "corp to corp" in text
    if hourly:
        minimum = C2C_HOURLY_MIN if c2c else W2_HOURLY_MIN
        min_type = "C2C hourly rate" if c2c else "W2 hourly rate"

    salary_min, salary_max = _salary(job)
    if salary_min is None and salary_max is None:
        reasons.append(f"{min_type} is not listed")
    elif (salary_max or salary_min or 0) < minimum:
        reasons.append(f"Listed compensation is below the {min_type} minimum of {minimum}")
        return {"status": "excluded", "reasons": reasons, "evidence": evidence, "policy_version": POLICY_VERSION}
    elif (salary_min or 0) < minimum:
        reasons.append(f"Compensation range overlaps the {min_type} minimum")

    if not hourly and ("relocat" in text or "onsite" in text or "on-site" in text) and (salary_max or salary_min or 0) < FULL_TIME_RELOCATION_MIN:
        reasons.append("Relocation/on-site compensation is below the $150,000 relocation threshold")
    if hourly and "relocat" in text and (salary_max or salary_min or 0) < HOURLY_RELOCATION_MIN:
        reasons.append("Hourly relocation compensation is below the $80/hr relocation threshold")

    if "12 month" not in text and "12-month" not in text and "one year" not in text and "long term" not in text and "long-term" not in text:
        reasons.append("W2 project duration of at least 12 months is not confirmed")

    if excluded:
        status = "excluded"
    elif reasons:
        status = "verification_required"
    else:
        status = "eligible"
    return {"status": status, "reasons": reasons, "evidence": evidence, "policy_version": POLICY_VERSION}