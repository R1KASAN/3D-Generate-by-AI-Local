from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import aiosqlite
import pytest
import pytest_asyncio

from local3d.domain.jobs import AssetKind, GenerationJob, JobAsset, JobEvent, JobState
from local3d.persistence.database import Database
from local3d.persistence.jobs import JobRepository


def _asset(job_id, *, expires_at: datetime | None = None) -> JobAsset:
    return JobAsset(
        job_id=job_id,
        kind=AssetKind.INPUT,
        relative_path=f"uploads/{job_id}/input.png",
        content_type="image/png",
        size_bytes=185,
        sha256="a" * 64,
        expires_at=expires_at or datetime.now(timezone.utc) + timedelta(hours=24),
    )


def _job(job_id, asset_id, *, status: JobState = JobState.QUEUED, expires_at=None) -> GenerationJob:
    now = datetime.now(timezone.utc)
    return GenerationJob(
        job_id=job_id,
        token_digest="b" * 64,
        status=status,
        workflow_revision="workflow-rev-1",
        input_asset_id=asset_id,
        created_at=now,
        queued_at=now,
        expires_at=expires_at or now + timedelta(hours=24),
    )


@pytest_asyncio.fixture
async def repository(tmp_path: Path):
    database = Database(tmp_path / "jobs.sqlite3")
    await database.initialize()
    yield JobRepository(database)


@pytest.mark.asyncio
async def test_accept_job_commits_job_input_and_first_event_atomically(repository: JobRepository) -> None:
    job_id = uuid4()
    asset = _asset(job_id)
    job = _job(job_id, asset.asset_id)

    await repository.accept_job(job, asset)

    stored = await repository.get_job(job_id)
    events = await repository.list_events(job_id)
    assert stored is not None
    assert stored.status is JobState.QUEUED
    assert stored.input_asset_id == asset.asset_id
    assert [event.event_type for event in events] == ["accepted"]
    assert events[0].sequence == 1


@pytest.mark.asyncio
async def test_accept_job_rolls_back_all_rows_on_constraint_failure(repository: JobRepository) -> None:
    job_id = uuid4()
    asset = _asset(job_id)
    job = _job(job_id, asset.asset_id)
    await repository.accept_job(job, asset)

    with pytest.raises(aiosqlite.IntegrityError):
        await repository.accept_job(job, asset)

    assert len(await repository.list_events(job_id)) == 1
    assert await repository.count_assets(job_id) == 1


@pytest.mark.asyncio
async def test_transition_asset_and_event_roll_back_together(repository: JobRepository) -> None:
    job_id = uuid4()
    input_asset = _asset(job_id)
    job = _job(job_id, input_asset.asset_id)
    await repository.accept_job(job, input_asset)
    assert job.expires_at is not None
    output_asset = JobAsset(
        job_id=job_id,
        kind=AssetKind.OUTPUT,
        relative_path=f"{job_id}/outputs/model.glb",
        content_type="model/gltf-binary",
        size_bytes=12,
        sha256="c" * 64,
        expires_at=job.expires_at,
    )
    # Sequence 1 already belongs to the accepted event, forcing the final
    # insert to fail after the asset and job update statements have run.
    event = job.transition(JobState.PROCESSING)

    with pytest.raises(aiosqlite.IntegrityError):
        await repository.persist_transition(job, event, asset=output_asset)

    stored = await repository.get_job(job_id)
    assert stored is not None
    assert stored.status is JobState.QUEUED
    assert await repository.count_assets(job_id) == 1


@pytest.mark.asyncio
async def test_foreign_keys_reject_assets_for_unknown_jobs(repository: JobRepository) -> None:
    asset = _asset(uuid4())

    with pytest.raises(aiosqlite.IntegrityError):
        await repository.add_asset(asset)


@pytest.mark.asyncio
async def test_event_order_is_monotonic_per_job(repository: JobRepository) -> None:
    job_id = uuid4()
    asset = _asset(job_id)
    await repository.accept_job(_job(job_id, asset.asset_id), asset)

    await repository.append_event(
        JobEvent(job_id=job_id, sequence=2, event_type="state_changed", to_status=JobState.PROCESSING)
    )
    await repository.append_event(
        JobEvent(job_id=job_id, sequence=3, event_type="progress", progress_percent=50)
    )

    assert [event.sequence for event in await repository.list_events(job_id)] == [1, 2, 3]


@pytest.mark.asyncio
async def test_expiry_removes_terminal_jobs_but_keeps_active_jobs(repository: JobRepository) -> None:
    now = datetime.now(timezone.utc)
    expired_id = uuid4()
    expired_asset = _asset(expired_id, expires_at=now - timedelta(minutes=1))
    expired_job = _job(
        expired_id,
        expired_asset.asset_id,
        status=JobState.FAILED,
        expires_at=now - timedelta(minutes=1),
    )
    active_id = uuid4()
    active_asset = _asset(active_id, expires_at=now - timedelta(minutes=1))
    active_job = _job(active_id, active_asset.asset_id, expires_at=now - timedelta(minutes=1))
    await repository.accept_job(expired_job, expired_asset)
    await repository.accept_job(active_job, active_asset)

    assert await repository.delete_expired(now) == [expired_id]
    assert await repository.get_job(expired_id) is None
    assert await repository.get_job(active_id) is not None


@pytest.mark.asyncio
async def test_restart_reads_persisted_job(tmp_path: Path) -> None:
    path = tmp_path / "jobs.sqlite3"
    first = Database(path)
    await first.initialize()
    job_id = uuid4()
    asset = _asset(job_id)
    await JobRepository(first).accept_job(_job(job_id, asset.asset_id), asset)

    second = Database(path)
    await second.initialize()
    stored = await JobRepository(second).get_job(job_id)

    assert stored is not None
    assert stored.job_id == job_id


@pytest.mark.asyncio
async def test_submission_reservation_is_durable_and_single_use(repository: JobRepository) -> None:
    job_id = uuid4()
    asset = _asset(job_id)
    await repository.accept_job(_job(job_id, asset.asset_id), asset)

    assert await repository.reserve_submission(job_id) is True
    assert await repository.reserve_submission(job_id) is False
    stored = await repository.get_job(job_id)
    assert stored is not None
    assert stored.attempt_count == 1


@pytest.mark.asyncio
async def test_busy_timeout_is_configured(tmp_path: Path) -> None:
    database = Database(tmp_path / "jobs.sqlite3", busy_timeout_ms=4321)
    await database.initialize()

    async with database.connection() as connection:
        cursor = await connection.execute("PRAGMA busy_timeout")
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == 4321


@pytest.mark.asyncio
async def test_unsafe_sqlite_version_falls_back_from_wal(tmp_path: Path) -> None:
    database = Database(tmp_path / "jobs.sqlite3", sqlite_version=(3, 21, 0))
    await database.initialize()

    async with database.connection() as connection:
        cursor = await connection.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()

    assert row is not None
    assert str(row[0]).lower() == "delete"
