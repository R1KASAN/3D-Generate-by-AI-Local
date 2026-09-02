from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .base import EngineHandle, EngineObservation, GenerationRequest, JobObservationStatus


@dataclass
class _MockExecution:
    request: GenerationRequest
    calls: int = 0


class MockGenerationAdapter:
    """Deterministic fixture-backed adapter for macOS development."""

    def __init__(self, *, fixture_path: Path, mode: str = "success") -> None:
        if mode not in {"success", "failure", "missing", "timeout", "disconnect", "uncertain", "cancelled"}:
            raise ValueError("unsupported mock mode")
        self.fixture_path = Path(fixture_path)
        self.mode = mode
        self._executions: dict[str, _MockExecution] = {}
        self._idempotency: dict[str, EngineHandle] = {}

    @property
    def submission_count(self) -> int:
        return len(self._executions)

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
        shutil.copyfile(self.fixture_path, candidate)
        return EngineObservation(status=JobObservationStatus.SUCCEEDED, candidates=(candidate,))
