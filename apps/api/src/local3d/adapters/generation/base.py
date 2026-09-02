from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol
from uuid import UUID


class JobObservationStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    job_id: UUID
    input_path: Path
    output_dir: Path
    workflow_revision: str
    timeout_seconds: float
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class EngineHandle:
    """Adapter-private execution handle; no engine identifier is public."""

    internal_id: str
    public_id: None = None

    def __repr__(self) -> str:
        """Avoid leaking engine identifiers through logs or debug output."""

        return "EngineHandle(<private>, public_id=None)"


@dataclass(frozen=True, slots=True)
class EngineObservation:
    status: JobObservationStatus
    progress_percent: int | None = None
    candidates: tuple[Path, ...] = ()
    error_code: str | None = None
    safe_message: str | None = None


class GenerationAdapter(Protocol):
    """Stable backend-facing contract shared by mock and real adapters."""

    def submit(self, request: GenerationRequest) -> EngineHandle: ...

    def inspect(self, handle: EngineHandle) -> EngineObservation: ...
