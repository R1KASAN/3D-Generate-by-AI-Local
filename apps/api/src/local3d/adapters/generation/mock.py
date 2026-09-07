from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .base import EngineHandle, EngineObservation, GenerationRequest, JobObservationStatus


@dataclass
class _MockExecution:
    request: GenerationRequest
    calls: int = 0


def _write_isolated_fixture(source: Path, destination: Path, job_id: object) -> None:
    """Copy a valid fixture while giving each mock job distinct GLB bytes."""

    data = source.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("mock fixture is not a GLB")
    version, declared_length = struct.unpack_from("<II", data, 4)
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if version != 2 or declared_length != len(data) or chunk_type != 0x4E4F534A:
        raise ValueError("mock fixture has an unsupported GLB layout")

    document = json.loads(data[20 : 20 + chunk_length].decode("utf-8").rstrip(" \t\r\n\0"))
    asset = document.setdefault("asset", {})
    extras = asset.setdefault("extras", {})
    extras["local3d_mock_job"] = str(job_id)
    encoded = json.dumps(document, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    remaining_chunks = data[20 + chunk_length :]
    total_length = 12 + 8 + len(encoded) + len(remaining_chunks)
    destination.write_bytes(
        b"glTF"
        + struct.pack("<II", 2, total_length)
        + struct.pack("<II", len(encoded), 0x4E4F534A)
        + encoded
        + remaining_chunks
    )


class MockGenerationAdapter:
    """Deterministic fixture-backed adapter for macOS development."""

    def __init__(self, *, fixture_path: Path, mode: str = "success") -> None:
        if mode not in {"success", "failure", "missing", "timeout", "disconnect", "uncertain", "cancelled"}:
            raise ValueError("unsupported mock mode")
        self.fixture_path = Path(fixture_path)
        self.mode = mode
        self._executions: dict[str, _MockExecution] = {}
        self._idempotency: dict[str, EngineHandle] = {}
        self.workflow_revision = "mock-fixture-rev-1"

    def close(self) -> None:
        """Match the managed adapter lifecycle; the mock owns no resources."""
        return

    @property
    def submission_count(self) -> int:
        return len(self._executions)

    def is_live(self) -> bool:
        """The mock has no external engine to hang or disconnect."""
        return True

    def submit(self, request: GenerationRequest) -> EngineHandle:
        existing = self._idempotency.get(request.idempotency_key)
        if existing is not None:
            return existing
        request.output_dir.mkdir(parents=True, exist_ok=True)
        handle = EngineHandle(internal_id=uuid4().hex)
        self._executions[handle.internal_id] = _MockExecution(request=request)
        self._idempotency[request.idempotency_key] = handle
        return handle

    def inspect(self, handle: EngineHandle) -> EngineObservation:
        execution = self._executions.get(handle.internal_id)
        if execution is None:
            return EngineObservation(
                status=JobObservationStatus.UNKNOWN,
                error_code="unknown_execution",
                safe_message="Generation status is unavailable",
            )
        execution.calls += 1
        if self.mode == "failure" and execution.calls >= 2:
            return EngineObservation(
                status=JobObservationStatus.FAILED,
                error_code="generation_failed",
                safe_message="Generation failed",
            )
        if self.mode == "timeout" and execution.calls >= 2:
            return EngineObservation(
                status=JobObservationStatus.UNKNOWN,
                error_code="generation_timeout",
                safe_message="Generation status is unavailable",
            )
        if self.mode == "disconnect" and execution.calls >= 2:
            return EngineObservation(
                status=JobObservationStatus.UNKNOWN,
                error_code="engine_disconnect",
                safe_message="Generation status is unavailable",
            )
        if self.mode == "uncertain" and execution.calls >= 2:
            return EngineObservation(
                status=JobObservationStatus.UNKNOWN,
                error_code="unknown_execution",
                safe_message="Generation status is unavailable",
            )
        if self.mode == "cancelled" and execution.calls >= 2:
            return EngineObservation(
                status=JobObservationStatus.CANCELLED,
                error_code="generation_cancelled",
                safe_message="Generation was cancelled",
            )
        if execution.calls == 1:
            return EngineObservation(status=JobObservationStatus.QUEUED)
        if execution.calls == 2:
            return EngineObservation(status=JobObservationStatus.PROCESSING, progress_percent=50)
        candidate = execution.request.output_dir / "model.glb"
        if self.mode == "missing":
            return EngineObservation(status=JobObservationStatus.SUCCEEDED, candidates=())
        _write_isolated_fixture(self.fixture_path, candidate, execution.request.job_id)
        return EngineObservation(status=JobObservationStatus.SUCCEEDED, candidates=(candidate,))
