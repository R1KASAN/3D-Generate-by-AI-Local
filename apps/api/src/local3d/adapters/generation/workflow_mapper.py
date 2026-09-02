from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


class WorkflowMappingError(ValueError):
    """Raised when a workflow manifest or allowlisted mutation is invalid."""


@dataclass(frozen=True, slots=True)
class WorkflowBinding:
    node_id: str
    field: str


class WorkflowMapper:
    """Load an immutable API workflow and mutate only manifest-approved fields."""

    def __init__(
        self,
        *,
        workflow_path: Path,
        input_bindings: tuple[WorkflowBinding, ...],
        output_binding: WorkflowBinding,
        expected_sha256: str,
    ) -> None:
        self.workflow_path = Path(workflow_path).resolve()
        self.input_bindings = input_bindings
        self.output_binding = output_binding
        self.expected_sha256 = expected_sha256
        self._verify_source_hash()

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> "WorkflowMapper":
        manifest_file = Path(manifest_path).resolve()
        try:
            manifest = json.loads(manifest_file.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowMappingError("workflow manifest is invalid") from exc
        if not isinstance(manifest, dict):
            raise WorkflowMappingError("workflow manifest is invalid")
        workflow_name = manifest.get("api_workflow_path")
        expected_hash = manifest.get("api_workflow_sha256")
        raw_inputs = manifest.get("input_bindings")
        raw_output = manifest.get("output_binding")
        if not isinstance(workflow_name, str) or not isinstance(expected_hash, str):
            raise WorkflowMappingError("workflow manifest is incomplete")
        if not isinstance(raw_inputs, list) or not isinstance(raw_output, dict):
            raise WorkflowMappingError("workflow manifest bindings are invalid")
        input_bindings = tuple(_parse_binding(item) for item in raw_inputs)
        output_binding = _parse_binding(raw_output)
        workflow_path = (manifest_file.parent / workflow_name).resolve()
        if not workflow_path.is_relative_to(manifest_file.parent):
            raise WorkflowMappingError("workflow source must remain beside the manifest")
        return cls(
            workflow_path=workflow_path,
            input_bindings=input_bindings,
            output_binding=output_binding,
            expected_sha256=expected_hash,
        )

    def map_request(self, *, input_path: Path, output_prefix: str) -> dict[str, Any]:
        self._verify_source_hash()
        _validate_output_prefix(output_prefix)
        try:
            workflow = json.loads(self.workflow_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowMappingError("workflow source is invalid") from exc
        if not isinstance(workflow, dict):
            raise WorkflowMappingError("workflow source is invalid")
        mapped = copy.deepcopy(workflow)
        input_name = Path(input_path).name
        if not input_name or input_name in {".", ".."}:
            raise WorkflowMappingError("input path is invalid")
        for binding in self.input_bindings:
            _set_allowlisted_field(mapped, binding, input_name)
        _set_allowlisted_field(mapped, self.output_binding, output_prefix)
        return mapped

    def _verify_source_hash(self) -> None:
        try:
            digest = hashlib.sha256(self.workflow_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise WorkflowMappingError("workflow source is unavailable") from exc
        if digest != self.expected_sha256:
            raise WorkflowMappingError("workflow source hash does not match manifest")


def _parse_binding(raw: Any) -> WorkflowBinding:
    node_id: Any = None
    field: Any = None
    if isinstance(raw, str):
        parts = raw.split(".", 1)
        if len(parts) != 2:
            raise WorkflowMappingError("workflow binding is invalid")
        node_id, field = parts
    elif isinstance(raw, dict):
        node_id, field = raw.get("node_id"), raw.get("field")
    else:
        raise WorkflowMappingError("workflow binding is invalid")
    if not isinstance(node_id, str) or not node_id or not isinstance(field, str) or not field:
        raise WorkflowMappingError("workflow binding is invalid")
    if field.startswith("inputs."):
        field = field.removeprefix("inputs.")
    return WorkflowBinding(node_id=node_id, field=field)


def _set_allowlisted_field(workflow: dict[str, Any], binding: WorkflowBinding, value: str) -> None:
    node = workflow.get(binding.node_id)
    if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
        raise WorkflowMappingError("allowlisted workflow binding is missing")
    inputs = node["inputs"]
    if binding.field not in inputs:
        raise WorkflowMappingError("allowlisted workflow binding is missing")
    inputs[binding.field] = value


def _validate_output_prefix(output_prefix: str) -> None:
    if not output_prefix or "\x00" in output_prefix:
        raise WorkflowMappingError("output prefix is invalid")
    posix = PurePosixPath(output_prefix)
    windows = PureWindowsPath(output_prefix)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
        raise WorkflowMappingError("output prefix must remain inside the job output root")
