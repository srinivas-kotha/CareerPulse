# Implementation task ledger

Prepared 2026-09-06. Check a task only after its acceptance evidence exists. Documentation is not implementation. Update this ledger in the repository as work proceeds.

## Status convention

States: pending, in progress, blocked, complete. For each task record commit, test command/result, artifact or UI evidence, remaining risks, and next step. Never infer completion from an upstream README claim. Real candidate data and submission evidence stay in private runtime storage, not this ledger.

Current execution order and milestone summary: [TODO.md](TODO.md). New-chat
instructions: [CONTINUE-HERE.md](CONTINUE-HERE.md). PRD/plan requirements remain
accepted; T00/T01 are in progress and the integrated T02-T10 outcomes are pending.
The latest UI review found persisted discovery data but incomplete resume/search
setup and a scoring backlog. Test success does not imply a completed user flow.

Latest maintenance: PRD/plan status reconciled and step-by-step TODO/new-chat
handoff added. Implementation committed locally as `62764ff`; no push performed.
Git identity was supplied by the operator and configured locally. Online backup
passed; the old server initially resisted termination, but its port subsequently
became free. The updated server started successfully on loopback using the same
DB; health verified DB/scheduler/Ollama. Startup reconciled the legacy resume into
the named-resume list. Search preferences remain unconfigured. A local-model
scoring backlog run was triggered; check live progress before duplicate work.
Existing test evidence below was retained, not rerun during this maintenance.

## Completed setup / incomplete verification

- [x] Actual fork and checkout exist; origin and upstream verified.
- [x] User reports CareerPulse opens locally.
- [x] Local qwen3.5:9b generates a response.
- [x] GPU model/VRAM/driver verified with nvidia-smi.
- [x] PRD, plan, private context and continuation instructions prepared outside the repo due to workspace restrictions.
- [x] Copy generic docs into docs/implementation or save them there from a repo-scoped coding task.
- [ ] Verify saved model settings, browser dependencies, running process, port, and actual data paths.
- [ ] Run baseline tests and complete code audit of change surfaces.
- [ ] T01 storage foundation implemented and tested; full candidate integration and subsequent milestones remain pending.

## T00: Establish implementation workspace (first)

- [x] Confirm cwd and write permission target the real checkout; read applicable instructions.
- [x] Inspect Git status/remotes/HEAD; preserve existing changes and data.
- [x] Verify branch `feature/multi-profile-automation`; create only if absent.
- [ ] Read existing docs/plans and frontend/extension startup and CI scripts.
- [x] Inventory existing DB/data; create and verify SQLite backup before migrations.
- [x] Persist PRD.md, IMPLEMENTATION-PLAN.md, TASKS.md; add a short repository instruction pointer without overwriting existing instructions.
- [x] Run baseline backend, frontend and extension tests; separate pre-existing failures from new regressions (latest evidence below).

Acceptance: reproducible baseline, preserved data, generic docs in the fork, correct origin and no personal data staged.

## T01: Candidate contexts and storage (depends T00)

- [x] Installation registry and configurable external data root (scheduler metadata remains T06).
- [ ] Candidate database/artifact directory creation and lifecycle.
- [ ] Explicit CandidateContext request dependency and worker context.
- [ ] Refactor global candidate state in routes, matching, tailoring, autofill, scheduler and notifications.
- [ ] Migrate existing single-person data into the first candidate without loss.
- [ ] Separate browser profiles, token references, caches and documents.
- [ ] Candidate-scoped API wrapper and profile switcher.
- [ ] Isolated, non-secret profile export/import for separate installations.

Acceptance: two synthetic profiles can operate independently; profile switching during a task cannot change its identity; backup restore works.

## T02: Generic onboarding and eligibility (depends T01)

- [ ] Parse PDF/DOCX/text resumes into evidence-linked factual profile, preserve original.
- [ ] Review/edit onboarding for role targets, arrangements, pay, location, authorization and availability.
- [ ] Version policy/profile; invalidate only affected evaluations.
- [ ] Rule evaluator with eligible/excluded/verification states and evidence.
- [ ] Separate C2C/W2 hourly rates and full-time base; preserve currency and range semantics.
- [ ] Location/remote restrictions; historical sponsorship cannot prove specific-role eligibility.
- [ ] Unknown/overlap handling and explicit review decision UI.
- [ ] Import first candidate's private facts after review without placing them in Git.

Acceptance: all hard-rule fixtures pass; unknowns never become automatically eligible; other candidates inherit no personal restrictions.

## T03: Discovery and duplicates (depends T01-T02)

- [ ] Inspect each existing source; record actual method, credentials and known limitations.
- [ ] JobSpy adapter with correct per-site arguments and bounded requests.
- [ ] Initial live direct ATS adapters (Greenhouse/Lever/Ashby as verified).
- [ ] Normalized raw snapshots, canonical links and requisition IDs.
- [ ] First 30-day and subsequent overlapping incremental discovery.
- [ ] Candidate-specific exact/fuzzy duplicate checks and uncertain-review queue.
- [ ] Liveness check; distinguish source outage from job closure.
- [ ] Per-source counts/errors/last-success/next-run in UI.
- [ ] Source request budgets coordinated across candidates.

Acceptance: real listings from functioning sources, one canonical job for aliases, distinct requisitions retained, visible unavailable sources. No claim of 100-200 results if fewer were returned.

## T04: Local matching and trustworthy materials (depends T02-T03)

- [ ] Test Ollama model selection/endpoint and actual GPU use.
- [ ] Benchmark 30 representative cases with context 8192/concurrency one.
- [ ] Correct handling of thinking fields, JSON schema, truncation and malformed responses.
- [ ] Explainable fit bands and evidence separate from eligibility.
- [ ] Cache per candidate/profile/policy/JD/model/prompt version.
- [ ] Tailored PDF/DOCX and useful cover letters/application answers.
- [ ] Separate reviewer pass with at most two revisions; unsupported claims block.
- [ ] Preserve immutable document versions and hashes.
- [ ] Visual rendering and extractable text checks for output artifacts.

Acceptance: accurate factual materials for real shortlisted jobs, documented model quality, no invented experience or dates, correct profile ownership.

## T05: Usable assisted release (depends T01-T04)

- [ ] Matches/verification/pipeline UI with candidate banner.
- [ ] Direct apply links and download/copy actions.
- [ ] Candidate-bound extension pairing and assisted form fill.
- [ ] Manual confirmed-applied action differentiated from automatic evidence.
- [ ] Basic persisted run/task progress and daily target/shortfall report.
- [ ] One-click start instructions; demonstrate complete discover-to-assisted-apply flow.

Acceptance: user can find, review and apply to a genuine eligible job with prepared materials and track it. Do not call auto-submit or durable recovery complete at this milestone.

## T06: Durable harness and budgets (can start after T01)

- [ ] Runs/tasks/events persisted with immutable identity/inputs and idempotency keys.
- [ ] Transactional claims, lease heartbeat, cancellation and bounded retry.
- [ ] Recovery of unfinished work; submission-uncertain reconciliation.
- [ ] Six-hour discovery, 15-minute Gmail sync, 30-second dispatch configurable per candidate.
- [ ] Fair profile scheduling, shared source limits, one model request/browser submit initially.
- [ ] Installation-wide cost reservations/cap and per-profile allocations.
- [ ] Runtime view and SSE reconnect from persisted state.
- [ ] Startup-at-sign-in, single instance, sleep/offline recovery and one catch-up cycle.

Acceptance: simulated interruption resumes safe work; no duplicate applications; cap respected with in-flight work; app reports outages honestly.

## T07: Historical application and Gmail reconciliation (depends T01,T06)

- [ ] Gmail OAuth read-only local setup and protected token storage.
- [ ] Twelve-month application-related import configurable per candidate.
- [ ] LinkedIn-only application history reconciliation/import and explicit coverage gaps.
- [ ] Incremental message processing, cursor-expiry recovery and deduplication.
- [ ] Evidence-linked unambiguous status updates; conflicting/unmatched messages enter review.
- [ ] Preserve manual corrections, chronology and candidate identity.

Acceptance: past confirmed applications suppress repeats; replaying messages is idempotent; offers are not automatically accepted.

## T08: Audited automatic applications (depends T02-T04,T06-T07)

- [ ] Generic adapter interface with capability/status declaration.
- [ ] Greenhouse hosted-form adapter, then Lever.
- [ ] Preflight checks: identity, authorization, live vacancy, duplicate, eligibility, facts and artifacts.
- [ ] Correct numeric units and exact answer-option mapping; never infer legal start dates.
- [ ] Required/conditional fields and uploads; no blanket defaults for ambiguous questions.
- [ ] Exact question/answer/document/destination snapshot before submission.
- [ ] Confirmation detection independent of button click; uncertain outcome state.
- [ ] Local fixtures for errors, hidden requirements, network failures and resume upload.
- [ ] One real authorized eligible application per adapter with full evidence before unattended enablement.

Acceptance: supported submissions have verifiable confirmation and exact audit; unknowns/login/CAPTCHA/assessments pause; crash or retry does not duplicate.

## T09: All remaining features (incremental, not forgotten)

- [ ] Dice, additional boards, and wider company directories after live checks.
- [ ] Workday/iCIMS/Taleo/LinkedIn-specific capabilities as individually tested adapters; assisted fallback retained.
- [ ] Company research with sources and timestamps.
- [ ] Recruiter contact discovery, CRM and personalized outreach drafts.
- [ ] Follow-up drafts and reminders; sending requires review.
- [ ] Q&A bank refinements and interview preparation/tracking.
- [ ] In-app notifications first; configurable Telegram/email/webhook channels, default disabled until configured.
- [ ] Notion one-way candidate-scoped sync, local DB remains source of truth.
- [ ] Observed application/conversion analytics with denominators; no unsupported success predictions.
- [ ] Cost-of-living information for relocation review, with sourced data and no automatic override of exclusions.

## T10: Packaging, portability and release

- [ ] Windows setup/start/stop/backup/restore/update scripts and shortcut.
- [ ] Fresh-install and upgrade/migration test, including separate candidate installation.
- [ ] Document account connection, model options, budget, troubleshooting, privacy and limitations.
- [ ] Verify no personal data/secrets in Git or test fixtures; preserve license attribution.
- [ ] Run relevant baseline/regression suites and record actual counts/results.
- [ ] Create PR to the user's fork with final behavior and validation evidence.
- [ ] Release only tested capabilities; leave pending items visible.

## Mandatory cross-cutting regression cases

- [ ] Candidate A submits; candidate B may apply to same requisition.
- [ ] Two different requisitions at same employer remain distinct.
- [ ] Wrong browser identity and profile-switch races fail closed.
- [ ] Below-minimum compensation excluded; overlap or missing pay verified manually.
- [ ] Explicit sponsorship incompatibility excluded; unknown remains unknown.
- [ ] C2C acceptance is not confused with client sponsorship.
- [ ] Excluded headquarters with allowed remote residence retained; required excluded relocation rejected.
- [ ] Conflicting/old emails cannot silently overwrite newer manual decisions.
- [ ] Power loss after submit does not trigger blind resubmission.
- [ ] Listing/resume/email prompt injection cannot change policy or execute actions.
- [ ] Budget reservations prevent concurrent overspend.
- [ ] Generated factual claims map to approved candidate evidence.
- [ ] Reset/delete/export actions are scoped to the intended candidate and require explicit user intent for destructive operations.

## Evidence log template

Task ID:
State:
Commit:
What changed and why:
Tests and results:
UI or runtime evidence (private artifacts referenced locally):
Known limitations:
Next task:

## 2026-09-06 implementation evidence

Task IDs: T00 / T01
State: in progress (storage foundation complete; application integration pending)
Commit: uncommitted on feature/multi-profile-automation; commit attempt failed
because Git author name/email are unset. No identity was configured.

- Verified checkout and temporary-file write access. Original tracked tree clean;
  baseline HEAD `629aa992f3e3c3d05575686f350a7173e8b5e108`. Origin points to
  `srinivas-kotha/CareerPulse`; upstream points to `tcpsyn/CareerPulse`.
- Copied only the three generic handoff documents. Private context remains in
  its original external location. Added ignore rules and a CLAUDE.md pointer.
- Read repository instructions, CI and package manifests, original architecture,
  robust scrape design, extension/profile design, and current storage/lifespan
  implementation. Other historical plans were indexed, not fully audited.
- Existing loopback listener on port 8085 was preserved. Legacy database has
  50 tables. SQLite online backup saved under the external default data root's
  `backups` directory and passed integrity_check. No live data migration ran.
- Added app/candidates.py: external-root registry, fresh candidate databases,
  separate artifact/browser/cache directories, immutable explicit contexts,
  dual DB connections, and create/list/backup CLI. No candidate APIs, UI switcher,
  worker refactor, live migration, secret store, or export/import is claimed.
- Eight new tests pass: concurrent synthetic profile isolation, settings
  isolation, independent same-requisition state, immutable context identity,
  missing/invalid ID rejection, missing DB rejection, root validation, and
  committed-WAL backup recovery with overwrite protection.
- Frontend: 180 passed (8 files). Extension: 469 passed (7 files). Used existing
  pnpm lockfiles and installed Vitest 3.2.4, without changing dependencies.
  Corepack initially hit certificate verification failure; enabling Node's
  system CA store resolved it. Dependency build scripts were not needed for
  either test suite. Backend baseline: 662 passed, 1 failed in 870.92s; see triage below.
- Runtime setup: confirmed installed Ollama model qwen3.5:9b. Saved app model
  was blank (upstream fallback llama3, absent locally). Saved qwen3.5:9b through
  the loopback settings API and verified readback. No paid model or real
  application was invoked; model quality evaluation remains pending.

New tests: `.\.venv\Scripts\python.exe -m pytest tests/test_candidates.py -q`
Storage usage and limitations: [STORAGE.md](STORAGE.md).
Next: complete baseline failure triage, then legacy-copy migration verification
and explicit request/worker context integration before enabling profile switching.

Baseline triage: test_scrape_heartbeat_updates failed reproducibly because the
real Windows monotonic clock returned the same value for an entire fast fake
scrape. The test now controls only the scheduler clock; production behavior is
unchanged. Focused regression command:
`.\.venv\Scripts\python.exe -m pytest tests/test_candidates.py tests/test_scrape_robust.py tests/test_scheduler.py -q --tb=short`
Result: 26 passed in 3.74s. This includes all 8 new storage tests.

Full baseline completed: 662 passed, 1 failed (heartbeat timing test above).
The run collected before new tests/fix existed. The corrected focused suite
passed 26 tests; no full post-fix backend rerun was performed.
Continuation checkpoint: [CONTINUE-HERE.md](CONTINUE-HERE.md).

## 2026-09-06 continuation: legacy-copy migration slice

Task ID: T01, still in progress. Existing staged changes preserved; this slice
is unstaged and uncommitted.

- Added `migrate-copy` for an empty installation registry. Imports a private
  SQLite backup as the initial candidate, preserving the complete database,
  including unknown tables and legacy account/credential references. Integrity,
  foreign keys, and byte equality are checked before publication. A transaction
  rechecks registry emptiness at publication. Other profiles still start fresh.
- Explicit external artifacts receive verified copies and a private path/hash
  manifest. Browser sessions and ambient environment credentials are not imported.
- Added `restore-copy` to a new private directory, with checksum verification and
  independent recovery files. Neither command switches or stops the legacy app.
- Six new synthetic tests cover complete restore, binary/duplicate rows in an
  unknown table, credentials, independent fresh profiles, editable active files,
  overwrite rejection, corruption, manifest traversal, broken foreign keys and
  interrupted copying. No real candidate data was imported.
- Validation: `.venv/Scripts/python.exe -m pytest tests/test_legacy_migration.py
  tests/test_candidates.py tests/test_scrape_robust.py tests/test_scheduler.py -q
  --tb=short`: **32 passed in 4.80s**. No full backend/frontend/extension rerun;
  frontend and extension code did not change.

Remaining: live cutover/rollback and older-schema startup migration testing;
automatic discovery/rebinding of external file references; Windows credential
storage; explicit request/worker ownership and API/UI/browser integration.
The T01 acceptance checkbox remains open. Next implement candidate runtime
ownership before routing multiple candidates through the app.

## 2026-09-06 continuation: runtime ownership and upstream checks

Task IDs: T00/T01; targeted fixes supporting T03/T04/T05. T01 remains in progress.
All prior staged changes preserved; new implementation is unstaged/uncommitted.

- Extracted shared service helpers from `main.py`. Added a persistent candidate
  runtime manager, explicit path-ID request dependency, independent services/
  locks/progress/notification queues, and owned background tasks. Shutdown drains
  workers before closing DB connections. Browser pools can now use separate
  cookie directories and reject path traversal. Nine runtime tests cover request
  identity, in-flight ownership, scoring/notification separation, shutdown,
  failed startup retry and browser cookie isolation. Production profile routes,
  scheduler migration, frontend switching and extension pairing are not enabled.
- Live source checks exposed Windows CA verification failures. Scraper HTTP
  clients and enrichment/apply-link/contact/company lookup clients now use the
  system trusted roots with certificate and hostname verification still enabled.
  Retest: Remotive devops returned 18 listings; Greenhouse Cloudflare engineer
  search returned 167; all returned URLs used HTTPS. RemoteOK responded but the
  Python query returned zero listings. No job eligibility or universal source
  reliability is implied by these counts. Scraper error-to-empty behavior still
  needs structured source-health handling under T03.
- Local qwen3.5:9b matching initially returned no parseable final JSON. Qwen3/
  Qwen3.5 requests now disable thinking so the bounded output budget reaches the
  final answer; empty and length-truncated answers fail explicitly. Retest on a
  synthetic platform-engineer example returned valid scoring JSON (score 92);
  tailoring returned resume and cover-letter text without thinking markup.
  This is a smoke check, not the 30-case quality/eligibility evaluation.
  API reference: https://docs.ollama.com/capabilities/thinking .
- Fixed resume preparation swallowing a missing selected-resume error; it now
  returns 404 without generating an application. Tailoring failure retains the
  explicitly selected resume instead of substituting the default resume.
- Fixed CRM timeline ordering for equal timestamps using descending event ID
  as a tie-breaker, with a deterministic regression fixture.
- Strengthened DOCX tests to read back generated content. Synthetic resume and
  cover-letter PDF previews were rendered and visually inspected: readable,
  no clipping or overlap. DOCX generation/content/API tests pass; native Word
  layout and real browser form integration are not yet visually validated.
- Parser tests now isolate mocked source throttling from shared real-time quotas;
  production throttling and its dedicated tests are unchanged.

Validation results:

- Initial full run this turn: 676 passed, 1 failed in 840.36s. Sole failure was
  the equal-timestamp CRM timeline ordering, reproduced and fixed above.
- Full rerun: `.venv/Scripts/python.exe -m pytest -q --tb=short`:
  **690 passed in 378.79s**. This collected before the final additional scoring/
  notification ownership test. Final runtime/DOCX follow-up:
  `.venv/Scripts/python.exe -m pytest tests/test_docx_export.py
  tests/test_candidate_runtime.py -q --tb=short`: **18 passed in 3.61s**,
  including all nine runtime tests and strengthened DOCX content assertions.
- Frontend: **180 passed**. Extension: **469 passed**. Both used
  `corepack pnpm exec vitest run` in their respective directories.
- Other focused checks: affected backend selection 190 passed;
  CRM/database/storage follow-up 48 passed.
- Additional live local-model batch smoke returned two correctly identified
  synthetic job IDs: platform role 92/matching track, frontend role 5/mismatched
  track. These examples do not satisfy the planned model-quality benchmark.

Live app was not restarted or migrated; no real application or message was sent,
and no paid-model call was made. New code takes effect when the app next loads it.
Next: wire explicit runtimes into candidate-scoped router/worker operations and
frontend routing together with extension pairing; retain migration/cutover gates.
