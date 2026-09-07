# Next execution steps

The PRD and implementation plan remain accepted. This is their execution queue,
not a replacement plan. TASKS.md retains the full backlog and test evidence.

## Current implementation status

| Milestone | Status | Remaining acceptance work |
| --- | --- | --- |
| T00 setup/baseline | In progress; baseline tests pass | Finish remaining architecture/browser dependency audit and check-in |
| T01 candidate isolation | Storage, copy migration and runtime helpers tested | Production router/worker integration, scoped frontend, pairing, credentials, cutover, export/import |
| T02 onboarding/eligibility | Pending | Evidence-linked facts, policy versions, deterministic hard rules and review |
| T03 discovery | Existing adapters smoke-tested selectively | JobSpy/direct ATS coverage, source health, snapshots, aliases, deduplication and liveness |
| T04 matching/materials | Upstream fixes and synthetic smoke tests pass | 30-case evaluation, evidence/reviewer validation, caching and immutable artifacts |
| T05 assisted release | Pending | Demonstrable candidate-aware discover/review/prepare/apply-link/track flow |
| T06 durable runtime/budgets | Pending | Persisted runs, leases, retries, recovery, scheduling, caps and Windows startup |
| T07 history/Gmail | Pending | Read-only OAuth, historical import, cursors and evidence reconciliation |
| T08 automatic applications | Pending | Tested adapters, preflight gates, exact audit and confirmed outcomes |
| T09 expanded features | Pending under new design | Additional sources/ATS, research, outreach drafts, notifications, Notion, analytics |
| T10 packaging/release | Pending | Windows scripts, upgrades, docs, license/privacy audit, final checks and fork PR |

## Step-by-step continuation

1. Read CONTINUE-HERE.md, PRD.md, IMPLEMENTATION-PLAN.md, TASKS.md, STORAGE.md and
   repository instructions. Inspect Git status and current branch. Preserve all
   uncommitted work. Do not infer completion from an unchecked or stale summary.
2. Recheck the local API, listener, active scrape/scoring work and actual DB path.
   The live single-candidate app has accumulated jobs; do not reset it. Back up
   with the SQLite backup CLI before any migration or deployment-related data work.
3. Resolve loading the latest backend fixes: inspect the owning server process,
   stop it gracefully only when its ownership and restart command are known, and
   restart on loopback with the same DB. Never kill every Python process. If the
   original process cannot be controlled, explain the concrete blocker. Merely
   refreshing Chrome does not update the Python process.
4. Address the observed setup gap: legacy resume text is saved, but the named
   resume list and derived search configuration were empty at review. Reconcile
   these paths without duplicate data; handle failed analysis honestly. Preserve
   facts and obtain missing preferences from the operator rather than inventing
   them. Review onboarding's 2/3 status and separate Save buttons.
5. Diagnose the scoring backlog using bounded runs and visible progress. Verify
   the latest Qwen final-answer fix is loaded. Do not launch another broad scrape
   merely to hide stalled scoring. Use only local AI unless paid use is authorized.
6. Complete T01 as an integrated slice: candidate-scoped requests and worker
   ownership, API wrapper/download/SSE routing, state separation, browser/extension
   pairing, then a visible profile switcher. Legacy unscoped extension calls must
   fail closed in multi-candidate mode. Test concurrent profiles and switches
   during generation. Do not expose a switcher over the legacy shared state.
7. Test older-schema startup migration, explicit external artifact references,
   credential protection, live cutover/rollback and secret-free export/import.
8. Proceed through T02-T05: reviewed onboarding and hard eligibility, validated
   sources/deduplication/liveness, calibrated matching and factual materials,
   then demonstrate the assisted workflow in the actual UI. Show what is saved,
   which action to take next, and why any job/task is blocked.
9. Retain T06-T10 and all mandatory regression cases. Do not enable automatic
   submissions before their gates or treat an extension click as acceptance.
10. Run checks appropriate to the changes, inspect actual UI/document output,
    update evidence and this queue, and make reviewable commits to the feature
    branch. A remote push/PR is not implied by a local check-in.

## Existing verification, not a new run

- Backend: 690 passed; collected before one additional ownership test.
- Subsequent runtime/DOCX checks: 18 passed, including all nine runtime tests.
- Frontend: 180 passed. Extension: 469 passed.
- Live selected source and synthetic Ollama checks are in TASKS.md.
- Native Word layout, real-site autofill, comprehensive model evaluation and
  end-to-end multi-candidate operation remain unverified.

## Commands

Run from the checkout in PowerShell:

```powershell
& 'C:/Program Files/Git/cmd/git.exe' status --short
.\.venv\Scripts\python.exe -m app.candidates backup data/jobfinder.db
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8085
```

The server command is for after confirming the port is free and the working
directory/database match the existing installation. Frontend and extension tests
use `corepack pnpm exec vitest run` from app/static and extension respectively;
Node/Corepack are under `C:/Program Files/nodejs` if absent from PATH.
