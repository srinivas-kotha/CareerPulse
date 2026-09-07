from contextlib import closing
import json
import sqlite3

import pytest

from app.candidates import CandidateRegistry, backup_database
from app.database import Database
from app.legacy_migration import file_hash, migrate_legacy_copy, restore_migration_copy


@pytest.fixture
async def legacy(tmp_path):
    source = tmp_path / "legacy.db"
    db = Database(str(source))
    await db.init()
    await db.save_user_profile(full_name="Synthetic Candidate", email="test@example.invalid")
    await db.save_ai_settings(provider="ollama", model="synthetic-model", api_key="synthetic-secret")
    await db.close()
    with closing(sqlite3.connect(source)) as conn, conn:
        # Unknown future tables, duplicate rows, blobs and account references
        # must survive too; a known-table export would lose these.
        conn.execute("CREATE TABLE future_evidence (value BLOB, account_ref TEXT)")
        conn.executemany("INSERT INTO future_evidence VALUES (?, ?)",
                         [(b"\x00\xff", "synthetic-account")] * 2)
    snapshot = backup_database(source, tmp_path / "backup.db")
    return source, snapshot


async def test_migration_and_restore_preserve_entire_database_and_artifacts(tmp_path, legacy):
    source, snapshot = legacy
    source_hash = file_hash(source)
    registry = CandidateRegistry(tmp_path / "private")
    artifact = tmp_path / "original.txt"
    artifact.write_text("Synthetic resume document", encoding="utf-8")
    record = migrate_legacy_copy(registry, snapshot, "Initial candidate", [artifact])
    assert record.submission_mode == "review"
    manifest = json.loads((record.directory / "recovery/manifest.json").read_text())
    assert "future_evidence" in manifest["tables"]
    assert file_hash(record.db_path) == manifest["database_sha256"]
    assert not list((record.directory / "browser").iterdir())
    async with registry.context(record.candidate_id) as context:
        assert (await context.db.get_user_profile())["full_name"] == "Synthetic Candidate"
        assert (await context.bg_db.get_ai_settings())["api_key"] == "synthetic-secret"
        await context.db.save_user_profile(full_name="Changed after migration")
    (record.directory / manifest["artifacts"][0]["path"]).write_text("Changed active artifact")
    restored = restore_migration_copy(record.directory, tmp_path / "restored")
    with closing(sqlite3.connect(restored)) as conn:
        assert conn.execute("SELECT full_name FROM user_profile").fetchone() == ("Synthetic Candidate",)
        assert conn.execute("SELECT * FROM future_evidence").fetchall() == [
            (b"\x00\xff", "synthetic-account")] * 2
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert (restored.parent / manifest["artifacts"][0]["path"]).read_bytes() == artifact.read_bytes()
    assert file_hash(source) == source_hash
    with pytest.raises(FileExistsError):
        restore_migration_copy(record.directory, restored.parent)
    # A later fresh profile never inherits migrated settings or documents.
    fresh = await registry.create("Another candidate")
    async with registry.context(fresh.candidate_id) as context:
        assert not await context.db.get_ai_settings()
    with pytest.raises(ValueError, match="empty"):
        migrate_legacy_copy(registry, snapshot, "Duplicate identity")


@pytest.mark.parametrize("damage", ["database", "artifact", "traversal"])
async def test_restore_rejects_corrupt_or_unsafe_bundle(tmp_path, legacy, damage):
    registry = CandidateRegistry(tmp_path / "private")
    artifact = tmp_path / "resume.txt"
    artifact.write_text("Synthetic")
    record = migrate_legacy_copy(registry, legacy[1], "Initial", [artifact])
    manifest_path = record.directory / "recovery/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if damage == "database":
        (record.directory / "recovery/legacy.db").write_bytes(b"broken")
    elif damage == "artifact":
        (record.directory / "recovery" / manifest["artifacts"][0]["path"]).write_text("changed")
    else:
        manifest["artifacts"][0]["path"] = "../outside.txt"
        manifest_path.write_text(json.dumps(manifest))
    destination = tmp_path / "restore"
    with pytest.raises(ValueError):
        restore_migration_copy(record.directory, destination)
    assert not destination.exists()


async def test_broken_links_are_not_published(tmp_path, legacy):
    with closing(sqlite3.connect(legacy[1])) as conn, conn:
        conn.execute("CREATE TABLE broken (parent INTEGER REFERENCES jobs(id))")
        conn.execute("INSERT INTO broken VALUES (99999)")
    registry = CandidateRegistry(tmp_path / "private")
    with pytest.raises(RuntimeError, match="foreign key"):
        migrate_legacy_copy(registry, legacy[1], "Initial")
    assert registry.list() == []


async def test_failed_copy_does_not_publish_or_modify_source(tmp_path, legacy, monkeypatch):
    registry = CandidateRegistry(tmp_path / "private")
    before = file_hash(legacy[1])
    def fail(*args):
        raise OSError("Simulated disk failure")
    monkeypatch.setattr("app.legacy_migration.shutil.copyfile", fail)
    with pytest.raises(OSError, match="disk failure"):
        migrate_legacy_copy(registry, legacy[1], "Initial")
    assert registry.list() == []
    assert file_hash(legacy[1]) == before
