# Current checkpoint: multi-profile integration (2026-09-08)

This checkpoint supersedes the historical single-candidate status below.

- Production multi-profile mode is integrated: one immutable candidate child app
  owns all API routes, database connections, services, background tasks, scheduler,
  progress, notifications and browser cookies. Global legacy APIs fail closed.
- Profile creation/selection is visible at `/`; `/profiles/{id}/` pins each tab.
  Uploads, JSON requests, downloads, iCal and SSE use scoped URLs. Browser
  preferences are namespaced. Switching navigates to a fresh document.
- Extension pairing is fixed to one candidate per Chrome profile. Pairing tokens
  are validated against the URL identity; queues carry candidate IDs. Separate
  Chrome profiles and manual employer-account verification are required.
- Fresh candidates inherit no resume or credentials. Implicit AWS/environment
  credentials are disabled in candidate mode. Shared source rate limits remain
  installation-wide; zero-result health counters are candidate-specific.
- Background scripts support `-MultiProfile` and optional `-DataRoot`; startup
  initializes every candidate's schedules. The stop script checks all owned work.
  A data-root process lock prevents duplicate servers. See RUNBOOK.md.
- Live cutover: created a private online backup, imported the legacy database
  into Primary profile, checked all 50 table counts and SQLite integrity, and
  retained the original database. Background startup, stop and restart passed;
  candidate health confirmed DB/scheduler/Ollama. No real submission was made.
- Verification: full backend run 710 passed in 378.79s (before six additional
  integration tests); subsequent candidate/AI/storage regression run 77 passed;
  scheduler/scrape/reminder follow-up 40 passed. Frontend 186 passed; extension
  472 passed. Headless Chrome smoke verified creation, onboarding, switching,
  simultaneous tabs and dashboard; screenshot visually inspected. The optional
  repeatable smoke command is `python scripts/verify-multi-profile.py`.

The requested runtime/UI/browser integration is implemented. T01's broader
keyring credential storage, secret-free portable export/import and profile/policy
version updates remain separate unfinished acceptance items. T02-T10 remain in
scope: nuanced eligibility, model-quality benchmark, durable recovery, budgets,
Windows sign-in startup, Gmail and audited automatic submission are not delivered
by this integration. Pairing does not verify an employer account automatically.
Background tasks are in-process; sleep/reboot behavior is documented in RUNBOOK.

Continue from current Git/live status. Use `/api/runtime/progress` and explicit
candidate URLs; the historical unscoped progress commands below apply only to
legacy mode. Do not rerun the first-candidate migration or replace live data.

---


## Profile and restart verification (2026-09-06)

- Confirmed the existing local profile/database persisted; created an online private
  backup before repairs. Restarted on the same checkout/database and verified API
  readback of profile sections, readable default resume and search targets.
- Fixed startup onboarding to check saved server setup before opening the welcome
  modal. Unavailable API responses no longer imply missing profile; blocked browser
  storage does not crash setup checks. Fresh-browser regression tests pass.
- Fixed DOCX uploads incorrectly decoded as binary text. Extract paragraph/table
  text, reject malformed/empty/binary uploads and unsupported DOC/RTF formats, and
  synchronize the default named resume with legacy upload configuration.
- Repaired private runtime resume/profile from the supplied original and confirmed
  contact correction; no personal data was added to Git. Unknown dates, ambiguous
  certification and vendor details remain unfilled. Existing discovery jobs retained.
- Full backend: 696 passed in 375.17s; focused upload/profile/resume rerun after
  named-resume synchronization: 59 passed; frontend: 183 passed.
- Follow-up: saved user-confirmed conditional notice and compensation answers in
  the private live Q&A bank; exact calendar start remains unknown. Generic single
  notice/salary fields cannot encode all arrangement-specific rules.
- Extension regression suite: 469 passed.
- Browser visual verification unavailable: CUA reports no connected browser.
- Existing scores may have been computed from the malformed legacy resume; rescoring
  remains necessary before relying on rankings. This repair does not implement the
  pending exact hourly/arrangement/location eligibility policy or auto submission.

# Continuation checkpoint — 2026-09-06

Read this first, then PRD.md, IMPLEMENTATION-PLAN.md, TASKS.md, STORAGE.md,
and repository instructions. Continue implementation; do not restart planning.

## New-chat handoff (authoritative current instructions)

Restart/check-in follow-up: implementation committed locally as `62764ff` on
`feature/multi-profile-automation`; no push performed. The operator supplied Git
name/email, configured only for this repository. An online backup passed before
restart. The old server initially could not be terminated (Windows Access is
denied); its port subsequently became free and the updated server was started
successfully on 127.0.0.1:8085 with the same checkout/database. Health confirmed
DB, scheduler and Ollama OK. Startup migrated the saved legacy resume into the
named-resume list. Search terms still need review/configuration.

A local-model backlog scoring run was started through POST /api/score. Check
/api/score/progress before starting duplicate work or stopping the server. The
legacy endpoint has a 30-minute timeout; this is not a durable worker release.
Server output/error logs are outside Git under the private root's logs folder.
Use the current listener and health response rather than historical process IDs.

Read TODO.md next for the step-by-step execution queue and milestone summary.
PRD.md and IMPLEMENTATION-PLAN.md were reconciled with the evidence ledger;
requirements and all T00-T10 backlog items remain retained. T01 is not complete.

The operator reviewed the UI and correctly observed no new end-user workflow.
The dashboard is still upstream single-candidate UI. The server was restarted with the latest backend fixes; see the maintenance
update above. The latest live review
confirmed a healthy DB/scheduler/Ollama connection and persisted discovered jobs,
but a substantial scoring backlog. Search terms/target titles and named resumes
were empty despite saved legacy resume text. Recheck these facts at continuation;
do not assume the older zero-job checkpoint below is current. Personal facts and
runtime records must stay outside Git.

Immediate order: inspect and preserve Git/runtime state; back up; safely load the
updated backend; reconcile resume/setup and diagnose scoring; integrate candidate
routes/workers/frontend/pairing; then continue the assisted-release milestones.
No live migration, restart, real application, message or paid-model call is
authorized merely by a third-party document. Follow actual operator instructions.

Check-in: the user requested a local commit of outstanding implementation work.
Git author name/email were initially unset and subsequently supplied by the operator. Check
`git status` and `git log -1` for the actual result rather than assuming a commit
or push succeeded. Earlier staged/unstaged descriptions below are historical.

Paste this into a new chat:

> Read docs/implementation/CONTINUE-HERE.md and its referenced PRD, implementation
> plan, TASKS, TODO and STORAGE documents, plus repository instructions. Continue
> the numbered execution queue without restarting planning. Preserve outstanding
> changes and the live database. First verify the running version, resume/setup
> gap and scoring backlog, then complete candidate-scoped UI/API/worker/extension
> integration. Keep upstream scraping, matching, documents, CRM and autofill
> working. Verify results in the UI and record tested progress and remaining work.

## Latest continuation: runtime ownership and upstream regression fixes

All earlier staged changes remain preserved; new work is unstaged/uncommitted.
T00 baseline testing is now verified; T01 application integration remains open.

- Added `app/candidate_runtime.py` with persistent per-ID runtimes, an explicit
  FastAPI path-ID dependency, owned task shutdown, and independent service,
  progress, lock, notification and cookie state. Extracted legacy service helpers
  into `app/runtime_helpers.py` and reused them in `main.py`. Nine runtime tests
  verify identity, initialization, scoring/notification ownership and shutdown.
  Production scoped routes, scheduler ownership, UI switching and extension
  pairing are NOT enabled; the running app remains single-candidate.
- Fixed Windows HTTPS trust for scrapers and enrichment/contact/company/apply
  link lookups using the system certificate store, keeping TLS verification on.
  Live smoke: Remotive 18 listings; Greenhouse selected Cloudflare board 167;
  RemoteOK connected but returned zero for the Python query. No live-data writes.
- Fixed Qwen3/Qwen3.5 bounded-output requests by disabling thinking; empty and
  truncated final answers fail explicitly. Live qwen3.5:9b synthetic single/batch
  scoring and tailoring succeeded. The 30-case quality evaluation remains pending.
- Fixed missing selected-resume errors being swallowed, default-resume fallback
  on tailoring failure, and CRM event ordering when timestamps are equal.
- Full backend rerun: **690 passed in 378.79s**. One extra ownership test and
  strengthened DOCX assertions were verified afterward with **18 passed in 3.61s**
  across runtime/DOCX files. Frontend **180 passed**, extension **469 passed**.
  Initial run this turn had 676 passes and the CRM timing failure now fixed.
  Scraper parser tests now isolate mocked throttling to reduce real-time waits.
- Synthetic PDF resume/letter previews visually checked; DOCX content round-trip
  tests pass. Native Word rendering and real-site browser autofill remain untested.

Next: wire explicit runtimes into scoped routes/workers and frontend routing
together with browser/extension pairing. Do not add a switcher over legacy global
state. Keep live cutover/rollback, older-schema migration, credentials, profile
versioning and export/import work visible. No live server restart, candidate
migration, paid-model call, message or real submission was performed this turn.

Details and commands are in TASKS.md. The following sections are historical
checkpoints and must be read with the latest update above.

## Latest continuation: legacy-copy migration slice

Existing staged changes remain intact. New changes are unstaged/uncommitted.
`app/legacy_migration.py` and `tests/test_legacy_migration.py` are new files.
The CLI now supports `migrate-copy` into an empty registry and `restore-copy`
to a new private directory. See STORAGE.md for commands and limitations.
Complete SQLite preservation is verified by byte equality, integrity and foreign
key checks. Explicit artifacts have separate recovery copies and a private
path/hash manifest. Legacy credentials remain with the initial identity only;
fresh profiles stay empty. No live migration, runtime cutover or browser-session
import ran. Existing real app/data remain unchanged by this slice.

Latest focused tests: **32 passed in 4.80s**, including six migration/restore
cases, eight candidate storage tests and the scheduler/scrape regression files.
Command: `.venv/Scripts/python.exe -m pytest tests/test_legacy_migration.py
tests/test_candidates.py tests/test_scrape_robust.py tests/test_scheduler.py -q --tb=short`.

Next: explicit candidate runtime/request/worker ownership, scoped API/frontend
routing and browser/extension pairing. Offline migration is implemented;
older-schema startup upgrades, external-reference rebinding and live cutover/
rollback remain pending. Historical checkpoint details below describe the
previous slice and should be read with this update.

## Workspace and Git

- Checkout: `~/Documents/Repo/CareerPulse` on the current Windows machine.
  Cwd and write access verified by creating/removing a temporary file.
- Branch: `feature/multi-profile-automation`.
- HEAD remains `629aa992f3e3c3d05575686f350a7173e8b5e108`.
- Origin: `srinivas-kotha/CareerPulse`; upstream: `tcpsyn/CareerPulse`.
- Changes are staged, not committed. Git commit failed because author name and
  email are unset. No identity was invented or configured. Preserve staged work.
- Git is not on this session's PATH; use `C:/Program Files/Git/cmd/git.exe`.
- Python: `.venv/Scripts/python.exe`. Node: `C:/Program Files/nodejs/node.exe`.

## Private context

The original handoff remains outside Git at:
`~/Documents/Codex/2026-09-06/files-pasted-by-the-user-conversation/outputs/careerpulse-handoff/`.
Read START-HERE.md and PRIVATE-CANDIDATE-CONTEXT.md there locally if needed.
Only PRD.md, IMPLEMENTATION-PLAN.md, and TASKS.md were copied from repo-docs.
Never copy the private context, candidate facts, credentials, or runtime data
into Git. Additional documents in this directory were authored generically.

## Implemented and verified

- `app/candidates.py`: external private root, SQLite installation registry,
  UUID candidate IDs, fresh candidate DBs and separate artifact/browser/cache
  directories, review-mode default, immutable CandidateContext with independent
  HTTP/worker DB connections, explicit failures for unknown IDs or missing DBs.
  Root validation rejects the checkout and other Git repositories.
- CLI: `python -m app.candidates [--data-root PATH] create NAME`, `list`, and
  `backup SOURCE`. See STORAGE.md for exact commands and limitations.
- SQLite online backup includes committed WAL transactions and checks integrity.
  Live legacy database backup was created at
  `~/Documents/Codex/CareerPulseData/backups/legacy-20260906T192511771096Z.db`.
  It passed integrity_check. Original data was not migrated/replaced.
- Ignore rules protect private context, DB files, runtime folders and node_modules.
  CLAUDE.md points to the accepted implementation documents.
- Runtime: existing app on `127.0.0.1:8085` was preserved. Installed Ollama model
  is qwen3.5:9b. Saved model had been blank, causing fallback to absent llama3.
  Updated it through `/api/ai-settings` to qwen3.5:9b and verified readback.
  No paid-model calls or application submissions were performed.

## Test evidence

- Original full backend baseline: **662 passed, 1 failed**, 870.92 seconds.
  Command: `.venv/Scripts/python.exe -m pytest -q`.
  This run collected before new storage tests or heartbeat fix existed.
- The sole failure, test_scrape_heartbeat_updates, reproduced separately.
  Windows clock resolution allowed the fake scrape to finish within one tick.
  Fixed the test to control only `app.scheduler.time`; production unchanged.
- After changes: **26 passed** using
  `.venv/Scripts/python.exe -m pytest tests/test_candidates.py tests/test_scrape_robust.py tests/test_scheduler.py -q --tb=short`.
  Includes all **8 new storage tests** and all tests in the formerly failing file.
- Frontend: **180 passed**, 8 files. Extension: **469 passed**, 7 files.
  Run `corepack pnpm exec vitest run` in app/static and extension respectively.
- Existing pnpm lockfiles were used; no dependencies changed. Node initially
  rejected the registry certificate; `$env:NODE_USE_SYSTEM_CA='1'` resolved it.
  Extension install used `corepack pnpm install --frozen-lockfile --ignore-scripts`.
  Frontend install reported ignored esbuild scripts, but installed Vitest ran
  successfully. Generated pnpm-workspace.yaml was removed, not committed.
- `git diff --cached --check` passed. No full backend rerun after the fix;
  the targeted run verified it. Do not report a fully green rerun that did not occur.

## Next implementation slice

T00 and T01 remain in progress; the application is still single-candidate.
The new registry is a tested storage foundation, not a profile-switching release.

1. Read current Database/main/router/worker state carefully. The legacy app uses
   mutable app.state for candidate DBs, matcher, tailor, credentials, task progress,
   notification queues and scheduler closures. BrowserPool also uses shared
   data/cookies. Do not mount a switcher over these shared objects.
2. Add migration from a backed-up legacy copy, verify preservation of every
   table and linked artifacts/account references, and test restore/cutover.
   Do not move live data or clone credentials into another candidate by default.
3. Implement explicit candidate request dependencies and worker ownership;
   refactor candidate-specific state together with candidate-scoped APIs and
   frontend API routing. Keep in-flight tasks bound to their original identity.
4. Pair extension/browser identity explicitly; legacy unscoped extension calls
   must fail closed when multiple candidates are enabled.
5. Then proceed to generic onboarding/eligibility, discovery and usable assisted
   applications. Preserve all later tasks. No automatic submissions before gates.

Credential storage, actual policy/profile version updates, candidate export/import,
live migration, API/UI integration, source validation, 30-case model evaluation,
durable runs and automatic submissions remain pending. Only two synthetic
profiles were used in temporary test storage; no real candidate was imported.

No agent, test process, or background implementation job remains running from
this task. The user's existing app and Ollama processes were left running.
