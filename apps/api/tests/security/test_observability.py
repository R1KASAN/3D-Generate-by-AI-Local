from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from local3d.config import Settings
from local3d.main import create_app
from local3d.observability.logging import configure_logging, log_job_event


def test_structured_logs_allow_safe_diagnostics_and_redact_sensitive_sentinels(
    caplog,
) -> None:
    logger = configure_logging("local3d.observability.contract")
    job_id = uuid4()
    caplog.set_level(logging.INFO, logger=logger.name)

    log_job_event(
        logger,
        job_id=job_id,
        event_type="failed",
        safe_message="Generation failed",
        details={
            "duration_ms": 1234,
            "failure_category": "engine_timeout",
            "token": "secret-token-sentinel",
            "filename": "private-input-sentinel.png",
            "path": "C:/private/storage/input.png",
            "engine_id": "prompt-secret-sentinel",
            "temporary_url": "https://secret.trycloudflare.com",
            "authorization": "Bearer secret-header-sentinel",
        },
    )

    text = caplog.text
    assert str(job_id) in text
    assert "failed" in text
    assert "Generation failed" in text
    assert "duration_ms" in text
    assert "failure_category" in text
    for sentinel in (
        "secret-token-sentinel",
        "private-input-sentinel.png",
        "C:/private/storage/input.png",
        "prompt-secret-sentinel",
        "secret.trycloudflare.com",
        "secret-header-sentinel",
    ):
        assert sentinel not in text


def test_job_lifecycle_logs_safe_transition_fields_without_credentials(tmp_path: Path, caplog) -> None:
    fixture = Path(__file__).parents[4] / "fixtures/inputs/valid-reference.png"
    settings = Settings(storage_root=tmp_path / "storage", database_path=tmp_path / "jobs.sqlite3")
    caplog.set_level(logging.INFO)
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/jobs",
            files={"file": ("reference.png", fixture.read_bytes(), "image/png")},
        )
        assert response.status_code == 201

    text = caplog.text
    assert "event=accepted" in text
    assert "to_state=queued" in text
    assert response.json()["job_token"] not in text
