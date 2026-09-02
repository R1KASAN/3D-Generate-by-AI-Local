from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from local3d.adapters.generation.mock import MockGenerationAdapter
from local3d.config import Settings
from local3d.main import create_app
from local3d.services.job_service import JobService


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"
MODEL = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def test_two_users_wait_in_fifo_queue_and_keep_isolated_outputs(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
    adapter = MockGenerationAdapter(fixture_path=MODEL)
    service = JobService(settings, adapter=adapter)
    with TestClient(create_app(settings, service=service)) as client:
        first = client.post("/api/v1/jobs", files={"file": ("one.png", FIXTURE.read_bytes(), "image/png")}).json()
        second = client.post("/api/v1/jobs", files={"file": ("two.png", FIXTURE.read_bytes(), "image/png")}).json()
        first_headers = {"X-Job-Token": first["job_token"]}
        second_headers = {"X-Job-Token": second["job_token"]}

        first_queued = client.get(f"/api/v1/jobs/{first['job_id']}", headers=first_headers).json()
        first_processing = client.get(f"/api/v1/jobs/{first['job_id']}", headers=first_headers).json()
        second_waiting = client.get(f"/api/v1/jobs/{second['job_id']}", headers=second_headers).json()
        second_still_waiting = client.get(f"/api/v1/jobs/{second['job_id']}", headers=second_headers).json()
        first_completed = client.get(f"/api/v1/jobs/{first['job_id']}", headers=first_headers).json()
        second_queued = client.get(f"/api/v1/jobs/{second['job_id']}", headers=second_headers).json()
        second_processing = client.get(f"/api/v1/jobs/{second['job_id']}", headers=second_headers).json()
        second_completed = client.get(f"/api/v1/jobs/{second['job_id']}", headers=second_headers).json()

        first_model = client.get(f"/api/v1/jobs/{first['job_id']}/model", headers=first_headers)
        second_model = client.get(f"/api/v1/jobs/{second['job_id']}/model", headers=second_headers)

    assert first_queued["status"] == "queued"
    assert first_processing["status"] == "processing"
    assert second_waiting["status"] == second_still_waiting["status"] == "queued"
    assert second_waiting["queue_position_is_approximate"] is True
    assert first_completed["status"] == "completed"
    assert second_queued["status"] == "queued"
    assert second_processing["status"] == "processing"
    assert second_completed["status"] == "completed"
    assert first["job_id"] != second["job_id"]
    assert first_model.content == second_model.content
    assert adapter.submission_count == 2
    assert service.storage.ensure_job(first["job_id"]).job_root != service.storage.ensure_job(second["job_id"]).job_root
