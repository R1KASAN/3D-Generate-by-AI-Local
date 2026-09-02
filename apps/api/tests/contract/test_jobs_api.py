from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from local3d.main import create_app


FIXTURE = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"


def test_runtime_routes_match_the_public_openapi_contract() -> None:
    document = TestClient(create_app()).get("/openapi.json").json()
    expected = {
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}",
        "/api/v1/jobs/{job_id}/model",
        "/api/v1/jobs/{job_id}/download",
        "/api/v1/health/live",
        "/api/v1/health/ready",
    }

    assert expected <= set(document["paths"])


def test_create_job_returns_an_opaque_token_and_no_store_header() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("reference.png", FIXTURE.read_bytes(), "image/png")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["job_token"]
    assert "prompt_id" not in json.dumps(payload)
    assert response.headers["cache-control"] == "no-store"


def test_job_resources_require_the_header_token_and_return_glb_content() -> None:
    with TestClient(create_app()) as client:
        created = client.post(
            "/api/v1/jobs",
            files={"file": ("reference.png", FIXTURE.read_bytes(), "image/png")},
        )
        job_id = created.json()["job_id"]
        status = client.get(f"/api/v1/jobs/{job_id}", headers={"X-Job-Token": "wrong"})
        missing = client.get(f"/api/v1/jobs/{job_id}")
        unknown = client.get(f"/api/v1/jobs/{uuid4()}", headers={"X-Job-Token": "wrong"})
        model = client.get(f"/api/v1/jobs/{job_id}/model", headers={"X-Job-Token": "wrong"})
        download = client.get(
            f"/api/v1/jobs/{job_id}/download", headers={"X-Job-Token": "wrong"}
        )

    assert status.status_code == 404
    assert missing.status_code == 404
    assert unknown.status_code == 404
    assert status.json() == missing.json() == unknown.json()
    assert model.status_code in {404, 409}
    assert download.status_code in {404, 409}
