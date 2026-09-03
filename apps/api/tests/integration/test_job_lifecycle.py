from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
from pathlib import Path
import shutil
import time

import pytest
from fastapi.testclient import TestClient

from local3d.adapters.generation.mock import MockGenerationAdapter
from local3d.adapters.generation.base import EngineObservation, JobObservationStatus
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


def test_fast_engine_success_records_legal_processing_bridge(tmp_path: Path) -> None:
    class FastSuccessAdapter(MockGenerationAdapter):
        def inspect(self, handle):  # type: ignore[no-untyped-def]
            execution = self._executions[handle.internal_id]
            execution.calls += 1
            if execution.calls == 1:
                return EngineObservation(status=JobObservationStatus.QUEUED)
            candidate = execution.request.output_dir / "model.glb"
            shutil.copyfile(self.fixture_path, candidate)
            return EngineObservation(status=JobObservationStatus.SUCCEEDED, candidates=(candidate,))

    settings = _settings(tmp_path)
    service = JobService(settings, adapter=FastSuccessAdapter(fixture_path=MODEL))
    with TestClient(create_app(settings, service=service)) as client:
        created = client.post(
            "/api/v1/jobs",
            files={"file": ("reference.png", FIXTURE.read_bytes(), "image/png")},
        ).json()
        queued = client.get(
            f"/api/v1/jobs/{created['job_id']}",
            headers={"X-Job-Token": created["job_token"]},
        )
        completed = client.get(
            f"/api/v1/jobs/{created['job_id']}",
            headers={"X-Job-Token": created["job_token"]},
        )

    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_repeated_engine_processing_observations_update_progress(tmp_path: Path) -> None:
    class RepeatedProcessingAdapter(MockGenerationAdapter):
        def inspect(self, handle):  # type: ignore[no-untyped-def]
            execution = self._executions[handle.internal_id]
            execution.calls += 1
            if execution.calls == 1:
                return EngineObservation(status=JobObservationStatus.QUEUED)
            if execution.calls <= 3:
                return EngineObservation(
                    status=JobObservationStatus.PROCESSING,
                    progress_percent=(execution.calls - 1) * 10,
                )
            candidate = execution.request.output_dir / "model.glb"
            shutil.copyfile(self.fixture_path, candidate)
            return EngineObservation(status=JobObservationStatus.SUCCEEDED, candidates=(candidate,))

    settings = _settings(tmp_path)
    service = JobService(settings, adapter=RepeatedProcessingAdapter(fixture_path=MODEL))
    with TestClient(create_app(settings, service=service)) as client:
        created = client.post(
            "/api/v1/jobs",
            files={"file": ("reference.png", FIXTURE.read_bytes(), "image/png")},
        ).json()
        headers = {"X-Job-Token": created["job_token"]}
        statuses = [
            client.get(f"/api/v1/jobs/{created['job_id']}", headers=headers).json()
            for _ in range(4)
        ]

    assert [item["status"] for item in statuses] == ["queued", "processing", "processing", "completed"]
    assert statuses[1]["progress_percent"] == 10
    assert statuses[2]["progress_percent"] == 20


@pytest.mark.asyncio
async def test_background_worker_advances_unpolled_queued_jobs(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    adapter = MockGenerationAdapter(fixture_path=MODEL)
    service = JobService(settings, adapter=adapter)
    await service.startup()
    worker_task = service.start_worker(interval_seconds=0.01)
    try:
        with FIXTURE.open("rb") as stream:
            first, _first_token = await service.create_job(
                stream,
                filename="first.png",
                content_type="image/png",
            )
        with FIXTURE.open("rb") as stream:
            second, _second_token = await service.create_job(
                stream,
                filename="second.png",
                content_type="image/png",
            )

        # Deliberately do not read either job. The worker must still drain the
        # first job and then advance the second job in FIFO order.
        observed = None
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            observed = await service.repository.get_job(second.job_id)
            if observed is not None and observed.status is JobState.COMPLETED:
                break
            await asyncio.sleep(0.05)
    finally:
        await service.stop_worker(worker_task)

    assert observed is not None
    assert observed.status is JobState.COMPLETED
    assert adapter.submission_count == 2


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
