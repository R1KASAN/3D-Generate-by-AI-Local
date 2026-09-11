from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from local3d.adapters.generation.mock import MockGenerationAdapter
from local3d.config import Settings
from local3d.services.job_service import JobNotCancellableError, JobNotFoundError, JobService
from local3d.services.recovery import RecoveryService


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"
MODEL = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


@pytest.mark.asyncio
async def test_cancel_is_idempotent_and_wrong_tokens_are_hidden(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
    service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await service.startup()
    with FIXTURE.open("rb") as stream:
        first, first_token = await service.create_job(stream, filename="one.png", content_type="image/png")
    with FIXTURE.open("rb") as stream:
        second, second_token = await service.create_job(stream, filename="two.png", content_type="image/png")

    with pytest.raises(JobNotFoundError):
        await service.cancel_job(second.job_id, first_token)
    cancelled = await service.cancel_job(second.job_id, second_token)
    retried = await service.cancel_job(second.job_id, second_token)
    assert cancelled.status.value == retried.status.value == "cancelled"
    assert service.adapter.submission_count == 0


@pytest.mark.asyncio
async def test_terminal_cancellation_and_restart_retain_state(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
    service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await service.startup()
    with FIXTURE.open("rb") as stream:
        job, token = await service.create_job(stream, filename="reference.png", content_type="image/png")
    await service._advance(job)
    with pytest.raises(JobNotCancellableError):
        await service.cancel_job(job.job_id, token)
    restarted = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await restarted.startup()
    await RecoveryService(restarted).reconcile()
    with pytest.raises(JobNotCancellableError):
        await restarted.cancel_job(job.job_id, token)


def test_async_contract_module_is_importable() -> None:
    assert asyncio.iscoroutinefunction(JobService.cancel_job)
