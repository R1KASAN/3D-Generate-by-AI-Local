from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local3d.adapters.generation.workflow_mapper import WorkflowMapper, WorkflowMappingError


def _write_manifest(tmp_path: Path) -> tuple[Path, Path, str]:
    workflow_path = tmp_path / "workflow.json"
    workflow = {
        "10": {"class_type": "LoadImage", "inputs": {"image": "placeholder.png", "unused": "keep"}},
        "20": {"class_type": "Hy3DExportMesh", "inputs": {"filename_prefix": "placeholder"}},
    }
    workflow_path.write_text(json.dumps(workflow, indent=2) + "\n")
    digest = hashlib.sha256(workflow_path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "workflow-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "api_workflow_path": workflow_path.name,
                "api_workflow_sha256": digest,
                "workflow_revision": "test-rev-1",
                "input_bindings": [{"node_id": "10", "field": "image"}],
                "output_binding": {"node_id": "20", "field": "filename_prefix"},
            },
            indent=2,
        )
        + "\n"
    )
    return manifest_path, workflow_path, digest


def test_mapper_changes_only_allowlisted_input_and_output_fields(tmp_path: Path) -> None:
    manifest_path, workflow_path, original_hash = _write_manifest(tmp_path)
    mapper = WorkflowMapper.from_manifest(manifest_path)

    mapped = mapper.map_request(input_path=tmp_path / "job" / "input.png", output_prefix="jobs/job-1/model")

    assert mapped["10"]["inputs"]["image"] == "input.png"
    assert mapped["20"]["inputs"]["filename_prefix"] == "jobs/job-1/model"
    assert mapped["10"]["inputs"]["unused"] == "keep"
    assert hashlib.sha256(workflow_path.read_bytes()).hexdigest() == original_hash


def test_mapper_rejects_output_prefix_traversal(tmp_path: Path) -> None:
    manifest_path, _workflow_path, _original_hash = _write_manifest(tmp_path)
    mapper = WorkflowMapper.from_manifest(manifest_path)

    with pytest.raises(WorkflowMappingError, match="output prefix"):
        mapper.map_request(input_path=tmp_path / "input.png", output_prefix="jobs/../escape/model")


def test_mapper_rejects_unknown_binding_without_mutating_source(tmp_path: Path) -> None:
    manifest_path, workflow_path, original_hash = _write_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["input_bindings"] = [{"node_id": "missing", "field": "image"}]
    manifest_path.write_text(json.dumps(manifest))
    mapper = WorkflowMapper.from_manifest(manifest_path)

    with pytest.raises(WorkflowMappingError, match="allowlisted"):
        mapper.map_request(input_path=tmp_path / "input.png", output_prefix="jobs/job-1/model")
    assert hashlib.sha256(workflow_path.read_bytes()).hexdigest() == original_hash


def test_mapper_requires_manifest_hash_to_match_source(tmp_path: Path) -> None:
    manifest_path, workflow_path, _original_hash = _write_manifest(tmp_path)
    workflow_path.write_text(workflow_path.read_text().replace("placeholder.png", "changed.png"))

    with pytest.raises(WorkflowMappingError, match="hash"):
        WorkflowMapper.from_manifest(manifest_path)
