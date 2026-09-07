"""Installation storage foundation; never resolves an ambient current candidate.

The legacy application is not routed through this registry yet. Creating a
candidate here cannot change the running application's identity or database.
"""

import argparse
import asyncio
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4

from app.database import Database


def external_data_root(value: str | Path | None = None) -> Path:
    root = Path(value or os.environ.get("CAREERPULSE_DATA_ROOT") or
                Path.home() / "Documents" / "Codex" / "CareerPulseData")
    root = root.expanduser().resolve()
    checkout = Path(__file__).resolve().parents[1]
    if root == checkout or checkout in root.parents:
        raise ValueError("Candidate storage must be outside the checkout")
    if any((parent / ".git").exists() for parent in (root, *root.parents)):
        raise ValueError("Candidate storage must be outside Git repositories")
    return root


def backup_database(source: Path, destination: Path) -> Path:
    """Snapshot committed WAL data without modifying or replacing the source."""
    source, destination = source.resolve(), destination.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents overwriting an earlier recovery point.
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


@dataclass(frozen=True)
class CandidateRecord:
    candidate_id: str
    display_name: str
    directory: Path
    profile_version: int
    policy_version: int
    submission_mode: str

    @property
    def db_path(self) -> Path:
        return self.directory / "candidate.db"


@dataclass(frozen=True)
class CandidateContext:
    candidate: CandidateRecord
    db: Database
    bg_db: Database


class CandidateRegistry:
    def __init__(self, root: str | Path | None = None):
        self.root = external_data_root(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "installation.db"
        with closing(self._connect()) as conn, conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                profile_version INTEGER NOT NULL DEFAULT 1,
                policy_version INTEGER NOT NULL DEFAULT 1,
                submission_mode TEXT NOT NULL DEFAULT 'review'
                    CHECK(submission_mode IN ('review', 'links', 'automatic')),
                created_at TEXT NOT NULL
            )""")

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _record(self, row) -> CandidateRecord:
        candidate_id = row["candidate_id"]
        if str(UUID(candidate_id)) != candidate_id:
            raise ValueError("Invalid candidate ID")
        directory = (self.root / "candidates" / candidate_id).resolve()
        if self.root not in directory.parents:
            raise ValueError("Candidate directory escapes data root")
        return CandidateRecord(candidate_id, row["display_name"], directory,
                               row["profile_version"], row["policy_version"],
                               row["submission_mode"])

    def list(self) -> list[CandidateRecord]:
        with closing(self._connect()) as conn:
            return [self._record(row) for row in conn.execute(
                "SELECT * FROM candidates ORDER BY created_at, candidate_id")]

    def get(self, candidate_id: str) -> CandidateRecord:
        # Reject aliases and paths; do not create a missing candidate on lookup.
        try:
            valid = str(UUID(candidate_id)) == candidate_id
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise KeyError(candidate_id)
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM candidates WHERE candidate_id = ?",
                               (candidate_id,)).fetchone()
        if row is None:
            raise KeyError(candidate_id)
        return self._record(row)

    async def create(self, display_name: str) -> CandidateRecord:
        display_name = display_name.strip()
        if not display_name or len(display_name) > 120:
            raise ValueError("Display name must contain 1 to 120 characters")
        candidate_id = str(uuid4())
        directory = (self.root / "candidates" / candidate_id).resolve()
        if self.root not in directory.parents:
            raise ValueError("Candidate directory escapes data root")
        directory.mkdir(parents=True, exist_ok=False)
        for name in ("artifacts", "browser", "cache"):
            (directory / name).mkdir()
        database = Database(str(directory / "candidate.db"))
        try:
            await database.init()
        finally:
            await database.close()
        # Publish only after initialization. Failed creation never lists a
        # partial candidate and never copies credentials from another profile.
        with closing(self._connect()) as conn, conn:
            conn.execute("""INSERT INTO candidates
                (candidate_id, display_name, created_at) VALUES (?, ?, ?)""",
                (candidate_id, display_name, datetime.now(timezone.utc).isoformat()))
        return self.get(candidate_id)

    @asynccontextmanager
    async def context(self, candidate_id: str):
        candidate = self.get(candidate_id)
        if not candidate.db_path.is_file():
            raise FileNotFoundError(candidate.db_path)
        db = Database(str(candidate.db_path))
        bg_db = Database(str(candidate.db_path))
        try:
            await db.init()
            await bg_db.init()
            yield CandidateContext(candidate, db, bg_db)
        finally:
            await bg_db.close()
            await db.close()


def main():
    parser = argparse.ArgumentParser(description="CareerPulse private storage tools")
    parser.add_argument("--data-root")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("display_name")
    sub.add_parser("list")
    backup = sub.add_parser("backup")
    backup.add_argument("source", type=Path)
    migrate = sub.add_parser("migrate-copy", help="Import a private backup into an empty registry")
    migrate.add_argument("source", type=Path)
    migrate.add_argument("display_name")
    migrate.add_argument("--artifact", type=Path, action="append", default=[])
    restore = sub.add_parser("restore-copy", help="Restore a migration recovery point without cutover")
    restore.add_argument("candidate_id")
    restore.add_argument("destination", type=Path)
    args = parser.parse_args()
    registry = CandidateRegistry(args.data_root)
    if args.command == "backup":
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        print(backup_database(args.source, registry.root / "backups" / f"legacy-{stamp}.db"))
    elif args.command == "restore-copy":
        from app.legacy_migration import restore_migration_copy
        record = registry.get(args.candidate_id)
        print(restore_migration_copy(record.directory, args.destination))
    elif args.command in {"create", "migrate-copy"}:
        if args.command == "create":
            record = asyncio.run(registry.create(args.display_name))
        else:
            from app.legacy_migration import migrate_legacy_copy
            record = migrate_legacy_copy(registry, args.source, args.display_name, args.artifact)
        print(json.dumps({"candidate_id": record.candidate_id,
                          "submission_mode": record.submission_mode}))
    else:
        print(json.dumps([{"candidate_id": r.candidate_id,
                           "display_name": r.display_name,
                           "submission_mode": r.submission_mode} for r in registry.list()]))


if __name__ == "__main__":
    main()
