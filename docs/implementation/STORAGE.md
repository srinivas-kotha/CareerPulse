# Runtime integration update (2026-09-08)

The registry is now used by production multi-profile mode. Start with
`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-background.ps1 -MultiProfile`.
The application opens each registered candidate database, applies normal startup
migrations, and starts independent schedules. No implicit legacy migration runs.
One server per data root is enforced by an OS process lock.

The existing installation was copied into Primary profile after private backup;
all table counts and integrity were verified. The original DB and immutable
recovery snapshot remain available. Startup/stop/restart were verified. The
copy/restore commands below remain valid; historical statements that production
integration and live cutover are pending are superseded by this update.

Secrets remain in candidate-private local storage, not a Windows keyring. Browser
pairing tokens are stored under each candidate's browser directory; creating a
profile never clones tokens, accounts, cookies, credentials or resume text.
Portable secret-free export/import and automatic external-reference rebinding
remain pending. See RUNBOOK.md for current operation and deliberate rollback.

# Candidate storage foundation

The storage CLI is implemented. The dashboard, scheduler, and extension still
use the legacy single-candidate database. Creating a registry candidate does
not switch the dashboard or migrate existing data. Do not use the current UI
for multiple people until request, worker, and extension isolation is complete.

Run from the checkout using its existing Python environment:

```powershell
.\.venv\Scripts\python.exe -m app.candidates backup data/jobfinder.db
.\.venv\Scripts\python.exe -m app.candidates list
.\.venv\Scripts\python.exe -m app.candidates create "Example candidate"
```

The default private root is `~/Documents/Codex/CareerPulseData`. Set
`CAREERPULSE_DATA_ROOT`, or pass `--data-root <absolute-directory>` before the
command, to select another external location. The tool rejects storage inside
the checkout. The registry and all candidate files belong outside Git.

Each candidate receives an opaque ID, its own SQLite database, and separate
`artifacts`, `browser`, and `cache` directories. New candidates start in review
mode, with no copied profile or account settings. Display names do not form
paths. Duplicate display names are permitted; IDs determine ownership.

`CandidateRegistry.context(candidate_id)` opens independent request and worker
connections and closes both on exit. Context identity is immutable. Unknown IDs
and missing databases fail explicitly; neither falls back to the legacy user.
This is storage isolation for a trusted local operator, not Windows user access
control. Credential-manager integration and versioned policy editing remain
pending. Failed initialization may leave an unregistered directory for diagnosis;
it is never listed as a usable candidate.

Backups use SQLite's online backup API, include committed WAL transactions,
and pass `PRAGMA integrity_check` before success is reported. Every backup has a
unique timestamp and refuses to overwrite an existing file. Backups contain
private data and potentially legacy credentials; keep them in private storage.
The command does not migrate, replace, or stop the running database. Automated
restore/cutover of the live application remains pending. Synthetic recovery
tests verify backup contents without replacing the live database.

Validation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_candidates.py -q
```

## Legacy-copy migration and recovery

An empty installation registry can now import a previously backed-up legacy
database as its initial candidate. Use a private backup outside Git. This
preserves legacy credentials inside SQLite for that identity; it is not a
secret-free profile export. Further candidates must use `create`.

```powershell
.\.venv\Scripts\python.exe -m app.candidates --data-root C:/Private/CareerPulse migrate-copy C:/Private/Backups/legacy.db "Example candidate" --artifact C:/Private/resume.txt
.\.venv\Scripts\python.exe -m app.candidates --data-root C:/Private/CareerPulse restore-copy CANDIDATE_ID C:/Private/RestoreCheck
```

The import creates an online SQLite snapshot, restores it byte for byte, checks
integrity and foreign keys, and publishes the candidate only after verification.
All SQLite tables, rows, source aliases, embedded document text and account
references survive, including tables unknown to the migration code. No schema
upgrade or application startup runs during import. New identity starts in review.

External artifacts are individual files selected with repeated `--artifact`
arguments. Keep them quiescent during copying. Their hashes and original paths
are recorded in a private recovery manifest; filenames become opaque. The
current app stores prepared materials and uploaded resume text in SQLite and
generates PDF/DOCX downloads on demand. The tool does not discover arbitrary
external references, rewrite paths in database text, or import browser sessions,
environment credentials, or OS credential-store entries.

`restore-copy` verifies the recovery database and artifacts and restores them
into a new external directory. It refuses existing destinations and does not
alter the registry or running app. Recovery files are separate from editable
candidate files; retain the entire candidate directory. A failure can leave an
unregistered or partial directory for diagnosis. Live cutover, startup migrations
against older schema versions, and rollback of an active runtime remain pending.

Next: integrate explicit request/worker contexts, candidate-scoped APIs and
frontend routing with extension pairing before switching the live application.

## Candidate runtime ownership

`CandidateRuntimeManager` now manages one persistent runtime per explicit
candidate ID, with independent request/worker connections, AI service objects,
locks, progress, notification queues and a browser pool with private cookie
storage. Its async context manager cancels and drains owned tasks before closing
connections. Startup failures are not cached. `require_candidate_runtime` is a
FastAPI dependency that requires a path candidate ID and never falls back to the
legacy database. These components are tested but not mounted in the legacy app.

The legacy app now uses the same extracted service-helper implementation,
preserving its routes. Actual scoped routes, frontend switching, browser/extension
pairing, and scheduler ownership remain the next integration slice. Do not expose
multiple profiles through the legacy routes. Dedicated cookie storage alone is
not account-identity verification or a persistent Chrome profile implementation.
