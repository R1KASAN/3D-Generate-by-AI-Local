import asyncio
from datetime import datetime, timedelta, timezone
import io
import os
from pathlib import Path
from uuid import uuid4

from local3d.storage.job_storage import JobStorage
from local3d.adapters.generation.mock import MockGenerationAdapter
from local3d.config import Settings
from local3d.services.image_validation import LowStorageError
from local3d.services.job_service import JobService

FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"
MODEL = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def test_orphan_cleanup_removes_only_old_uuid_directories(tmp_path: Path) -> None:
    storage = JobStorage(tmp_path)
    old_id, fresh_id = uuid4(), uuid4()
    old = storage.ensure_job(old_id).job_root
    fresh = storage.ensure_job(fresh_id).job_root
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()
    import os
    os.utime(old, (old_time, old_time))
    removed = storage.remove_orphaned_jobs(set(), older_than=datetime.now(timezone.utc) - timedelta(hours=1))
    assert removed == [old_id]
    assert not old.exists()
    assert fresh.exists()


def test_orphan_cleanup_does_not_follow_symlink_or_delete_known_job(tmp_path: Path) -> None:
    storage = JobStorage(tmp_path)
    known_id = uuid4()
    known = storage.ensure_job(known_id).job_root
    target = tmp_path / "outside"
    target.mkdir()
    link = tmp_path / str(uuid4())
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        return
    removed = storage.remove_orphaned_jobs({known_id}, older_than=datetime.now(timezone.utc) + timedelta(hours=1))
    assert removed == []
    assert known.exists() and target.exists() and link.exists()


def test_crash_created_uuid_directory_is_grace_protected_then_removed(tmp_path: Path) -> None:
    storage = JobStorage(tmp_path)
    orphan_id = uuid4()
    orphan = tmp_path / str(orphan_id)
    orphan.mkdir()
    now = datetime.now(timezone.utc)
    assert storage.remove_orphaned_jobs(set(), older_than=now - timedelta(hours=1)) == []
    old_time = (now - timedelta(hours=2)).timestamp()
    os.utime(orphan, (old_time, old_time))
    assert storage.remove_orphaned_jobs(set(), older_than=now - timedelta(hours=1)) == [orphan_id]


def test_cleanup_and_result_read_share_a_storage_lock(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
        service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
        await service.startup()
        await service._cleanup_lock.acquire()
        cleanup = asyncio.create_task(service.cleanup_expired(datetime.now(timezone.utc)))
        await asyncio.sleep(0)
        assert not cleanup.done()
        service._cleanup_lock.release()
        await cleanup

    asyncio.run(scenario())


def test_low_disk_rejects_new_work_without_removing_accepted_work(tmp_path: Path, monkeypatch) -> None:
    async def scenario() -> None:
        settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
        service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
        await service.startup()
        first, _token = await service.create_job(io.BytesIO(FIXTURE.read_bytes()), filename="first.png", content_type="image/png")
        monkeypatch.setattr("local3d.services.job_service.shutil.disk_usage", lambda _: type("Usage", (), {"free": 1, "total": 100})())
        try:
            await service.create_job(io.BytesIO(FIXTURE.read_bytes()), filename="second.png", content_type="image/png")
        except LowStorageError:
            pass
        else:
            raise AssertionError("low disk admission unexpectedly accepted work")
        assert await service.repository.get_job(first.job_id) is not None

    asyncio.run(scenario())
