from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from local3d.adapters.generation.mock import MockGenerationAdapter
from local3d.config import Settings
from local3d.main import create_app
from local3d.services.job_service import JobService, JobNotCancellableError, JobNotFoundError
from local3d.services.recovery import RecoveryService


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"
MODEL = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def _settings(tmp_path: Path) -> Settings:
    return Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")


def test_cancel_endpoint_is_token_isolated_idempotent_and_durable(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    adapter = MockGenerationAdapter(fixture_path=MODEL)
    service = JobService(settings, adapter=adapter)
    asyncio.run(service.startup())
    client = TestClient(create_app(settings, service=service))

    first = client.post(
        "/api/v1/jobs",
        files={"file": ("one.png", FIXTURE.read_bytes(), "image/png")},
    ).json()
    second = client.post(
        "/api/v1/jobs",
        files={"file": ("two.png", FIXTURE.read_bytes(), "image/png")},
    ).json()
    cancel_url = f"/api/v1/jobs/{second['job_id']}/cancel"

    missing = client.post(cancel_url)
    cross_job = client.post(cancel_url, headers={"X-Job-Token": first["job_token"]})
    cancelled = client.post(cancel_url, headers={"X-Job-Token": second["job_token"]})
    retried = client.post(cancel_url, headers={"X-Job-Token": second["job_token"]})
    restored = client.get(
        f"/api/v1/jobs/{second['job_id']}",
        headers={"X-Job-Token": second["job_token"]},
    )

    assert missing.status_code == cross_job.status_code == 404
    assert missing.json() == cross_job.json()
    assert cancelled.status_code == retried.status_code == restored.status_code == 200
    assert cancelled.json()["status"] == retried.json()["status"] == restored.json()["status"] == "cancelled"
    assert cancelled.json()["queue_position"] is None
    assert cancelled.headers["cache-control"] == "no-store"
    assert str(second["job_id"]) not in service.dispatcher.pending
    assert adapter.submission_count == 0


@pytest.mark.asyncio
async def test_cancelled_job_stays_terminal_after_api_restart(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await first.startup()
    with FIXTURE.open("rb") as stream:
        job, token = await first.create_job(stream, filename="reference.png", content_type="image/png")

    cancelled = await first.cancel_job(job.job_id, token)
    restarted_adapter = MockGenerationAdapter(fixture_path=MODEL)
    restarted = JobService(settings, adapter=restarted_adapter)
    await restarted.startup()
    reconciled = await RecoveryService(restarted).reconcile()
    restored = await restarted.read_job(job.job_id, token)

    assert cancelled.status.value == restored.status.value == "cancelled"
    assert restored.error_code == "cancelled_by_user"
    assert reconciled == []
    assert restarted.dispatcher.pending == ()
    assert restarted_adapter.submission_count == 0


@pytest.mark.asyncio
async def test_submitted_or_cross_token_job_cannot_be_cancelled(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await service.startup()
    with FIXTURE.open("rb") as stream:
        job, token = await service.create_job(stream, filename="reference.png", content_type="image/png")

    await service._advance(job)

    with pytest.raises(JobNotCancellableError):
        await service.cancel_job(job.job_id, token)
    with pytest.raises(JobNotFoundError):
        await service.cancel_job(job.job_id, "wrong-token")
    assert service.adapter.submission_count == 1
