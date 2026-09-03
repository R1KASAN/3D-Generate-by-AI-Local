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
