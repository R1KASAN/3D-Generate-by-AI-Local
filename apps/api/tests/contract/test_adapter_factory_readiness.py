from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from local3d.config import Settings
from local3d.main import create_app


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    root = tmp_path / "storage"
    return Settings(
        storage_root=root,
        database_path=root / "jobs.sqlite3",
        **overrides,  # type: ignore[arg-type]
    )


def test_mock_adapter_readiness_is_unaffected(tmp_path: Path) -> None:
    """Regression guard: the default mock path must stay green (T073)."""

    with TestClient(create_app(_settings(tmp_path))) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_mock_adapter_engine_liveness_is_always_ok(tmp_path: Path) -> None:
    """Feature 003 FR-025: /health/engine is distinct from /health/ready.
    The mock adapter has no external engine to hang or disconnect."""

    with TestClient(create_app(_settings(tmp_path))) as client:
        response = client.get("/api/v1/health/engine")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_comfyui_adapter_with_invalid_manifest_fails_closed(tmp_path: Path) -> None:
    """An unusable real manifest must not crash the app; /ready must be 503."""

    settings = _settings(
        tmp_path,
        generation_adapter="comfyui",
        workflow_manifest_path=tmp_path / "does-not-exist.json",
        comfyui_output_root=tmp_path / "comfy-output",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
        # /live must remain unaffected - the process itself is healthy.
        assert client.get("/api/v1/health/live").status_code == 200


def test_comfyui_adapter_with_valid_manifest_is_ready(tmp_path: Path) -> None:
    """A complete, hash-matching manifest builds the real adapter and reports ready."""

    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "1": {"class_type": "LoadImage", "inputs": {"image": "placeholder.png"}},
                "2": {
                    "class_type": "Hy3DExportMesh",
                    "inputs": {"filename_prefix": "jobs/placeholder/model"},
                },
            }
        )
    )
    import hashlib

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "workflow_revision": "contract-rev-1",
                "api_workflow_path": "workflow.json",
                "api_workflow_sha256": hashlib.sha256(workflow_path.read_bytes()).hexdigest(),
                "input_bindings": ["1.image"],
                "output_binding": {"node_id": "2", "field": "filename_prefix"},
            }
        )
    )
    settings = _settings(
        tmp_path,
        generation_adapter="comfyui",
        workflow_manifest_path=manifest_path,
        comfyui_output_root=tmp_path / "comfy-output",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert client.app.state.job_service.workflow_revision == "contract-rev-1"


def test_comfyui_adapter_with_no_live_engine_is_ready_but_not_live(tmp_path: Path) -> None:
    """Feature 003 FR-025/SC-008: a real adapter with a valid manifest is
    'ready' (startup config passed) even when no ComfyUI is actually
    listening - /health/ready must not regress (it never made a network
    call). /health/engine is the endpoint that must catch this: it makes a
    real, short-timeout probe and must report unavailable when nothing
    answers on the configured loopback port."""

    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "1": {"class_type": "LoadImage", "inputs": {"image": "placeholder.png"}},
                "2": {
                    "class_type": "Hy3DExportMesh",
                    "inputs": {"filename_prefix": "jobs/placeholder/model"},
                },
            }
        )
    )
    import hashlib as _hashlib

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "api_workflow_path": "workflow.json",
                "api_workflow_sha256": _hashlib.sha256(workflow_path.read_bytes()).hexdigest(),
                "input_bindings": ["1.image"],
                "output_binding": {"node_id": "2", "field": "filename_prefix"},
            }
        )
    )
    settings = _settings(
        tmp_path,
        generation_adapter="comfyui",
        workflow_manifest_path=manifest_path,
        comfyui_output_root=tmp_path / "comfy-output",
        comfyui_base_url="http://127.0.0.1:8199",  # a port nothing listens on
    )
    with TestClient(create_app(settings)) as client:
        ready_response = client.get("/api/v1/health/ready")
        assert ready_response.status_code == 200, "readiness is a startup/config check and must not regress"

        engine_response = client.get("/api/v1/health/engine")
        assert engine_response.status_code == 503
        assert engine_response.json() == {"status": "unavailable"}
        body_text = json.dumps(engine_response.json())
        assert "8199" not in body_text and "127.0.0.1" not in body_text, (
            "the unavailable response must never leak the engine's internal address or port"
        )
