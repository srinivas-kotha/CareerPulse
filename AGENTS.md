# Repository maintenance

Keep RUNBOOK.md usable by a new member starting from a fork. Whenever a change
affects installation, dependencies, startup/shutdown, configuration, user workflows,
profile management, APIs used in the guide, storage, scheduling, browser pairing,
backup/recovery, or troubleshooting, update the relevant runbook instructions in
the same change. Keep the README entry point consistent.

Include prerequisites, copy/paste commands with generic paths, expected success,
and useful failure/recovery guidance. Verify examples against the implementation.
Distinguish tested workflows from limitations; do not claim unperformed tests.
Keep private candidate data, credentials, sessions, logs and backups outside Git.
Documentation-only changes need link/example checks, not application regression
tests unless executable behavior also changes.
