from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from local3d.adapters.generation.mock import MockGenerationAdapter
from local3d.config import Settings
from local3d.main import create_app
from local3d.services.job_service import JobService
from local3d.services.recovery import RecoveryService


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"
MODEL = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def _settings(tmp_path: Path) -> Settings:
    return Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")


def _submit(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/jobs", files={"file": ("reference.png", FIXTURE.read_bytes(), "image/png")})
    assert response.status_code == 201, response.text
    payload = response.json()
    return payload["job_id"], payload["job_token"]


@pytest.mark.parametrize(
    ("mode", "expected_status", "expected_code"),
    [
        ("timeout", "failed", "generation_timeout"),
        ("disconnect", "failed", "engine_unavailable"),
        ("uncertain", "failed", "engine_unavailable"),
        ("cancelled", "cancelled", "generation_cancelled"),
    ],
)
def test_adapter_recovery_modes_are_safe_and_non_public(tmp_path: Path, mode: str, expected_status: str, expected_code: str) -> None:
    settings = _settings(tmp_path)
    adapter = MockGenerationAdapter(fixture_path=MODEL, mode=mode)
    service = JobService(settings, adapter=adapter)
    with TestClient(create_app(settings, service=service)) as client:
        job_id, token = _submit(client)
        headers = {"X-Job-Token": token}
        client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        observed = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        result = client.get(f"/api/v1/jobs/{job_id}/model", headers=headers)

    assert observed.json()["status"] == expected_status
    assert observed.json()["error"]["code"] == expected_code
    assert "internal" not in observed.text.lower()
    assert result.status_code == 409
    assert adapter.submission_count == 1


@pytest.mark.asyncio
async def test_restart_reconciliation_fails_processing_without_duplicate_submission(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first_adapter = MockGenerationAdapter(fixture_path=MODEL)
    first_service = JobService(settings, adapter=first_adapter)
    app = create_app(settings, service=first_service)
    with TestClient(app) as client:
        job_id, token = _submit(client)
        headers = {"X-Job-Token": token}
        client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        processing = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert processing.json()["status"] == "processing"

    restarted_adapter = MockGenerationAdapter(fixture_path=MODEL)
    restarted = JobService(settings, adapter=restarted_adapter)
    await restarted.startup()
    reconciled = await RecoveryService(restarted).reconcile()
    stored = await restarted.repository.get_job(__import__("uuid").UUID(job_id))

    assert reconciled == [job_id]
    assert stored is not None
    assert stored.status.value == "failed"
    assert stored.error_code == "restart_recovery"
    assert restarted_adapter.submission_count == 0


@pytest.mark.asyncio
async def test_restart_rehydrates_accepted_queued_job_without_duplicate_submission(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await first.startup()
    with FIXTURE.open("rb") as stream:
        job, token = await first.create_job(stream, filename="reference.png", content_type="image/png")

    restarted_adapter = MockGenerationAdapter(fixture_path=MODEL)
    restarted = JobService(settings, adapter=restarted_adapter)
    await restarted.startup()
    reconciled = await RecoveryService(restarted).reconcile()
    await restarted.read_job(job.job_id, token)
    await restarted.read_job(job.job_id, token)

    assert reconciled == [str(job.job_id)]
    assert restarted_adapter.submission_count == 1
    stored = await restarted.repository.get_job(job.job_id)
    assert stored is not None
    assert stored.status.value == "processing"


@pytest.mark.asyncio
async def test_restart_records_completed_job_with_missing_output(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await first.startup()
    with FIXTURE.open("rb") as stream:
        job, token = await first.create_job(stream, filename="reference.png", content_type="image/png")
    for _ in range(4):
        await first.read_job(job.job_id, token)
    first.storage.resolve_path(job.job_id, "outputs/model.glb").unlink()

    restarted = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL))
    await restarted.startup()
    reconciled = await RecoveryService(restarted).reconcile()
    events = await restarted.repository.list_events(UUID(str(job.job_id)))

    assert str(job.job_id) in reconciled
    assert events[-1].event_type == "output_missing"
    assert events[-1].safe_message == "Generated model is unavailable"
