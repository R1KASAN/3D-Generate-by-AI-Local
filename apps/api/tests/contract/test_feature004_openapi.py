from fastapi.testclient import TestClient

from local3d.main import create_app


def test_public_job_contract_uses_relative_no_store_resources() -> None:
    document = TestClient(create_app()).get("/openapi.json").json()
    jobs = document["paths"]["/api/v1/jobs/{job_id}"]["get"]
    assert "X-Job-Token" in str(jobs)
    assert "/api/v1/jobs/{job_id}/cancel" in document["paths"]
    assert "/api/v1/jobs/{job_id}/model" in document["paths"]
    assert "/api/v1/jobs/{job_id}/download" in document["paths"]
