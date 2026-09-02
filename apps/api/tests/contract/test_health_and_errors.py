from __future__ import annotations

import logging
from uuid import uuid4

import pytest

from local3d.api.errors import map_exception
from local3d.api.health import health_payload
from local3d.observability.logging import configure_logging, log_job_event


def test_health_payload_exposes_only_allowed_status() -> None:
    assert health_payload("ok") == {"status": "ok"}
    assert health_payload("degraded") == {"status": "degraded"}

    with pytest.raises(ValueError):
        health_payload("database path: /private/jobs.sqlite3")


def test_internal_errors_are_mapped_to_a_safe_public_message() -> None:
    mapped = map_exception(
        RuntimeError("Traceback: /private/storage/jobs/secret.glb prompt_id=abc"),
        job_id=uuid4(),
    )

    assert mapped.status_code == 500
    assert mapped.body == {
        "error": {"code": "internal_error", "message": "The job could not be completed."}
    }
    assert "private" not in str(mapped.body).lower()
    assert "prompt_id" not in str(mapped.body)


def test_structured_job_logging_keeps_job_id_but_drops_sensitive_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = configure_logging("local3d.test")
    job_id = uuid4()
    caplog.set_level(logging.INFO, logger="local3d.test")

    log_job_event(
        logger,
        job_id=job_id,
        event_type="accepted",
        safe_message="Job accepted",
        details={
            "token": "raw-token-must-not-appear",
            "filename": "private-input.png",
            "path": "/private/storage/jobs/secret/input.png",
            "basic_authorization": "Basic c2VjcmV0",
        },
    )

    text = caplog.text
    assert str(job_id) in text
    assert "accepted" in text
    assert "Job accepted" in text
    for forbidden in ("raw-token-must-not-appear", "private-input.png", "/private/storage", "Basic"):
        assert forbidden not in text
