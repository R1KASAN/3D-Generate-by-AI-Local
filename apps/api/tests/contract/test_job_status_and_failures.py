from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from local3d.adapters.generation.mock import MockGenerationAdapter
from local3d.config import Settings
from local3d.domain.jobs import JobState
from local3d.main import create_app
from local3d.services.generation_coordinator import GenerationCoordinator
from local3d.services.job_service import JobService


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"
MODEL = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def _client(tmp_path: Path, *, mode: str = "success") -> TestClient:
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
    service = JobService(settings, adapter=MockGenerationAdapter(fixture_path=MODEL, mode=mode))
    return TestClient(create_app(settings, service=service))


def _create(client: TestClient) -> tuple[str, str]:
    response = client.post("/api/v1/jobs", files={"file": ("reference.png", FIXTURE.read_bytes(), "image/png")})
    assert response.status_code == 201, response.text
    payload = response.json()
    return payload["job_id"], payload["job_token"]


def test_coordinator_maps_engine_observations_without_inventing_progress() -> None:
    coordinator = GenerationCoordinator()
    queued = coordinator.decide("queued")
    processing = coordinator.decide("processing", progress_percent=37)
    unknown = coordinator.decide("unknown", error_code="engine_disconnect")

    assert queued.target_state is JobState.QUEUED
    assert queued.progress_percent is None
    assert processing.target_state is JobState.PROCESSING
    assert processing.progress_percent == 37
    assert unknown.target_state is JobState.FAILED
    assert unknown.error is not None
    assert unknown.error.code == "engine_unavailable"


def test_status_exposes_only_engine_backed_progress_and_safe_terminal_result(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        job_id, token = _create(client)
        headers = {"X-Job-Token": token}
        queued = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        processing = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        completed = client.get(f"/api/v1/jobs/{job_id}", headers=headers)

    assert queued.json()["status"] == "queued"
    assert queued.json()["progress_percent"] is None
    assert queued.json()["queue_position"] in {None, 1}
    assert queued.json()["queue_position_is_approximate"] is True
    assert processing.json()["status"] == "processing"
    assert processing.json()["progress_percent"] == 50
    assert completed.json()["status"] == "completed"
    assert completed.json()["progress_percent"] == 100
    assert completed.json()["model_url"].endswith(f"/{job_id}/model")


def test_engine_failure_is_safe_and_result_stays_unavailable(tmp_path: Path) -> None:
    with _client(tmp_path, mode="failure") as client:
        job_id, token = _create(client)
        headers = {"X-Job-Token": token}
        client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        failed = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        model = client.get(f"/api/v1/jobs/{job_id}/model", headers=headers)

    assert failed.json()["status"] == "failed"
    assert failed.json()["error"] == {"code": "generation_failed", "message": "Generation failed"}
    assert "traceback" not in failed.text.lower()
    assert model.status_code == 409


def test_missing_output_and_timeout_are_terminal_without_false_completion(tmp_path: Path) -> None:
    with _client(tmp_path / "missing", mode="missing") as client:
        missing_id, missing_token = _create(client)
        headers = {"X-Job-Token": missing_token}
        for _ in range(3):
            missing = client.get(f"/api/v1/jobs/{missing_id}", headers=headers)
        missing_model = client.get(f"/api/v1/jobs/{missing_id}/model", headers=headers)

    with _client(tmp_path / "timeout", mode="timeout") as client:
        timeout_id, timeout_token = _create(client)
        headers = {"X-Job-Token": timeout_token}
        client.get(f"/api/v1/jobs/{timeout_id}", headers=headers)
        timeout = client.get(f"/api/v1/jobs/{timeout_id}", headers=headers)
        timeout_model = client.get(f"/api/v1/jobs/{timeout_id}/model", headers=headers)

    assert missing.json()["status"] == "failed"
    assert missing.json()["error"]["code"] == "invalid_result"
    assert missing_model.status_code == 409
    assert timeout.json()["status"] == "failed"
    assert timeout.json()["error"]["code"] == "generation_timeout"
    assert timeout_model.status_code == 409
