"""Candidate-owned, deterministic eligibility. No personal policy defaults."""

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EligibilityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirmed: bool = False
    currency: str = ""
    annual_min: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    w2_hourly_min: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    c2c_hourly_min: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    relocation_annual_min: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    relocation_hourly_min: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    min_contract_months: int | None = Field(default=None, ge=1, le=1200)
    excluded_titles: list[str] = Field(default_factory=list, max_length=100)
    excluded_locations: list[str] = Field(default_factory=list, max_length=100)
    allowed_work_types: list[Literal["remote", "hybrid", "onsite"]] = Field(default_factory=list)
    allowed_arrangements: list[Literal["fulltime", "w2", "c2c", "contract"]] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def currency_code(cls, value):
        value = value.strip().upper()
        if value and not re.fullmatch("[A-Z]{3}", value):
            raise ValueError("Use a three-letter currency code")
        return value

    @field_validator("excluded_titles", "excluded_locations")
    @classmethod
    def terms(cls, values):
        if any(not v.strip() or len(v) > 120 for v in values):
            raise ValueError("Use nonempty terms of at most 120 characters")
        return sorted(set(v.strip().lower() for v in values))


def normalize_policy(value):
    return EligibilityPolicy.model_validate(value).model_dump()


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def policy_version(profile):
    return "eligibility-v2:" + _digest({key: profile.get(key) for key in
        ("eligibility_policy", "requires_sponsorship", "willing_to_relocate")})


def review_fingerprint(job, profile):
    # Changed listing facts or candidate policy invalidate an earlier decision.
    return _digest({"policy": policy_version(profile), "job": {key: job.get(key) for key in
        ("id", "title", "company", "url", "description", "location", "salary_min",
         "salary_max", "compensation_period", "compensation_type", "salary_currency",
         "salary_source_text", "is_remote", "work_type", "relocation_required")}})


def _contains(term, text):
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I))


def _sponsorship_state(description):
    refusal = (r"no (?:visa )?sponsorship", r"without sponsorship",
               r"sponsorship (?:is |will be )?not (?:available|provided|offered|supported)", r"(?:cannot|can't|will not|do not|does not|unable to) sponsor",
               r"us citizens only", r"must be a us citizen", r"permanent residents only")
    positive = (r"will sponsor", r"visa sponsorship available", r"sponsor h-?1b",
                r"h-?1b sponsorship", r"sponsorship provided")
    if any(re.search(p, description, re.I) for p in refusal):
        return "refused"
    if any(re.search(p, description, re.I) for p in positive):
        return "confirmed"
    return "unknown"


def evaluate_job(job: dict, profile: dict | None = None, company: dict | None = None) -> dict:
    profile = profile or {}
    policy = normalize_policy(profile.get("eligibility_policy") or {})
    reasons, evidence, exclusions = [], [], []
    title = str(job.get("title") or "").lower()
    description = str(job.get("description") or "").lower()
    location = str(job.get("location") or "").lower()
    text = title + " " + description
    if not policy["confirmed"]:
        reasons.append("Confirm this profile's eligibility rules in Settings > Job Search")
    for term in policy["excluded_titles"]:
        if _contains(term, title):
            exclusions.append("Job title matches excluded role: " + term)
    if policy["excluded_locations"]:
        if not location:
            reasons.append("Work location is not established")
        elif any(_contains(term, location) for term in policy["excluded_locations"]):
            exclusions.append("Job work location matches an excluded location")
    # Headquarters mentioned in a description are not the job work location.
    work_type = str(job.get("work_type") or "").lower()
    if work_type not in {"remote", "hybrid", "onsite"}:
        if "hybrid" in location:
            work_type = "hybrid"
        elif "remote" in location or job.get("is_remote"):
            work_type = "remote"
        elif "onsite" in location or "on-site" in location:
            work_type = "onsite"
        else:
            work_type = ""
    if policy["allowed_work_types"]:
        if not work_type:
            reasons.append("Remote/hybrid/on-site arrangement needs verification")
        elif work_type not in policy["allowed_work_types"]:
            exclusions.append("Work type is outside this profile's allowed work types")
    if work_type == "remote" and re.search(r"must (?:reside|live)|remote (?:only )?(?:within|in)|residents? of", description):
        reasons.append("Verify the job's remote residence restrictions")
    sponsorship = _sponsorship_state(description)
    sponsorship_need = str(profile.get("requires_sponsorship", "")).lower()
    if sponsorship_need not in {"yes", "true", "1", "no", "false", "0"}:
        reasons.append("This profile's sponsorship requirement is not confirmed")
    if sponsorship_need in {"yes", "true", "1"}:
        if sponsorship == "refused":
            exclusions.append("Employer explicitly refuses required sponsorship")
        elif sponsorship == "unknown":
            reasons.append("Job-specific sponsorship is not confirmed")
            if company and company.get("h1b_sponsorship_status") == "reported":
                evidence.append("Historical sponsorship does not prove this role sponsors")
        else:
            evidence.append("Job description states sponsorship is available")
    period = str(job.get("compensation_period") or "").lower()
    arrangement = str(job.get("compensation_type") or "").lower()
    if arrangement not in {"fulltime", "w2", "c2c", "contract"}:
        if re.search(r"\bc2c\b|corp.to.corp", text):
            arrangement = "c2c"
        elif re.search(r"\bw-?2\b", text):
            arrangement = "w2"
        elif re.search(r"\bcontract\b", text):
            arrangement = "contract"
        elif re.search(r"full[ -]?time", text):
            arrangement = "fulltime"
        else:
            arrangement = ""
    if policy["allowed_arrangements"]:
        if not arrangement:
            reasons.append("Employment arrangement needs verification")
        elif arrangement not in policy["allowed_arrangements"]:
            exclusions.append("Employment arrangement is not allowed by this profile")
    minimum = None
    has_minimum = any(policy[k] is not None for k in ("annual_min", "w2_hourly_min", "c2c_hourly_min"))
    if period in {"annual", "yearly"}:
        minimum = policy["annual_min"]
    elif period == "hourly":
        if arrangement in {"w2", "c2c"}:
            minimum = policy[arrangement + "_hourly_min"]
        elif policy["w2_hourly_min"] is not None or policy["c2c_hourly_min"] is not None:
            reasons.append("Hourly W2/C2C arrangement needs verification")
    elif has_minimum:
        reasons.append("Compensation period needs verification")
    relocation = job.get("relocation_required") is True or bool(re.search(r"relocation (?:is )?required|must relocate", description))
    if relocation:
        if str(profile.get("willing_to_relocate", "")).lower() == "no":
            exclusions.append("Job requires relocation and this profile does not permit it")
        elif str(profile.get("willing_to_relocate", "")).lower() != "yes":
            reasons.append("Required relocation needs candidate confirmation")
        relocation_min = policy["relocation_hourly_min" if period == "hourly" else "relocation_annual_min"]
        if relocation_min is not None and period not in {"hourly", "annual", "yearly"}:
            reasons.append("Compensation period must be verified for the relocation minimum")
        elif relocation_min is not None:
            minimum = max(minimum or 0, relocation_min)
    if minimum is not None:
        currency = str(job.get("salary_currency") or "").upper()
        low, high = job.get("salary_min"), job.get("salary_max")
        if not currency or not policy["currency"] or currency != policy["currency"]:
            reasons.append("Compensation currency is missing or differs from the policy currency")
        elif low is None and high is None:
            reasons.append("Compensation is not listed")
        elif (low is not None and low < 0) or (high is not None and high < 0) or (low is not None and high is not None and low > high):
            reasons.append("Compensation range is invalid")
        elif high is not None and high < minimum:
            exclusions.append("Listed compensation is below this profile's minimum")
        elif low is None or low < minimum:
            reasons.append("Compensation is below or overlaps the minimum; verify the offered amount")
        else:
            evidence.append("Listed compensation meets this profile's minimum")
    if policy["min_contract_months"] is not None and arrangement in {"w2", "c2c", "contract"}:
        months = re.search(r"\b(\d+)\s*[- ]?months?\b", description)
        if not months:
            reasons.append("Contract duration needs verification")
        elif int(months[1]) < policy["min_contract_months"]:
            exclusions.append("Contract duration is below this profile's minimum")
    status = "excluded" if exclusions else "verification_required" if reasons else "eligible"
    # A review can resolve unknowns only for the exact facts it reviewed. Hard
    # exclusions always win, including after policy or listing changes.
    override = job.get("eligibility_override_status")
    if not exclusions and policy["confirmed"] and job.get("eligibility_review_fingerprint") == review_fingerprint(job, profile):
        if override in {"eligible", "excluded", "verification_required"} and job.get("eligibility_review_note"):
            status = override
            evidence.append("Candidate review: " + job["eligibility_review_note"])
            if override == "eligible":
                reasons = []
    return {"status": status, "reasons": exclusions + reasons, "evidence": evidence,
            "policy_version": policy_version(profile)}
