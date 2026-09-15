# Current execution queue - 2026-09-15

Latest slice: [DISCOVERY-RECOVERY-2026-09-15.md](DISCOVERY-RECOVERY-2026-09-15.md).

- [x] Improve discovery quality, conservative duplicate handling and listing
  availability checks; verify the controls and persisted results in the browser.
- [x] Repair malformed scoring output without relaxing evidence validation and
  verify recovery of the ready backlog. Net 1,155 new scores were saved; the final
  ready/cooldown/scoring-review counts are zero. The 48 remaining unscored records
  are 42 listing-quality reviews and 6 duplicates, retained for inspection.
- [x] Run the application in the background with the existing external data root;
  verify installation, candidate DB, scheduler and Ollama health.

These complete the requested discovery/recovery slice, not every T03/T04 release
criterion. All 3,061 original job IDs, 1,228 pre-task scores, application records
and profile/resume facts were verified preserved. See the evidence ledger for
checks, limitations and the local commit status.

The PRD remains accepted; full acceptance is pending. See
[REVIEW-2026-09-10.md](REVIEW-2026-09-10.md) for the complete pending inventory,
code findings and PRD coverage. [TASKS.md](TASKS.md) is the detailed checklist;
[CONTINUE-HERE.md](CONTINUE-HERE.md) is the handoff. Old checkpoints are history.

| Milestone | Current status | Next acceptance work |
| --- | --- | --- |
| T00 baseline | Complete, recorded evidence | Preserve evidence and final release checks |
| T01 isolation | Integrated; broader acceptance partial | Keyring, portable export/import, version updates and recovery coverage |
| T02 onboarding/eligibility | Candidate rules and hard-gate repair implemented | Full geographic/authorization interpretation, original-file provenance, immutable profile history and sourced sponsorship data |
| T03 discovery | Quality audit, strict deduplication and availability checks verified | Expanded JobSpy/ATS coverage, snapshots/aliases, incremental discovery and broader source acceptance |
| T04 matching/materials | Ready-backlog recovery verified; broader acceptance partial | 30-case quality benchmark, independent reviewer, versioned caches/artifacts and visual QA |
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
3. Review the retained listing-quality cases and duplicates via the dashboard.
   Keep invalid model responses unscored; use the persisted retry controls for new
   failures. The old 0/600 checkpoint is historical, not the current queue.
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

Current discovery/scoring verification is recorded in [DISCOVERY-RECOVERY-2026-09-15.md](DISCOVERY-RECOVERY-2026-09-15.md).
The old model-validation blockage is repaired and the ready backlog recovered.
The separate 30-case quality benchmark, full assisted workflow, real-site submission,
native Word layout and fresh-machine installation acceptance remain open.

Use the runbook's contributor commands for tests and its start/stop commands for
operation. The launcher accepts `-DataRoot`; it has no `-MultiProfile` parameter.
