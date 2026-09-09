> Status update, 2026-09-08: candidate runtime/API/UI/worker integration,
> extension pairing, and live copy cutover are implemented and verified. See
> CONTINUE-HERE.md for current evidence and remaining T01 acceptance items.
> Historical single-candidate status below is superseded; requirements remain.

# Implementation plan

Status: accepted plan, execution in progress at T00/T01. Continue from
CONTINUE-HERE.md and TODO.md; do not restart architecture planning. Follow TASKS.md
for execution evidence. Upstream features still run in single-candidate mode;
tested storage/runtime helpers do not yet constitute integrated profile support.

## Foundation and delivery

Extend the existing FastAPI, aiosqlite, APScheduler, vanilla JavaScript UI, and browser extension. Preserve upstream behavior where compatible. Keep origin pointed at the user's fork and upstream at tcpsyn/CareerPulse. Start an implementation branch named `feature/multi-profile-automation` after checking for user changes. Make narrow reviewable commits and a PR to the fork, never accidentally to upstream. Preserve licenses and audit dependency licenses before packaging.

Retain the existing live app/data as the baseline. Back up with SQLite's backup API before migrations; copying a live WAL database file alone is not adequate. Record the upstream SHA and test results. Do not delete or reset user data or use destructive Git commands to obtain a clean tree.

## Multi-candidate design

Use an installation registry with candidate IDs, paths and scheduler metadata, plus one SQLite DB and artifact directory per candidate. Keep the private data root configurable and outside the checkout; fresh installs default to a CareerPulseData directory under the operator's Documents/Codex folder. Do not automatically move existing data until backed up and migration-tested.

Create a CandidateContext containing explicit candidate ID, DB connections, profile/policy versions, model settings, credentials references, and browser directory. Use request dependencies to resolve this context. Remove candidate-specific mutable global `app.state` accesses from routers/workers; no ambient 'current candidate' determines task ownership. Maintain independent HTTP and worker DB connections where needed.

Profile-scoped APIs use `/api/candidates/{candidate_id}/...`; global endpoints are limited to registry, health, budgets, and operator controls. Browser/extension pairing binds to a candidate and validates identity before filling. Changing the visible UI profile cannot rebind existing tabs, queued tasks, or documents. Require explicit selection rather than a silent default for legacy extension calls after multi-profile support is enabled.

Keep API keys/OAuth credentials protected through Windows credential storage with references in candidate settings. Dedicated browser data directories per candidate. Localhost binding, restrictive origins, and pairing tokens for extension calls; never expose profile APIs to arbitrary websites. Separate directories prevent mistakes, not hostile access by the same Windows user.

Migrate an existing single-user DB into one initial candidate context without loss. Restore test must preserve source aliases, application events, profile facts, documents and account references. Do not clone credentials when creating another candidate. Export/import profile data excludes secrets and reconnects accounts.

## Data and interfaces

Within each candidate DB, extend existing jobs/applications with canonical aliases, listing snapshots, fact evidence, versioned policies/profiles, and review decisions. Add durable runs, tasks, task events, model usage, application attempts, artifact metadata, and Gmail cursor/message-evidence records. Installation registry enforces shared AI budget reservations and worker coordination.

Task input is immutable and includes candidate, operation, input versions and idempotency key. Cache evaluations by candidate/profile/policy/JD/model/prompt versions. Claim work transactionally with a lease/heartbeat. On expiry, non-submission work can retry; ambiguous submission work transitions to reconciliation instead.

Expose run/task list/detail, start/pause/retry, eligibility review, history import, and attempt audit endpoints. Keep upstream UI functionality available through a single frontend API wrapper updated for candidate scope. Use server-sent events for progress with persisted run/task state as the source of truth after reconnect. Never rely only on in-memory progress dictionaries.

## Each runtime cycle

1. Dispatcher checks due work every 30 seconds and records run ID/config version. One local worker process initially, serialized browser submissions, one model request at a time.
2. Claim/resume tasks; detect offline/auth/budget conditions. Initial discovery immediately, then every six hours per candidate, configurable in America/Chicago for the first candidate.
3. Scrape due sources using adapter-specific arguments and quotas. Persist counts, raw results, cursor/window and source errors. No silent fallback from failed to empty.
4. Normalize facts and canonicalize links; deduplicate against all portal aliases and candidate application history.
5. Verify liveness and hard eligibility. Preserve evidence. Unknown/overlapping requirements go to verification; do not use predicted salaries as facts.
6. Score new/changed plausible matches. Cheap deterministic checks first; LLM extraction/assessment uses schema validation and source evidence.
7. Prepare strongest candidates; draft and review with bounded revisions, save immutable artifacts.
8. Execute selected application mode after rechecking candidate/account, eligibility, live posting, duplicates and documents. Capture exact payload, then confirmation. Never blind-retry a possibly successful submit.
9. Sync Gmail every 15 minutes with incremental cursor; reconcile unambiguous status events. Expired cursor triggers bounded re-sync with message-ID deduplication.
10. Update dashboard counts, budget, task events, next due times, and meaningful notifications. Track all shortfalls and deferred work.

Retry transient source/model errors up to three retries with exponential delay and source Retry-After. Pause a failing source without blocking others. Cancellation marks checkpoints accurately. Coordinate limits across profiles so extra profiles do not multiply source request rates or costs invisibly. Candidate scheduling is round-robin to avoid starvation.

## Models and cost

Selected starting local model is `qwen3.5:9b`, not the previously suggested qwen3:8b. Start with context 8192 and concurrency one; validate context truncation never drops eligibility information. Download size is about 6.6 GB, not runtime VRAM usage. Confirm GPU use and benchmark with Ollama/nvidia-smi. Basic generation has succeeded; application quality has not been tested. Inspect Ollama thinking-output handling so internal thinking is not inserted into resumes or parsed as JSON.

Use a 30-case representative evaluation set before automation. All hard-rule cases must pass; structured outputs must parse and no unsupported fact may be accepted. If local quality fails, keep human review and test selective OpenAI GPT-5 mini drafting/review after model availability, API arguments and pricing verification. Never upgrade silently to a costly model.

Installation cap defaults to $25/month, warning at $20; reserve worst-case in-flight request cost and reconcile returned token usage including reasoning where billed. Per-candidate allocations must fit the global cap. Caching, deterministic extraction/filtering, short bounded outputs, and top-match-only drafting reduce cost. Default Gmail interpretation stays local. No paid proxies/data services initially. Local runtime AI spending and Codex development usage are separate.

## Recovery, packaging and usability

Windows sign-in starts the loopback server and worker, with a single-instance lock and restart policy. After sleep/shutdown, run one catch-up cycle and resume checkpoints, rather than replaying every missed scheduled run. App cannot execute while off. Browser tasks wait for a usable signed-in session.

Provide setup/start/stop/backup/restore/update PowerShell scripts and a desktop shortcut. Setup manages a Python 3.12 environment, dependencies, and browser binaries; detects existing installs. Do not require Docker, WSL or a CUDA toolkit just to use Ollama. Keep model installation optional if an approved API is selected. Explain first-run onboarding and recovery in a short operator guide. Package profiles generically for other Windows installations.

Existing baseline command:
`uv run --python 3.12 --extra playwright uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8085`

## Validation and rollout

Read actual local instructions, existing docs/plans, CI and tests. Run backend pytest and frontend/extension npm test after installing locked dependencies with npm ci where a lockfile exists; do not blindly invoke npx to fetch an unrelated tool version. Repository documentation test totals are not proof of passing tests.

Test profile isolation including concurrent requests, switch during generation, wrong browser account, export/import and migration. Test salary units/ranges, sponsorship distinctions, remote headquarters vs required work location, stale evidence, duplicate requisitions, email conflicts, retries, power-loss simulation, cost reservations and prompt injection. Render final PDFs/DOCX and check extractable text and visual layout using appropriate artifact workflows.

Enable each source only after live smoke testing. Submission adapters first pass local form fixtures for hidden/conditional required fields, uploads, validation errors and confirmation; then perform one authorized real eligible application with full evidence before unattended operation. Do not submit test applications to real employers merely to exercise the code.

Roll out assisted features first. Gate automatic adapters by tested capability, not a global 'supports all ATS' claim. Track actual source reliability and outcome rates; retain rollback through database backups and versioned code.

## Estimates and research references

Original rough estimates: baseline 1-2h; generic profiles additional 4-8h; first useful release additional 3-6h; history/recovery additional 4-8h; first automatic routes additional 1-3 workdays; broader backlog additional 3-6 workdays. Installation is now partly complete. Re-estimate after baseline inspection and do not present estimates as guarantees. User wants same-day usability: prioritize vertical slices and parallelize independent tool checks, not uncontrolled model-agent spawning.

Reviewed reference repositories: https://github.com/tcpsyn/CareerPulse ; https://github.com/speedyapply/JobSpy ; https://github.com/career-ops-hq/career-ops ; https://github.com/MadsLorentzen/ai-job-search ; https://github.com/Gsync/jobsync . Other Gemini suggestions included leopu00/job-hunter-team, Liam-Frost/AutoApply, anandanair/job-scraper, AIHawk, autopilot-jobhunt, Dify/n8n/AppFlowy. These were not selected and do not require renewed comparison unless the chosen foundation fails materially.

Technical references: https://docs.ollama.com/windows ; https://ollama.com/library/qwen3.5:9b ; https://developers.google.com/workspace/gmail/api/guides/sync ; https://developers.google.com/workspace/gmail/api/auth/scopes ; https://docs.astral.sh/uv/getting-started/installation/ . Recheck changing API/model details at implementation time. Gemini's claims of unrestricted scraping, guaranteed conversion gains, universal support and popularity were not accepted as verified facts.
