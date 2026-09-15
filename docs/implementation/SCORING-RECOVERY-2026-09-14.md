# Historical scoring recovery checkpoint - 2026-09-14

Superseded by [DISCOVERY-RECOVERY-2026-09-15.md](DISCOVERY-RECOVERY-2026-09-15.md). The ready backlog recovered on September 15; the findings below are historical.

Local check-in on `feature/profile-isolation-hardening`, based on `c15a807`.
Use `git log -1` for the resulting commit. No push or PR is included.

## Implemented and tested before the environment block

- Candidate-scoped `POST /score?limit=N` accepts 1-10000 jobs; default unchanged.
- Duplicate manual launches return 409, including before the worker acquires its lock.
- Per-job progress reports attempted, saved and failed counts, terminal status,
  sanitized error classification and stop reason. Three consecutive failures stop
  a run; existing scores and failed/unattempted jobs remain intact.
- Missing configuration and empty runs replace stale progress. Cancellation and
  unexpected failure report an incomplete outcome.
- Dashboard completion no longer claims every finished run scored the backlog;
  empty/skipped runs stop polling too.
- Tests on September 13: 31 passed across candidate runtime, multi-profile and
  matcher tests; all 191 frontend tests passed. No full backend rerun performed.
- Private online registry/candidate backups passed integrity checks before the
  idle server restart. The app restarted successfully on the same external root.
- The operator explicitly confirmed restoration of the existing profile's saved
  pay minimums; API readback verified them. No candidate facts were added to Git.

## Real verification and findings

- Initial saved-data inspection: 2370 jobs, 1228 scores, 641 active classified
  unscored jobs, zero active unclassified jobs. Counts are a dated snapshot.
- The bounded three-job run saved zero scores. Logs show invalid category ranges
  and non-contiguous evidence even after the existing correction retry.
- September 14 read-only health was healthy and idle. Later discovery had added
  jobs; the most recent progress was stopped, 0/1174, three attempted/failed,
  `invalid_model_response`. This is separate from the original bounded run.
- A local Ollama diagnostic reproduced negative logistics points and a quote
  assembled from separate listing phrases. A further prompt reminder still
  produced invented/short quotes. Neither diagnostic wrote scores to the DB.
- Some early backlog titles are malformed; source quality and model validation
  are separate issues. Repeated scheduling currently revisits the same failures.
- Dashboard UI showed the bounded run active on September 13. On September 14,
  the Chrome connection detached before preparation/tracking could be verified.
  No application was prepared, marked applied, or submitted during this slice.

## Current blockers and next work

Windows Application Control blocked `.venv/Scripts/python.exe` earlier on
September 14. During this check-in the same executable successfully ran the
focused backend suite; no policy changes were made. If the block recurs, obtain
normal Windows/admin review. The existing server was left running.

1. Reconnect the browser before live workflow verification.
2. Repair structured model output and evidence generation without relaxing
   validation. Consider constrained category values and source-bound excerpt
   selection; evaluate with real failure cases and the retained 30-case benchmark.
3. Add tested per-job retry/review handling so malformed responses do not repeatedly
   block later jobs. Do not convert failures into zero fit scores or delete jobs.
4. Verify a bounded real run against saved records, then broaden recovery only
   after inspecting its outcome. Validate shortlist facts and source liveness.
5. Demonstrate prepare and track in the actual UI, including reload and database
   readback. Final submission needs explicit approval; a link click is not proof.
6. Run broader backend and live acceptance checks as the recovery implementation
   advances; the focused check-in suite below does not establish release acceptance.

Durable run history, restart recovery, full backlog recovery, artifact factual and
visual acceptance, and the complete assisted workflow are still pending. Progress
in this slice is in memory. No push or PR was performed.

## September 14 check-in verification

- Backend: **74 passed** using the command below.
- Frontend: **191 passed** across 13 files using the command below.
- No full backend rerun, live scoring, browser verification or server restart
  was performed for this check-in. Earlier live observations above are historical.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_candidate_runtime.py tests/test_multi_profile.py tests/test_matcher.py tests/test_matcher_extended.py tests/test_matcher_eligibility.py tests/test_scoring_failures.py tests/test_scoring_reset.py -q --tb=short
Push-Location app/static
corepack pnpm exec vitest run
Pop-Location
```
