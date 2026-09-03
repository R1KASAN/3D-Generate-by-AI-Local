from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from local3d.config import Settings
from local3d.main import create_app
from local3d.api.dependencies import authorize_job
from local3d.services.job_service import JobService
from local3d.storage.job_storage import JobStorage, PathViolation


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"


def test_swapped_tokens_and_guessed_ids_have_uniform_404_without_disclosure(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
    with TestClient(create_app(settings)) as client:
        first = client.post("/api/v1/jobs", files={"file": ("one.png", FIXTURE.read_bytes(), "image/png")}).json()
        second = client.post("/api/v1/jobs", files={"file": ("two.png", FIXTURE.read_bytes(), "image/png")}).json()
        wrong_status = client.get(
            f"/api/v1/jobs/{second['job_id']}", headers={"X-Job-Token": first["job_token"]}
        )
        wrong_model = client.get(
            f"/api/v1/jobs/{second['job_id']}/model", headers={"X-Job-Token": first["job_token"]}
        )
        wrong_download = client.get(
            f"/api/v1/jobs/{second['job_id']}/download", headers={"X-Job-Token": first["job_token"]}
        )
        unknown = client.get(f"/api/v1/jobs/{uuid4()}", headers={"X-Job-Token": first["job_token"]})

    assert wrong_status.status_code == unknown.status_code == 404
    assert wrong_status.json() == unknown.json()
    assert wrong_model.status_code == wrong_download.status_code == 404
    assert "one.png" not in wrong_status.text
    assert "prompt" not in wrong_status.text.lower()


def test_expired_job_is_indistinguishable_on_status_preview_and_download(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
    service = JobService(settings)
    with TestClient(create_app(settings, service=service)) as client:
        created = client.post(
            "/api/v1/jobs",
            files={"file": ("expired.png", FIXTURE.read_bytes(), "image/png")},
        ).json()
        job = service._jobs[UUID(created["job_id"])]
        job.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        headers = {"X-Job-Token": created["job_token"]}
        responses = [
            client.get(f"/api/v1/jobs/{created['job_id']}", headers=headers),
            client.get(f"/api/v1/jobs/{created['job_id']}/model", headers=headers),
            client.get(f"/api/v1/jobs/{created['job_id']}/download", headers=headers),
        ]

    assert {response.status_code for response in responses} == {404}
    assert len({response.text for response in responses}) == 1


def test_job_storage_rejects_traversal_and_symlink_escape(tmp_path: Path) -> None:
    storage = JobStorage(tmp_path / "storage")
    job_id = uuid4()
    paths = storage.ensure_job(job_id)

    with pytest.raises(PathViolation):
        storage.resolve_path(job_id, "../outside.txt")

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    try:
        (paths.work_dir / "escape").symlink_to(outside)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is unavailable")
        raise
    with pytest.raises(PathViolation):
        storage.resolve_path(job_id, "work/escape")


def test_authorization_dependency_returns_none_for_missing_or_wrong_token() -> None:
    assert authorize_job(None, "digest") is False
    assert authorize_job("wrong", "digest") is False
