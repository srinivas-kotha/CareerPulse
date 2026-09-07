"""Lossless first-candidate migration from a private, offline recovery copy.

This does not cut over the running application or copy browser sessions. Legacy
credentials inside SQLite are preserved only for the initial candidate.
"""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4

from app.candidates import CandidateRegistry, backup_database, external_data_root


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def migrate_legacy_copy(registry: CandidateRegistry, source: Path,
                        display_name: str, artifacts: tuple[Path, ...] | list[Path] = ()):
    """Publish one verified recovery copy into an empty installation registry.

    Supply a previously backed-up DB and explicitly selected, quiescent files.
    Files receive opaque names; the private manifest retains their original
    references. No live path is rewritten and no scheduler is started. Failures
    leave an unregistered directory for diagnosis, never a usable candidate.
    """
    display_name = display_name.strip()
    if not display_name or len(display_name) > 120:
        raise ValueError("Display name must contain 1 to 120 characters")
    source = source.expanduser().resolve()
    external_data_root(source.parent)
    if registry.list():
        raise ValueError("Legacy migration requires an empty candidate registry")
    files = [Path(p).expanduser().resolve() for p in artifacts]
    if len(set(files)) != len(files):
        raise ValueError("Duplicate artifact paths")
    for path in files:
        if not path.is_file() or path == source:
            raise ValueError("Artifacts must be individual files distinct from the database")
        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            raise ValueError("Use SQLite backup for databases, not artifact copying")

    candidate_id = str(uuid4())
    directory = registry.root / "candidates" / candidate_id
    directory.mkdir(parents=True, exist_ok=False)
    for name in ("artifacts", "browser", "cache", "recovery"):
        (directory / name).mkdir()
    snapshot = backup_database(source, directory / "recovery" / "legacy.db")
    database = directory / "candidate.db"
    shutil.copyfile(snapshot, database)
    digest = file_hash(snapshot)
    if file_hash(database) != digest:
        raise RuntimeError("Database restore verification failed")
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as conn:
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        if not {"jobs", "applications", "user_profile"}.issubset(tables):
            raise ValueError("Source is not a supported CareerPulse database")
        if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise RuntimeError("Restored database integrity check failed")
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("Legacy database has broken foreign key references")
    entries = []
    (directory / "recovery" / "artifacts").mkdir()
    for index, path in enumerate(files):
        target = directory / "artifacts" / f"{index:06d}{path.suffix}"
        recovery_target = directory / "recovery" / "artifacts" / target.name
        before = file_hash(path)
        shutil.copyfile(path, recovery_target)
        shutil.copyfile(recovery_target, target)
        if (file_hash(target) != before or file_hash(recovery_target) != before
                or file_hash(path) != before):
            raise RuntimeError("Artifact changed during migration")
        entries.append({"source": str(path), "path": target.relative_to(directory).as_posix(),
                        "sha256": before})
    manifest = {"version": 1, "candidate_id": candidate_id,
                "database_sha256": digest, "tables": tables, "artifacts": entries,
                "source": str(source), "runtime_cutover": False}
    (directory / "recovery" / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    # Serialize publication with other registry writers and recheck after copying.
    with closing(registry._connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM candidates LIMIT 1").fetchone():
            raise ValueError("Legacy migration requires an empty candidate registry")
        conn.execute("""INSERT INTO candidates
            (candidate_id, display_name, created_at) VALUES (?, ?, ?)""",
            (candidate_id, display_name, datetime.now(timezone.utc).isoformat()))
    return registry.get(candidate_id)


def restore_migration_copy(candidate_directory: Path, destination: Path) -> Path:
    """Verify and restore the migration recovery point to a new private directory.

    This never replaces an existing candidate or changes registry ownership.
    The operator must keep the migration artifacts intact for recovery.
    """
    candidate_directory = candidate_directory.resolve()
    destination = external_data_root(destination)
    manifest = json.loads((candidate_directory / "recovery" / "manifest.json").read_text(
        encoding="utf-8"))
    if manifest.get("version") != 1:
        raise ValueError("Unsupported migration manifest")
    snapshot = candidate_directory / "recovery" / "legacy.db"
    if file_hash(snapshot) != manifest["database_sha256"]:
        raise ValueError("Recovery database checksum mismatch")
    files = []
    for entry in manifest["artifacts"]:
        relative = Path(entry["path"])
        path = (candidate_directory / "recovery" / relative).resolve()
        artifact_root = (candidate_directory / "recovery" / "artifacts").resolve()
        if relative.is_absolute() or ".." in relative.parts or artifact_root not in path.parents:
            raise ValueError("Invalid recovery artifact path")
        if file_hash(path) != entry["sha256"]:
            raise ValueError("Recovery artifact checksum mismatch")
        files.append((relative, path, entry["sha256"]))
    destination.mkdir(parents=True, exist_ok=False)
    restored = backup_database(snapshot, destination / "candidate.db")
    # The online backup validates SQLite; byte equality is checked using a
    # direct copy of the already closed recovery point as well.
    shutil.copyfile(snapshot, restored)
    if file_hash(restored) != manifest["database_sha256"]:
        raise RuntimeError("Restored database checksum mismatch")
    for relative, source, digest in files:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if file_hash(target) != digest:
            raise RuntimeError("Restored artifact checksum mismatch")
    return restored
