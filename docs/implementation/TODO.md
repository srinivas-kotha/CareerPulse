# Current execution queue - 2026-09-13

The PRD remains accepted; full acceptance is pending. See
[REVIEW-2026-09-10.md](REVIEW-2026-09-10.md) for the complete pending inventory,
code findings and PRD coverage. [TASKS.md](TASKS.md) is the detailed checklist;
[CONTINUE-HERE.md](CONTINUE-HERE.md) is the handoff. Old checkpoints are history.

| Milestone | Current status | Next acceptance work |
| --- | --- | --- |
| T00 baseline | Complete, recorded evidence | Preserve evidence and final release checks |
| T01 isolation | Integrated; broader acceptance partial | Keyring, portable export/import, version updates and recovery coverage |
| T02 onboarding/eligibility | Candidate rules and hard-gate repair implemented | Full geographic/authorization interpretation, original-file provenance, immutable profile history and sourced sponsorship data |
| T03 discovery | Existing adapters; acceptance partial | JobSpy/ATS coverage, snapshots/aliases, incremental windows, duplicates, liveness and health |
| T04 matching/materials | Existing implementation; acceptance partial | Scoring recovery, 30-case benchmark, reviewer, versioned caches/artifacts and visual QA |
| T05 assisted release | UI implemented; acceptance pending | Real complete assisted workflow, evidence distinctions, persisted progress and shortfall reporting |
| T06 durable runtime/budgets | In-process foundation only | Durable tasks/recovery, fairness, budgets and Windows sign-in/catch-up |
| T07 Gmail/history | Pending | OAuth, import, cursors, evidence and reconciliation |
| T08 automatic applications | Pending | Complete preflight, tested adapters, immutable audit and independent confirmation |
| T09 expanded features | Existing upstream tools; PRD acceptance partial | Source validation, evidence, reviewed outreach, integrations and observed analytics |
| T10 packaging/release | Scripts/runbook partial | Fresh-install/upgrade drills, automation, audits, final checks and fork PR |

## Next steps

1. Inspect Git and read-only installation health/runtime progress using
   [RUNBOOK.md](../../RUNBOOK.md#7-check-status-and-logs). Select candidate URLs
   explicitly. Preserve existing data; do not repeat completed migration.
2. Confirm eligibility rules independently in each profile via Settings > Job
   Search. The shared constants and override bypass are repaired; retain broader
   T02 acceptance and immutable history work. See PROFILE-ISOLATION-PLAN.md.
3. Diagnose scoring using saved records and sanitized errors, then a bounded local
   run. Review observed 0/600 counters without assuming the cause or backlog size.
4. Complete remaining T01 security/portability and T03 discovery acceptance;
   benchmark T04 and validate factual artifacts. Preserve upstream working tools.
5. Demonstrate T05 in the actual UI, including preparation and tracking. Real
   final submissions require explicit approval; extension activity is not proof.
6. Continue T06-T10 with dependencies in TASKS.md. Do not mark durability, Gmail,
   budgets or automatic applications complete from in-process background operation.
7. Run checks appropriate to each change, update evidence and this queue, and
   prepare reviewable commits. Check Git for the actual branch/commit; do not
   infer a remote push or PR from local work.

## Verification status

Current verification is recorded in [PROFILE-ISOLATION-PLAN.md](PROFILE-ISOLATION-PLAN.md).
The 2026-09-10 live 0/600 scoring result was traced to rejected model evidence;
full live backlog recovery remains pending. Synthetic local scoring is a separate,
limited check. Existing 30-case quality, real-site submission, native Word layout
and fresh-machine installation acceptance remain open.

Use the runbook's contributor commands for tests and its start/stop commands for
operation. The launcher accepts `-DataRoot`; it has no `-MultiProfile` parameter.
