# Profile isolation implementation and verification

Started 2026-09-10. Preserve existing private profiles and outstanding docs; no
data reset. This plan verifies the existing product independently per candidate,
with the broader PRD backlog retained in TODO.md.

1. [x] Inspect repository/runtime and preserve existing work. Baseline: 39 focused
   runtime, multi-profile, eligibility and approval tests passed.
2. [x] Audit profile-owned data/services and shared installation resources.
3. [x] Replace shared eligibility policy with editable candidate-private rules;
   invalidate outdated reviews and recheck preparation/approval gates.
4. [x] Verify different profiles' settings, resumes, jobs, queues, materials,
   progress, notifications and browser pairing independently, including restart.
5. [x] Run backend/frontend/extension regressions and synthetic browser workflow;
   verify actual local operation after a safe backup/restart if idle.
6. [x] Reconcile PRD progress/runbook and inspect staged content. Commit this
   reviewed change on `feature/profile-isolation-hardening`; use `git log -1`
   for its actual commit ID. No remote push is part of this checkpoint.

Installation resources may remain shared: listening port, local model service,
source request throttles and concurrency limits. They must not share candidate
credentials, rules, browser sessions, documents or mutable task results.

No test may submit a real application, send a message, or reset real profiles.
Use temporary synthetic candidates for destructive isolation tests.

## Implementation and evidence (2026-09-13)

| Surface | Ownership and verification |
| --- | --- |
| Identity, settings and storage | Immutable candidate child app, private SQLite database and explicitly scoped URLs. Multi-profile tests cover concurrent same-numbered jobs, missing storage, fresh credentials and restart. |
| Eligibility | Validated rules stored in the candidate profile; no personal defaults. Different thresholds give different outcomes for the same job. Policy content and listing fingerprints invalidate older evidence notes. Hard exclusions win over manual review. |
| Queue and materials | Recheck current rules when adding, preparing, approving and dispatching. Missing selected resumes fail instead of falling back. Concurrent synthetic profiles preserve their own generated materials and queues. |
| Progress and notifications | Candidate-owned state, task sets and subscribers. Tests keep the other profile's score/progress/notifications unchanged while work runs. |
| Browser | Candidate cookies and pairing token; a token for A cannot access B. Synthetic Chrome checks cover two tabs, different rules after reload, lifecycle and pipeline. Employer account identity is still a manual check. |
| AI and embedding failures | Circuit breakers are client-owned, preventing one candidate's bad credentials/service failures from blocking another. |
| Scraping and enrichment failures | Cooldowns keyed by candidate and source. Installation-wide request throttles remain shared deliberately. |

Current results: full backend **751 passed in 380.25s**; after the final safeguard
against policy writes from parsed resumes/form learning, **76 focused tests
passed in 13.36s**. Frontend **188 passed**; browser smoke passed and the policy
screen was visually inspected. Extension **472 passed** in the preceding work
session; extension code has not changed since.

The stopped real installation was copied to private backup storage; registry and
candidate database hashes matched, and SQLite integrity passed. Startup migration
preserved all original values across **49 tables**. Host and candidate health
reported healthy with no active work. After the final safeguard, the background
server was stopped while idle and restarted on the same root. No real candidate
policy was invented or automatically confirmed.

Checks: `git diff --cached --check`, local documentation links/anchors, and staged
artifact/credential-pattern inspection. Private backups, screenshots and runtime
data remain outside Git. No dependency changes were required.

Local `qwen3.5:9b` scored one synthetic job for each of two temporary profiles;
both validated scores stayed in their own database. One response needed the
existing bounded correction retry. Command:

```powershell
.\.venv\Scripts\python.exe scripts/verify-profile-ai.py --model qwen3.5:9b
```

This is two smoke cases, not the 30-case quality benchmark. The real 0/600 backlog
failure involved rejected evidence; full real-job scoring recovery remains open.
No real profiles were reset, no real application was submitted, and no cloud AI
or message-sending call was made by this verification.

Remaining PRD work includes keyring storage, portable secret-free export/import,
immutable profile/history versions, complete geographic and authorization rules,
source coverage/deduplication/liveness, model quality, durable recovery/budgets,
Gmail and audited automatic submissions. This change hardens the existing
multi-profile workflow; it does not mark those features delivered.
