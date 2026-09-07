import asyncio
from contextlib import closing
from dataclasses import FrozenInstanceError
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest

from app.candidates import CandidateRegistry, backup_database, external_data_root


async def test_candidate_connections_and_credentials_are_isolated(tmp_path):
    registry = CandidateRegistry(tmp_path)
    first, second = await asyncio.gather(registry.create("Example A"),
                                         registry.create("Example B"))
    assert first.submission_mode == second.submission_mode == "review"
    assert first.directory != second.directory
    async with registry.context(first.candidate_id) as a:
        await a.db.save_user_profile(full_name="Example A", email="a@example.invalid")
        await a.db.save_ai_settings(provider="ollama", model="test-model")
        async with registry.context(second.candidate_id) as b:
            await b.db.save_user_profile(full_name="Example B")
            assert not await b.db.get_ai_settings()
            assert (await b.bg_db.get_user_profile())["full_name"] == "Example B"
            assert (await a.bg_db.get_user_profile())["full_name"] == "Example A"
            assert a.db is not a.bg_db
            # The same requisition is independent in each candidate database.
            job = dict(title="Example role", company="Example employer", location="Remote",
                       salary_min=None, salary_max=None, description="Example listing",
                       url="https://example.invalid/jobs/1", posted_date=None,
                       application_method="url", contact_email=None)
            first_job = await a.db.insert_job(**job)
            second_job = await b.db.insert_job(**job)
            assert first_job is not None and second_job is not None
            await a.db.dismiss_job(first_job)
            assert (await a.bg_db.get_job(first_job))["dismissed"] == 1
            assert (await b.bg_db.get_job(second_job))["dismissed"] == 0
            with pytest.raises(FrozenInstanceError):
                a.candidate = second
        assert a.candidate.candidate_id == first.candidate_id
    # Registry survives a new process/instance; directories do not derive from names.
    assert len(CandidateRegistry(tmp_path).list()) == 2
    assert (first.directory / "browser").is_dir()
    assert (second.directory / "artifacts").is_dir()


@pytest.mark.parametrize("candidate_id", ["../other", "default", str(uuid4())])
async def test_unknown_candidate_never_falls_back(tmp_path, candidate_id):
    registry = CandidateRegistry(tmp_path)
    with pytest.raises(KeyError):
        async with registry.context(candidate_id):
            pytest.fail("Must not resolve a missing candidate")
    assert registry.list() == []


async def test_missing_database_is_not_silently_recreated(tmp_path):
    registry = CandidateRegistry(tmp_path)
    candidate = await registry.create("Example")
    candidate.db_path.unlink()
    with pytest.raises(FileNotFoundError):
        async with registry.context(candidate.candidate_id):
            pytest.fail("Missing data must require recovery")
    assert not candidate.db_path.exists()


def test_external_root_config_and_checkout_rejection(tmp_path, monkeypatch):
    monkeypatch.setenv("CAREERPULSE_DATA_ROOT", str(tmp_path))
    assert external_data_root() == tmp_path.resolve()
    with pytest.raises(ValueError, match="outside"):
        external_data_root(Path(__file__).resolve().parents[1] / "data" / "profiles")
    other_repo = tmp_path / "another-repository"
    other_repo.mkdir()
    (other_repo / ".git").write_text("gitdir: elsewhere")
    with pytest.raises(ValueError, match="outside Git"):
        external_data_root(other_repo / "private")


def test_backup_includes_committed_wal_and_can_restore(tmp_path):
    source = tmp_path / "live.db"
    backup = tmp_path / "backups" / "snapshot.db"
    with closing(sqlite3.connect(source)) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE evidence (value TEXT)")
        live.execute("INSERT INTO evidence VALUES ('committed')")
        live.commit()
        live.execute("INSERT INTO evidence VALUES ('uncommitted')")
        backup_database(source, backup)
        with closing(sqlite3.connect(backup)) as restored:
            assert restored.execute("SELECT value FROM evidence").fetchall() == [("committed",)]
            assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        with pytest.raises(FileExistsError):
            backup_database(source, backup)
        live.rollback()
    assert source.is_file()


def test_backup_missing_source_does_not_create_database(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup_database(tmp_path / "missing.db", tmp_path / "backup.db")
    assert not (tmp_path / "missing.db").exists()
