from __future__ import annotations

import hashlib
from pathlib import Path
import time

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
    assert first_processing["status"] == "running"
    assert second_waiting["status"] == second_still_waiting["status"] == "queued"
    assert second_waiting["queue_position_is_approximate"] is True
    assert first_completed["status"] == "completed"
    assert second_queued["status"] == "queued"
    assert second_processing["status"] == "running"
    assert second_completed["status"] == "completed"
    assert first["job_id"] != second["job_id"]
    assert first_model.content != second_model.content
    assert adapter.submission_count == 2
    assert service.storage.ensure_job(first["job_id"]).job_root != service.storage.ensure_job(second["job_id"]).job_root


def test_five_users_are_fifo_serial_and_get_distinct_results(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
    adapter = MockGenerationAdapter(fixture_path=MODEL)
    service = JobService(settings, adapter=adapter)
    with TestClient(create_app(settings, service=service)) as client:
        created = [
            client.post("/api/v1/jobs", files={"file": (f"{index}.png", FIXTURE.read_bytes(), "image/png")}).json()
            for index in range(5)
        ]
        observed: list[dict] = []
        max_running = 0
        saw_queued_while_running = False
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            observed = [
                client.get(f"/api/v1/jobs/{item['job_id']}", headers={"X-Job-Token": item["job_token"]}).json()
                for item in created
            ]
            max_running = max(max_running, sum(item["status"] == "running" for item in observed))
            saw_queued_while_running = saw_queued_while_running or (
                any(item["status"] == "running" for item in observed)
                and any(item["status"] == "queued" for item in observed)
            )
            if all(item["status"] == "completed" for item in observed):
                break
            time.sleep(0.05)
        downloads = [
            client.get(f"/api/v1/jobs/{item['job_id']}/download", headers={"X-Job-Token": item["job_token"]}).content
            for item in created
        ]
        cross_owner = client.get(
            f"/api/v1/jobs/{created[1]['job_id']}/download",
            headers={"X-Job-Token": created[0]["job_token"]},
        )
    assert all(item["status"] == "completed" for item in observed)
    assert max_running == 1
    assert saw_queued_while_running
    assert adapter.submission_count == 5
    assert len({item["job_id"] for item in observed}) == 5
    assert len({item["job_token"] for item in created}) == 5
    assert cross_owner.status_code == 404
    assert all(downloads)
    assert len(set(downloads)) == 5
    assert len({hashlib.sha256(item).hexdigest() for item in downloads}) == 5
    roots = [service.storage.ensure_job(item["job_id"]).job_root for item in created]
    assert len(set(roots)) == 5
    for created_job, root in zip(created, roots, strict=True):
        assert (root / "outputs" / "model.glb").is_file()
        assert str(created_job["job_id"]) in str(root)
