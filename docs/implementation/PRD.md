# CareerPulse multi-candidate automation: product requirements

Status: accepted requirements; implementation in progress at T00/T01. Storage,
offline migration and runtime ownership foundations are tested; the planned
multi-candidate end-user workflow is not released. See TASKS.md for evidence and
TODO.md for execution order. This generic document contains no real candidate profile.

## Product goal

A local Windows application that repeatedly discovers relevant jobs, verifies candidate eligibility, rates fit, prepares truthful materials, applies through supported integrations or supplies links, and tracks outcomes with an exact audit trail. Reuse CareerPulse rather than rebuilding its UI and basic application management.

Support both several profiles managed on one laptop and independent installations on other people's computers. Resume upload must not require code changes. Candidate isolation is foundational, not a later optional feature. The local shared-profile version is operated by a trusted Windows user; it is not a hosted multi-user SaaS with separate access control. Cross-device synchronization of a single candidate is deferred; use one active submitting installation per candidate.

## Candidate onboarding and editable policy

Every candidate supplies or confirms:

- Resume(s), factual employment/education/skills/certifications, preferred name and contact details.
- Target titles and seniority, primary role track, optional adjacent tracks.
- Employment arrangements, country/currency, hourly and annual-base thresholds, relocation preferences, local search anchor/radius, allowed remote work locations, exclusions.
- Work authorization and sponsorship needs, distinguishing client/vendor C2C arrangements from direct employment.
- Availability/notice information; missing fields remain unknown.
- Application answer bank and optional disclosure preferences.
- Gmail/account connections, browser identity, AI settings/budget, schedule and daily target.
- Submission preference: automatic, review first, or links only.

A resume supplies evidence, not execution instructions or all policy answers. Never infer protected traits or missing immigration details from names, education, or location. Each profile starts in review mode until its facts and automation settings are confirmed. Settings changes create policy/profile versions and trigger affected re-evaluations without overwriting past submission evidence.

## Discovery and history

- Pluggable sources; initial US sources via JobSpy plus direct Greenhouse/Lever/Ashby discovery. Incrementally enable Dice and other existing adapters only after live validation.
- Per-source search targets, health, errors, last success, coverage, rate limits and next run visible. A failed fetch is not zero vacancies.
- Initial 30-day search; overlapping incremental windows thereafter. Default discovery every six hours. Source quotas are targets, never guaranteed supply.
- Persist raw listing snapshots, normalized facts, source IDs, employer requisition ID, canonical destination, and first/last seen times.
- Verify top candidates are still live before preparation/submission. A source failure or disappearance alone does not prove closure.
- Import candidate-selected historical Gmail application confirmations; default 12 months. Reconcile portal-only application history separately and expose coverage gaps.
- Deduplication is per candidate. Exact requisition/URL match first, then company/title/location/description similarity. Preserve distinct requisitions. Uncertain matches enter review. Record all source aliases.
- An application from one candidate does not prevent another candidate from applying to the same job.

## Eligibility and fit are separate

Eligibility is eligible, excluded, or verification required, with field-level evidence and timestamps. Explicitly unacceptable compensation, arrangement, location, or work authorization overrides any model score. Unstated facts remain unknown. Estimated salary and historical sponsorship cannot establish eligibility for a particular vacancy. Overlapping pay ranges require verification if the offered pay is not established above the minimum.

Retain the upstream role/skills/seniority matching structure, but remove immigration and pay requirements from a merely weighted preference. Return structured component scores, cited profile/JD facts, missing requirements, confidence/uncertainty, and model/prompt/profile versions. Role alignment matters more than overlapping generic tools. Scores are fit assessments, not hiring probabilities or guarantees.

Default bands: 90-100 Excellent, 85-89 Strong, below 85 review/archive. Auto queue requires score >=85 and all hard requirements verified. A daily target cannot relax exclusions, manufacture jobs, or inflate scores. Ranking favors each candidate's configured locations and fresher jobs, with deterministic tie-breaking.

## Preparation and application modes

- Produce tailored resume PDF and DOCX, cover letter when useful/required, and application answers.
- Use only reviewed facts; preserve employers, dates, metrics, qualifications, and claims. Do not invent skill years or dates to fill forms.
- Distinct drafter and reviewer passes; maximum two revision attempts, then manual review. Separate calls do not guarantee factual independence; validate evidence programmatically too.
- Support automatic submission, review-before-submit, and materials plus direct links.
- Automatic submission requires supported tested adapter, matching account identity, confirmed candidate policy, eligible/live job, reviewed materials, resolved duplicate check, and all required answers known.
- Stop that task for CAPTCHA, login/2FA, assessments, unknown questions, and ambiguous controls. Do not bypass access controls.
- First automated routes: Greenhouse hosted forms, then Lever. Workday/iCIMS/Taleo and LinkedIn-specific applications remain assisted until separately implemented and tested.
- Review existing extension functionality but do not assume its claims of universal autofill mean universal submission support.
- Recruiter discovery and personalized outreach/follow-up drafts are included later; messages require user review before sending.

## Audit and lifecycle

Keep job, task, and application status separate. Application stages: ready, preparing, needs review, submitting, applied, assessment, interview, offer, rejected, withdrawn. Operational states include blocked and submission uncertain. Offer acceptance remains a human decision.

Each attempt captures candidate ID, job/requisition, source and final destination URLs, form questions and exact answers, document hashes/versions, profile/policy versions, adapter version, timestamps, confirmation evidence, and errors. Redact secrets from logs. A submit click or extension event alone is not proof of acceptance. Ambiguous completion blocks automatic retry until reconciled.

Gmail sync uses read-only access, message IDs and linked evidence; auto-update only unambiguous outcomes tied to the correct application. Conflicting/unmatched signals enter review. Preserve manual corrections and do not regress stages on old messages.

## Dashboard

- Profile switcher/onboarding with candidate identity visible in all application views.
- Today: confirmed applications vs target, drafts/links separately, verification queue, shortfall reasons.
- Matches: component scores, eligibility facts, pay, work arrangement, location, duplicates, sources, liveness and next action.
- Application pipeline: stage, materials, timeline, email evidence, exact submission audit.
- Runtime: active task/worker, per-source counts, retries, blocked work, heartbeat, last successful cycle, next run, catch-up state.
- Settings: schedules, thresholds, sources, models, per-profile budget allocation and installation cap.
- Pause/resume; backup/export/restore; meaningful notifications only.

## Full backlog retained

The MVP includes generic profiles, discovery, eligibility, deduplication, scoring, basic truthful materials, links/assisted applications, tracking, and run logs. Subsequent work includes durable recovery, Gmail import/sync, automatic submission adapters, additional sources, independent reviewer refinements, company research, recruiter discovery and drafts, Q&A bank, notifications, Notion one-way sync, analytics, interview preparation/tracking, and portable setup. No feature is silently dropped to meet a deadline. Model-generated success probabilities are not an acceptance criterion; report observed outcome metrics with denominators.

## Success and non-goals

Acceptance requires a real local run, meaningful tests, source health evidence, explainable decisions, and no cross-person leakage or duplicate retry. Thirty daily applications and 100-200 listings per source are configurable business targets subject to supply and access. Same-day usability is a priority, not permission to fake implementation or outcomes.

V1 is not hosted on the internet, does not require Docker/Redis/Supabase/Notion, does not promise every source works, and does not operate while the machine is powered off. Credentials and personal data never belong in the public fork.
