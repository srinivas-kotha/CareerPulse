# Discovery and scoring recovery - 2026-09-15

Branch: `feature/profile-isolation-hardening`. This update builds on `07931c4`.
Use `git log -1` for the resulting local check-in; a commit does not imply a push.

## Implemented

- Hacker News headers identify roles by their contents instead of assuming a
  fixed company/role/location order. New posts preserve complete descriptions and
  source timestamps. Ambiguous titles are retained for review.
- Discovery audits flag missing/malformed titles, insufficient descriptions and
  invalid URLs. Source-backed header repairs retain jobs and application records.
- URL identity strips known tracking parameters while preserving requisition
  parameters and path case. Indexed identity lookup avoids repeated full scans.
  Identical cross-source copies may share a primary record; fuzzy title similarity
  alone no longer automatically dismisses an opening. Historical duplicates remain
  stored and link to their primary record.
- Job feeds exclude quality reviews, known duplicates and confirmed closed
  listings by default. **Include quality review, duplicates and closed listings**
  reveals them; job details and pipeline history remain accessible.
- Candidate-scoped availability checks inspect public URLs, validate redirect
  destinations, cap response size/time and inspect matching JobPosting metadata.
  HTTP 404/410 or explicit closure evidence can establish closure. A CAPTCHA,
  HTTP 403/429, network failure, or generic HTTP 200 page remains unknown.
  Alternate known listing URLs are checked before declaring the opening closed.
- The dashboard exposes listing-review, duplicate, closure, scoring-ready,
  cooldown and scoring-review counts. Checks and failure state persist after
  reload/restart. Progress for a currently running batch remains in memory.
- Strict scoring uses source excerpt IDs, copied back to source text before the
  existing quote validation. Ollama receives a schema with bounded category values
  and response strings. High scores require two distinct excerpts from each source.
  No invalid response is converted into a zero score. Explicit eligibility zeroes
  survive **Rescore Failed**.
  The local provider integration follows [Ollama structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs).
- Job-local failures continue to later jobs and persist retry eligibility with
  exponential cooldown (15 minutes up to 24 hours). Three invalid-response attempts
  require review. Three consecutive provider failures stop a run. A manual retry
  resets failure state without clearing a valid score; manual scoring can be cancelled.
- Async dashboard responses cannot overwrite a page after navigation away.

## Live evidence

The existing private root was backed up with SQLite online backup and integrity
checks before migration/restart. No candidate facts, credentials or database files
are part of the check-in.

- Audit: 2,427 active listings inspected, 4 headers repaired, 77 quality reviews,
  and 6 historical duplicates identified. Existing records were preserved.
- First bounded scoring run: 3/3 saved. An intermediate 100-job run saved 52
  before an intentional backed-up restart for prompt refinements. It is not a
  completed 100-job result.
- Refined bounded run: 10/10 saved with zero failures.
- Background scheduled recovery: 1,085/1,090 saved; five responses needed another
  pass. Truncated output is now classified as a job-local model response failure.
- Revalidation inspected the 1,150 scores generated during this task. Two early
  high scores reused a source passage; their backed-up scores were requeued for
  the stronger diversity check. Older pre-task scores were retained.
- First ten listing availability checks: five matching listings, two closed
  URLs, three unknown results. This is a sample, not every source's acceptance.
- Background host health, candidate DB, scheduler and local Ollama were healthy.

Final recovery pass: **7/7 saved, zero failures**, including the five remaining
failures and the two revalidated early scores. The resulting snapshot has **2,383
total scores, 0 ready jobs, 0 cooldown jobs and 0 scoring reviews**. Net increase:
**1,155 scores**. The **48 retained unscored records** comprise **42 quality reviews
and 6 duplicates**. These are explicitly held out rather than given artificial
scores. Both closed listings were rechecked across their known URLs (HTTP 410).

Backup comparison verified all **3,061 original job IDs**, all **1,228 original
scores with their contents**, applications and profile/resume facts were preserved.

Browser checks passed for the live dashboard and reload, and for synthetic audit,
review filtering, availability actions, persisted results and navigation. The
existing multi-profile browser regression also passed. Final suite totals are
recorded in the check-in verification section below.

## Check-in verification

- Full backend: **791 passed in 410.32 seconds**.
- Focused discovery/runtime/scoring checks after the final audit guard: **74 passed**.
- Frontend: **191 passed**, 13 files.
- Multi-profile browser regression: passed.
- New discovery browser regression: passed, including audit/filter controls,
  availability action, database persistence and reload; no JavaScript errors.
- Read-only live dashboard/reload: passed again after the final background restart;
  the screenshot was visually inspected outside Git.
- Changed Markdown file links and Git whitespace checks: passed.
- Read-only validation of all **1,058 new model-generated scores** passed the final
  category, source-quote and evidence-diversity checks. The other **97 new scores**
  are deterministic sponsorship exclusions rather than model outputs.
- Fresh-machine installation, all-source liveness, the 30-case semantic-quality
  benchmark and complete assisted submission were not tested in this slice.

## Verification commands

From the checkout, with prerequisites from [RUNBOOK.md](../../RUNBOOK.md):

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short
Push-Location app/static
corepack pnpm exec vitest run
Pop-Location
.\.venv\Scripts\python.exe scripts/verify-multi-profile.py
.\.venv\Scripts\python.exe scripts/verify-discovery-ui.py
```

The discovery browser regression uses a temporary synthetic profile. It exercises
audit controls, feed filtering, a mocked closed listing, persistence after reload,
database readback and navigation without JavaScript errors. For a read-only live
dashboard check, provide your candidate ID:

```powershell
.\.venv\Scripts\python.exe scripts/verify-discovery-ui.py --base-url http://127.0.0.1:8085 --candidate YOUR-CANDIDATE-UUID
```

Screenshots are written to the OS temporary directory, outside Git.

## Remaining release acceptance

T03 still includes expanded source coverage, source snapshots/aliases, incremental
discovery and broader liveness verification. A reachable source does not prove
that every advertised opening is available. Similar but non-identical postings
are intentionally not automatically merged.

T04 still includes the separate 30-case model-quality benchmark, independent
material review, versioned artifacts/caches and visual document acceptance.
Literal evidence and a valid schema do not prove every model interpretation is
correct. The current audit does not revalidate pre-task scores against a new rubric.

The complete assisted application workflow, portable exports/keyring, durable
worker history/recovery, budgets, Gmail and audited automatic submissions remain
separate pending milestones. No real application was submitted during this work.
