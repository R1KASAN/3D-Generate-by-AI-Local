from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from local3d.adapters.generation.mock import MockGenerationAdapter
from local3d.config import Settings
from local3d.main import create_app
from local3d.services.job_service import JobService
from local3d.domain.jobs import JobState, SafeJobError


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"
MODEL = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def _settings(tmp_path: Path) -> Settings:
    return Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")


@pytest.mark.parametrize("mode", ["failure", "missing", "timeout"])
def test_failure_matrix_never_publishes_a_result_url(tmp_path: Path, mode: str) -> None:
    settings = _settings(tmp_path)
    service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL, mode=mode))
    with TestClient(create_app(settings, service=service)) as client:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("reference.png", FIXTURE.read_bytes(), "image/png")},
        )
        payload = response.json()
        headers = {"X-Job-Token": payload["job_token"]}
        observed = payload
        for _ in range(4):
            observed = client.get(f"/api/v1/jobs/{payload['job_id']}", headers=headers).json()
            if observed["status"] in {"failed", "cancelled"}:
                break

    assert observed["status"] == "failed"
    assert observed["model_url"] is None
    assert observed["download_url"] is None


def test_refresh_reuses_the_same_job_and_terminal_state_does_not_change(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    with TestClient(create_app(settings, service=service)) as client:
        created = client.post(
            "/api/v1/jobs",
            files={"file": ("reference.png", FIXTURE.read_bytes(), "image/png")},
        ).json()
        headers = {"X-Job-Token": created["job_token"]}
        first = client.get(f"/api/v1/jobs/{created['job_id']}", headers=headers).json()
        second = client.get(f"/api/v1/jobs/{created['job_id']}", headers=headers).json()
        completed = client.get(f"/api/v1/jobs/{created['job_id']}", headers=headers).json()
        repeated = client.get(f"/api/v1/jobs/{created['job_id']}", headers=headers).json()

    assert first["job_id"] == second["job_id"] == completed["job_id"] == repeated["job_id"]
    assert completed["status"] == repeated["status"] == "completed"
    assert completed["model_url"] == repeated["model_url"]


@pytest.mark.asyncio
async def test_retention_cleanup_removes_expired_terminal_job_files_and_rows(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await service.startup()
    with FIXTURE.open("rb") as stream:
        job, _token = await service.create_job(stream, filename="reference.png", content_type="image/png")
    events = await service.repository.list_events(job.job_id)
    job._event_sequence = events[-1].sequence
    event = job.transition(JobState.FAILED, error=SafeJobError(code="test_failure", message="Generation failed"))
    job.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await service.repository.persist_transition(job, event)

    removed = await service.cleanup_expired(datetime.now(timezone.utc))

    assert removed == [job.job_id]
    assert await service.repository.get_job(job.job_id) is None
    assert not (service.storage.root / str(job.job_id)).exists()


@pytest.mark.asyncio
async def test_periodic_retention_cleanup_runs_without_operator_request(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await service.startup()
    with FIXTURE.open("rb") as stream:
        job, _token = await service.create_job(stream, filename="reference.png", content_type="image/png")
    events = await service.repository.list_events(job.job_id)
    job._event_sequence = events[-1].sequence
    event = job.transition(JobState.FAILED, error=SafeJobError(code="test_failure", message="Generation failed"))
    job.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await service.repository.persist_transition(job, event)

    task = service.start_maintenance(interval_seconds=0.01)
    try:
        for _ in range(20):
            if await service.repository.get_job(job.job_id) is None:
                break
            await asyncio.sleep(0.01)
    finally:
        await service.stop_maintenance(task)

    assert await service.repository.get_job(job.job_id) is None
