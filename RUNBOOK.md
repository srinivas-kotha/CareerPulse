# CareerPulse runbook: from fork to everyday use

Start here if you are new to this fork. This guide covers **Windows, PowerShell,
and local multi-profile mode**. Run commands from your checkout unless stated
otherwise. Replace example names and paths with your own.

Last reviewed: 2026-09-09. Instructions were checked against the current code.
Windows operation and profile workflows have been exercised locally; a complete
fresh-machine installation was not repeated for this documentation update.

## Find what you need

| Task | Section |
| --- | --- |
| Fork and install | [1. Install](#1-install-from-your-fork) |
| Start after installation or reboot | [2. Start](#2-start-the-application) |
| Resume, profile, AI and search setup | [3. First profile](#3-set-up-your-first-profile) |
| Discover jobs, prepare, apply and track | [4. Daily use](#4-use-the-application) |
| Rename, delete or clear data | [5. Profiles](#5-manage-profiles-and-clear-data) |
| Browser autofill | [6. Extension](#6-install-and-pair-the-extension) |
| Health, progress and logs | [7. Status](#7-check-status-and-logs) |
| Stop, restart and update | [8. Maintenance](#8-stop-restart-and-update) |
| Backup and recovery | [9. Recovery](#9-back-up-and-recover) |
| Import old single-profile data | [10. Migration](#10-migrate-a-legacy-installation) |
| Diagnose a problem | [11. Troubleshooting](#11-troubleshooting-and-support) |
| Contribute and maintain this guide | [12. Contributors](#12-contributor-checks-and-documentation) |

## 1. Install from your fork

### Prerequisites

| Component | Purpose |
| --- | --- |
| Git and GitHub account | Fork, clone and update |
| PowerShell | Run Windows commands |
| uv | Install Python and locked dependencies |
| Python 3.13 | Matches repository CI; project requires Python 3.12 or newer |
| Chrome | Extension use and optional browser smoke test |
| Ollama, if using local AI | Runs the model separately from CareerPulse |
| Node.js and pnpm, contributors only | JavaScript tests; not needed to serve the UI |

Install [Git for Windows](https://gitforwindows.org/) and follow the
[official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).
For example, with Windows Package Manager:

```powershell
winget install --id=astral-sh.uv -e
```

Open a new PowerShell window afterward and check:

```powershell
git --version
uv --version
```

### Fork and clone

1. Open [the maintained fork](https://github.com/srinivas-kotha/CareerPulse).
2. Click **Fork**, choose your account and create your fork.
3. Copy your fork's HTTPS clone URL; replace the example below.

```powershell
$repoParent = Join-Path $env:USERPROFILE 'Documents\Repo'
New-Item -ItemType Directory -Path $repoParent -Force | Out-Null
Set-Location $repoParent
git clone https://github.com/YOUR-GITHUB-USERNAME/CareerPulse.git
Set-Location CareerPulse
git remote add upstream https://github.com/srinivas-kotha/CareerPulse.git
git remote -v
```

**Success:** origin points to your fork; upstream points to the maintained fork
above. For an existing checkout, inspect remotes before adding/changing them.
The original project is tcpsyn/CareerPulse; the maintained fork above contains
the profile features described here.

### Install the environment

```powershell
uv python install 3.13
uv sync --locked --python 3.13 --extra playwright
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe --version
```

**Success:** each command completes without errors and the virtual environment's
Python exists. Activation is unnecessary with these commands. The browser pool
tries installed Chrome first, then bundled Chromium. Keep the Playwright extra
on later syncs so browser-backed scraping dependencies stay installed.
The locked sync checks the committed dependency lock; see
[uv sync documentation](https://docs.astral.sh/uv/concepts/projects/sync/).

No separate frontend server/build, Docker or .env file is required for this
Windows workflow. Save candidate AI keys/search settings in the UI. The legacy
.env.example does not initialize new multi-profile candidates.

### Choose private storage once

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'Documents\Codex\CareerPulseData'
```

Or choose another private absolute path, such as D:\Private\CareerPulseData.
It must be outside the checkout and any Git repository. Record your chosen root
privately and use **the same root on every restart**. Set this variable again in
each new terminal. A different empty root makes the app look new.

Databases initialize automatically; no manual SQL is needed. To import old
single-profile data, follow section 10 before creating the first profile.

## 2. Start the application

First check whether a server already exists:

```powershell
Invoke-RestMethod http://127.0.0.1:8085/api/health | ConvertTo-Json
```

Connection refused means nothing answers there. If healthy, use that server or
stop its existing launch before starting another.

### Normal background start

From the checkout, with the data-root variable set:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-background.ps1 -DataRoot $dataRoot
```

Wait for **CareerPulse is running**, then open <http://127.0.0.1:8085>.
Use 127.0.0.1 consistently in browser/API examples.

**Success:** health reports status healthy, db ok, and multi_profile true. A fresh
installation has candidate_count 0 and shows **Add a profile**. Host health does
not prove every candidate's AI or every source works.

You may close PowerShell and browser tabs afterward. Keep Windows awake, online
for discovery and Ollama running for local AI. Background mode is not a Windows
service: it does not install sign-in startup or restart after a crash, reboot or
sign-out. Run the start command again after reboot.

### Foreground diagnosis

Use instead of background mode, with port 8085 free:

```powershell
$env:CAREERPULSE_DATA_ROOT = $dataRoot
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8085
```

Keep that terminal open. Stop with Ctrl+C there. Python code changes require
server restart; browser refresh alone does not load them.

## 3. Set up your first profile

1. Enter a display name and click **Create profile**. Creation stays on Manage
   profiles; choose **Set up profile** to continue. **Cancel** clears an unsubmitted form.
2. Upload a **PDF, DOCX, TXT or MD** resume. Check extracted text is readable.
   Scanned PDFs may need conversion to selectable text. DOC/RTF are unsupported.
3. Review contact details, work history, education, skills, certifications and
   application answers. Correct extraction mistakes; suggestions are not verified facts.
4. Configure and save AI settings using an option below.
5. In **Job Search**, save search terms, target titles, locations, salary/rate
   preferences and sources. Start with a small focused search. Supply source-specific
   credentials when required by the UI.
6. Review sponsorship, work authorization, remote/hybrid/on-site requirements and
   relocation against the real listing. Unknown sponsorship needs review; it is not a promise.

**Success:** refresh and reopen Settings; resume, profile, AI and search terms
remain saved. **Finish setup later** closes onboarding; **Back to Manage profiles**
returns to selection. Reopen onboarding through **Settings > Data Management >
Launch Setup Guide**.

### Local AI with Ollama

Install/open Ollama using its [Windows guide](https://docs.ollama.com/windows).
CareerPulse does not start it. Check service and installed models:

```powershell
ollama list
Invoke-RestMethod http://localhost:11434/api/tags
```

If no model is installed, choose one suitable for your hardware and run
`ollama pull MODEL_NAME`, replacing the placeholder with an actual model tag.
A short `ollama run MODEL_NAME` conversation checks it loads; /bye exits that chat.

In CareerPulse select **Ollama (Local)**, choose the installed model, use
http://localhost:11434 and save. Installed models can still run out of memory or
produce invalid evidence; verify with a small job batch. Open the Ollama desktop
app if needed; use `ollama serve` only when no server is already listening.

### Cloud AI

Select a provider offered in Settings and save that candidate's key/model.
Account access, billing and rate limits belong to the provider. Cloud inference
sends required resume/job/form text to that provider. Ollama inference is local
when using your local server; scraping still accesses external job sites.

New profiles inherit no other candidate's resume, keys or environment credentials.
Bedrock in candidate mode requires explicit candidate credentials; shared AWS
environment credentials are not a fallback. Local secrets are not currently
stored in a Windows keyring.

## 4. Use the application

### Find and review jobs

1. Confirm the selected profile, then click **Scrape Now**.
2. Watch source results/phases: discovery, enrichment, location classification
   and scoring when AI is configured. Avoid duplicate runs.
3. Browse the feed. Check score, keyword, work-type, location, stale and dismissed
   filters if empty. Listings found and new jobs saved can differ due to deduplication.
4. Open a job. Verify employer destination, description, dates, pay, location,
   eligibility, match reasons, concerns and evidence quotes.
5. If blocked by a source, use other sources or save a listing with the extension.
   CAPTCHA/403 is a source issue, not proof the whole app failed.

Unscored differs from a zero score. Jobs may remain unscored if AI is unavailable
or evidence fails validation. Check status/logs before restarting scoring.

### Prepare, apply and track

1. Open a suitable job and use its application-preparation actions.
2. Review tailored resume/cover-letter facts against real candidate history.
3. Download available PDF/DOCX documents; open and inspect before attaching.
4. Open the employer application. Optional extension autofill assists with answers.
5. Review all answers/attachments before final submission. Confirm the employer's
   result; document preparation or autofill is not a completed application.
6. Check saved status and track in **Pipeline**. After moving a card, refresh to
   verify persistence. Mark applied only after actual submission.

| Area | How to use it |
| --- | --- |
| Multiple resumes | Save versions and check the version selected for preparation |
| Queue | Prepare/fill jobs and review each employer form before submission |
| Interviews and Calendar | Record rounds, dates and outcomes; verify time zones |
| Calendar subscription | Use iCal; keep its token-bearing URL private |
| Networking/contacts | Record contacts, interactions and linked jobs |
| Offers and salary tools | Compare entered terms/assumptions; estimates are not actual offer terms |
| Analytics/skill gaps | Review patterns; incomplete/stale history limits usefulness |
| Saved views and alerts | Save filters and configure alerts for the selected profile |
| Data export | UI CSV/profile exports are not full installation backups |
| Email settings | Optional: review sender, recipient and enabled digest/follow-up behavior. Test-send actions can send real email |

### Background work

Every registered profile gets schedules at server startup, even without a tab.
Multi-profile discovery checks run every six hours and scoring hourly. Sources
also have due-time rules; discovery requires saved search terms. Other tasks
include enrichment, maintenance, reminders, alerts, embeddings and digest checks,
subject to each profile's settings and available services.

Schedules are in-process, not durable workers. Sleep pauses processing and restart
can reset progress. Do not assume missed work replays immediately. Use **Scrape Now**
for an immediate run. Clearing jobs does not disable schedules.

## 5. Manage profiles and clear data

Every profile, including imported Primary profile, has **Rename** and **Delete
profile** at Manage profiles. Names are labels; IDs identify data. Duplicate
names are allowed, so distinct labels help avoid mistakes.

| Action | Effect |
| --- | --- |
| Rename | Changes label; keeps ID, URLs and data. Does not rename the person on a resume |
| Switch | Opens the profile; existing work keeps its original identity |
| Clear Jobs | Removes jobs, scores and associated application records; keeps resume/search/AI settings |
| Reset All | Clears database content/settings covered by reset; retains registry identity and directory. Not full profile deletion |
| Delete profile | Confirms exact current name; removes registry entry and private directory, including DB, browser data, pairing, artifacts and internal recovery |

Deletion refuses active tasks/requests. Close that profile's other tabs, wait for
work, then retry. Other profiles remain intact. Deleting the last profile returns
to empty setup. Backups outside its directory remain.

Check profile and backup needs before clearing/resetting. Wait for discovery/
scoring to finish first. Reset is not restart or erasure of external downloads,
browser state, logs and backups. Check Clear Jobs by refreshing feed/Pipeline and
checking zero stats in section 7. Stats are a UI summary; full erasure audits need
database/index inspection. Later discovery can add jobs again.

## 6. Install and pair the extension

1. Use a separate **Chrome browser profile per candidate**.
2. Open chrome://extensions, enable **Developer mode**, choose **Load unpacked**
   and select this checkout's extension folder.
3. Open the intended candidate, click **Pair browser extension**, copy the code.
4. In the extension popup, paste it and click **Pair this browser**. Check the name.
5. Verify the signed-in employer account belongs to the candidate. Pairing binds
   CareerPulse data, not employer account identity.
6. Use **Fill Application**; review answers, skipped fields and attachments before
   personally completing final submission.

**Success:** popup identifies the intended candidate and reaches their API.
Page-selector changes do not rebind extension/queue. Pairing is fixed for that
extension installation; use another Chrome profile for another candidate.
Never share pairing codes.

After extension updates, click **Reload** on its extension card and refresh
employer tabs. Recheck pairing. Deleted candidates' API/pairing is unavailable.

## 7. Check status and logs

### Installation

```powershell
Invoke-RestMethod http://127.0.0.1:8085/api/health | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8085/api/runtime/progress | ConvertTo-Json -Depth 6
```

Runtime progress covers all candidates' owned tasks and active write requests.
Check before stopping.

### Select a candidate explicitly

Run in each new terminal before using the candidate-base variable. Paste a listed ID:

```powershell
Invoke-RestMethod http://127.0.0.1:8085/api/candidates | Format-Table candidate_id, display_name
$candidateId = 'paste-the-candidate-id-here'
$candidateBase = "http://127.0.0.1:8085/api/candidates/$candidateId"
Invoke-RestMethod "$candidateBase/health" | ConvertTo-Json
Invoke-RestMethod "$candidateBase/scrape/progress" | ConvertTo-Json -Depth 6
Invoke-RestMethod "$candidateBase/score/progress" | ConvertTo-Json -Depth 6
Invoke-RestMethod "$candidateBase/stats" | ConvertTo-Json
```

| Check | Expected evidence |
| --- | --- |
| Candidate health | DB OK, scheduler running; configured AI reachable |
| Scrape | Phase/source changes and results accumulate |
| Scoring | Successful scored count increases, sometimes after a batch |
| Stats | Saved counts reflect workflow; some exclude dismissed jobs |
| Job details | Plausible reasons and source-grounded evidence |

Health does not guarantee sources or valid output. Inactive does not mean every
job is scored. Progress is in memory and may be null after restart; use saved jobs
and logs for history.

When idle, start work for the selected candidate only:

```powershell
Invoke-RestMethod -Method Post "$candidateBase/scrape"
# Use separately, after confirming scrape/score progress is inactive:
Invoke-RestMethod -Method Post "$candidateBase/score"
```

Requests may take time; avoid repeats and check progress in another terminal.
Manual scoring has a 30-minute limit; large backlogs may need multiple runs.
Acknowledgement is not completion. To cancel a manual scrape:

```powershell
Invoke-RestMethod -Method Post "$candidateBase/scrape/cancel"
```

Recheck progress. A 404 can mean no active manual scrape. No dedicated score-cancel
endpoint exists in this workflow.

### Logs

Foreground logs appear in the original terminal. Background logs are outside Git:

```powershell
$logRoot = Join-Path $env:LOCALAPPDATA 'CareerPulse\background'
Get-ChildItem -LiteralPath $logRoot | Sort-Object LastWriteTime -Descending
$launch = Get-Content -LiteralPath (Join-Path $logRoot 'process.json') -Raw | ConvertFrom-Json
Get-Content -LiteralPath $launch.stderr -Tail 80
Get-Content -LiteralPath $launch.stdout -Tail 40
```

INFO can appear in the error log. Add -Wait to follow lines; Ctrl+C then stops log
viewing, not the server. Match timestamps and candidate IDs.

## 8. Stop, restart and update

### Stop and restart

Check all-profile runtime progress. Once inactive:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-background.ps1
Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue
```

**Success:** script reports stopped; listener check has no output. The script
checks the recorded process and refuses active work. It terminates that process,
not a graceful shutdown API. It manages background-script launches only.
Stop foreground launches with Ctrl+C in their original terminal and wait.

Restart using section 2 with -MultiProfile and the same root. Refresh/check health.
Normal restart preserves profiles and jobs.

### Update

Stop and make a full backup (section 9). Inspect first:

```powershell
git status --short
git branch --show-current
git remote -v
```

If not clean, preserve intended work in a commit or separate branch first. Do not
reset/delete changes to make updates proceed. For a clean checkout on your fork:

```powershell
git switch main
git pull --ff-only origin main
uv sync --locked --python 3.13 --extra playwright
.\.venv\Scripts\python.exe -m playwright install chromium
```

To integrate newer maintained-fork changes, with upstream configured as in section 1:

```powershell
git fetch upstream
git log --oneline main..upstream/main
git merge --ff-only upstream/main
```

A fast-forward refusal means divergent histories: stop and resolve deliberately;
do not force-push/discard work. After integrating upstream, rerun dependency sync
and browser installation. Publish reviewed updates to your fork with
`git push origin main` when intended.

Restart on the same root. Startup applies DB migrations; verify health, profile/
resume and representative jobs. Hard-refresh with Ctrl+F5 and reload changed
extension code. Older code may not understand upgraded DBs: preserve pre-upgrade
code and restore a pre-upgrade copy together for rollback.

## 9. Back up and recover

| Location | Contents |
| --- | --- |
| Checkout | Code, tests and docs |
| Data root / installation.db | Registry and profile labels |
| Data root / candidates / ID / candidate.db | Profile, resume text, settings, jobs/applications |
| Candidate artifacts/browser/cache/recovery folders | Private files, sessions/pairing, cache and migration recovery |
| LOCALAPPDATA / CareerPulse / background | Launch record/logs |
| Your download folders | Exported documents outside managed profile storage |

Keep private data outside Git. Isolation serves a trusted local operator, not
separate Windows-user authentication. Keep binding 127.0.0.1; shared/network
deployment needs a separate security design.

### Full backup

Stop and verify no listener (section 8). No other process should write the root.
A stopped folder copy retains registry, databases, SQLite sidecars, sessions and
artifacts together. Set the data-root variable to your actual startup root:

```powershell
$dataRoot = Join-Path $env:USERPROFILE 'Documents\Codex\CareerPulseData'
$backupParent = Join-Path $env:LOCALAPPDATA 'CareerPulse\backups'
New-Item -ItemType Directory -Path $backupParent -Force | Out-Null
$backupPath = Join-Path $backupParent ('installation-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
if (-not (Test-Path -LiteralPath (Join-Path $dataRoot 'installation.db'))) { throw 'Check the root first' }
if (Test-Path -LiteralPath $backupPath) { throw 'Choose a new destination' }
Copy-Item -LiteralPath $dataRoot -Destination $backupPath -Recurse -Force -ErrorAction Stop
Get-Item -LiteralPath (Join-Path $backupPath 'installation.db')
Get-ChildItem -LiteralPath (Join-Path $backupPath 'candidates') -ErrorAction SilentlyContinue
```

**Success:** copy completes, backup registry exists and expected candidate folders
are present. Keep destination outside source root and Git. Backups contain private
credentials/sessions. Rehearse recovery periodically; file presence alone is limited.

For a database-only live snapshot, after setting candidate ID in section 7:

```powershell
$candidateDb = Join-Path $dataRoot "candidates\$candidateId\candidate.db"
.\.venv\Scripts\python.exe -m app.candidates --data-root $dataRoot backup $candidateDb
if ($LASTEXITCODE -ne 0) { throw 'Database backup failed' }
```

The CLI uses SQLite online backup and integrity checking, printing a unique path
under the root's backups folder. Its filename uses legacy- even for candidate DBs.
It does not copy registry/artifacts. Do not copy only a live DB: committed data
may be in the WAL sidecar. CSV/profile JSON is not a full backup.

### Restore to a new root

Stop current server. Keep the original root and select an unused external
destination. Replace example paths; do not overwrite live data:

```powershell
$backupPath = 'C:\Private\Backups\installation-REPLACE-WITH-YOUR-BACKUP'
$restoreRoot = 'C:\Private\CareerPulseRestored'
if (Test-Path -LiteralPath $restoreRoot) { throw 'Restore destination must be new' }
Copy-Item -LiteralPath $backupPath -Destination $restoreRoot -Recurse -Force -ErrorAction Stop
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-background.ps1 -MultiProfile -DataRoot $restoreRoot
```

The restored server starts schedules. Verify health, profile names, resume/settings
and representative jobs/applications. For permanent recovery, record the restored
root for future starts. For a drill, stop it and restart the original root.
Keep backup until verification succeeds.

The restore-copy CLI in [STORAGE.md](docs/implementation/STORAGE.md) restores an
original migration snapshot, not an arbitrary current installation backup.
It is not a general live restore button.

## 10. Migrate a legacy installation

Skip for fresh installations or already-imported profiles. Migration requires an
**empty registry**; do not create a blank profile first or repeat import.
Stop the legacy server after work is inactive, choose your external root, and
point the legacy DB variable at the actual old file:

```powershell
$legacyDb = Join-Path (Get-Location).Path 'data\jobfinder.db'
$backupPath = & .\.venv\Scripts\python.exe -m app.candidates --data-root $dataRoot backup $legacyDb
if ($LASTEXITCODE -ne 0) { throw 'Backup failed' }
& .\.venv\Scripts\python.exe -m app.candidates --data-root $dataRoot migrate-copy $backupPath 'Primary profile'
if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
```

Start multi-profile mode on that root and verify settings, resume, records/counts.
The legacy DB stays unchanged. SQLite material is copied; external sessions and
environment-only credentials are not. See --artifact in
[STORAGE.md](docs/implementation/STORAGE.md) for selected external files.
Post-cutover changes exist only in the candidate DB.

Legacy mode is no longer a normal runtime. Keep a legacy backup only for migration
or recovery; production startup always uses the profile registry and candidate APIs.

### Docker and other platforms

Compose uses a named volume mounted at the external multi-profile data root.
Dockerfile omits optional browser installation, so browser-dependent scrapers may
need an image with the browser dependencies installed.

## 11. Troubleshooting and support

| Symptom | Check and next action |
| --- | --- |
| git/uv/ollama not recognized | Finish install, open new terminal, check version/path |
| Missing environment/imports | Run locked sync from checkout; stop if installation fails |
| uv download fails with UnknownIssuer | On machines using an organization-installed certificate, retry with uv's --system-certs option. Use the trusted Windows certificate store; do not disable certificate verification |
| Scripts blocked by policy | Use the shown process-scoped PowerShell Bypass invocation |
| Browser executable missing | Install Playwright extra and Chromium; smoke specifically needs Chrome |
| Port occupied | Check health/process; use or stop that launch before another |
| Access denied stopping | Use original terminal/account/elevation; never kill all Python processes |
| No launch record | May be foreground; use original terminal |
| Stop/delete busy | Check runtime and wait; close profile tabs for deletion |
| Startup timeout | Read launch error log/listener; process may still start |
| Profiles missing | Verify mode and exact root before replacement creation/migration |
| Wizard returns | Check saved Settings/resume/health; browser state is not proof of loss |
| Rename/delete absent | Hard-refresh Manage profiles; confirm update/restart Python APIs |
| Candidate 404/409 | Check ID/URL. Deleted is unavailable; missing storage needs recovery |
| Ollama unreachable | Open Ollama; check tags, saved URL/model and running server |
| AI responds but scoring fails | Check readable job/resume and evidence errors; connectivity is not validity |
| Scoring stops early | Check timeout, rejected evidence/logs before another backlog run |
| CAPTCHA/403/429/zero results | Inspect source outcomes, respect rate limits, use other/manual sources |
| Feed empty | Check profile/terms/filters/stale/dismissed state and stats |
| Jobs return after clearing | Discovery can add them; clearing does not disable schedules |
| Pipeline move missing | Check errors, refresh, confirm profile before repeating |
| Wrong person's autofill | Stop; check pairing, Chrome profile and employer account |
| Extension fails after update | Reload extension, refresh tabs, check server/pairing |
| Browser shutdown stalls | Allow cleanup/read logs; prefer stopping idle |
| Git fast-forward refused | Preserve work and resolve history; do not force/reset away changes |

Identify the listener without stopping anything:

```powershell
Get-NetTCPConnection -LocalPort 8085 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, OwningProcess
```

For support include attempted action, expected/actual result, time/time zone,
Windows/Python versions, git log -1 --oneline, startup mode, whether root is custom,
sanitized health/progress and timestamped logs. Include repeatable steps/exact
errors. Remove personal data, keys, pairing/calendar tokens and application answers.
Do not attach private databases/backups to public issues.

## 12. Contributor checks and documentation

Default uv development group installs backend test dependencies. Select checks
appropriate to the change:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_multi_profile.py tests/test_candidate_runtime.py tests/test_candidates.py -q
# Full backend regression when warranted:
.\.venv\Scripts\python.exe -m pytest -q
```

With Node.js/npm installed (CI uses Node 20), install pnpm if needed and check:

```powershell
node --version
npm --version
npm install -g pnpm
pnpm --version
```

Then use the CI lockfile workflow:

```powershell
Push-Location app/static
pnpm install --frozen-lockfile
pnpm exec vitest run
Pop-Location
Push-Location extension
pnpm install --frozen-lockfile
pnpm exec vitest run
Pop-Location
```

With Chrome and the Playwright extra installed:

```powershell
.\.venv\Scripts\python.exe scripts/verify-multi-profile.py
```

This uses synthetic candidates, temporary storage and a free port. It checks
creation, rename persistence, deletion/cancel, isolation, onboarding, pipeline
persistence and dashboard, then prints a screenshot path. It does not delete real
profiles. Passing tests do not prove every external source works.

### Keep this guide current

Changes to setup, dependencies, config, UI workflows, APIs, storage, schedules,
pairing, recovery or common errors must update the relevant runbook section in
the same change. Keep README's entry point aligned. This expectation also lives
in [AGENTS.md](AGENTS.md) for future coding sessions.

Write for new members: prerequisites, working directory, exact commands, expected
success and next action on failure. Use placeholders, not personal paths/IDs.
Separate normal operation from recovery/legacy. Verify examples against code,
check links and distinguish tested behavior from pending work. Update the review
date when checked; claim fresh-machine testing only when performed.
