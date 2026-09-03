from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePath
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobState(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES = frozenset({JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED})
ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.QUEUED: frozenset({JobState.PROCESSING, JobState.FAILED, JobState.CANCELLED}),
    JobState.PROCESSING: frozenset({JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}),
    JobState.COMPLETED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
}


class InvalidJobTransition(ValueError):
    """Raised when a job state transition violates the domain state machine."""


_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_UNSAFE_MESSAGE = re.compile(
    r"(?i)(traceback|stack trace|/private/|/storage/|\\storage\\|[a-z]:\\|\.glb\b|\n|\r)"
)


@dataclass(frozen=True, slots=True)
class SafeJobError:
    code: str
    message: str

    def __post_init__(self) -> None:
        if not _SAFE_CODE.fullmatch(self.code):
            raise ValueError("safe error code is invalid")
        if not self.message or len(self.message) > 240 or _UNSAFE_MESSAGE.search(self.message):
            raise ValueError("safe error message contains unsafe detail")


class AssetKind(str, Enum):
    INPUT = "input"
    INTERMEDIATE = "intermediate"
    OUTPUT = "output"


@dataclass(slots=True)
class JobAsset:
    asset_id: UUID = field(default_factory=uuid4)
    job_id: UUID = field(default_factory=uuid4)
    kind: AssetKind = AssetKind.INPUT
    relative_path: str = ""
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    sha256: str = ""
    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.kind = AssetKind(self.kind)
        if self.size_bytes < 0:
            raise ValueError("asset size cannot be negative")
        path = PurePath(self.relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("asset path must remain relative to the job root")
        if self.sha256 and not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("asset sha256 must be lowercase hexadecimal")


@dataclass(slots=True)
class JobEvent:
    job_id: UUID
    sequence: int
    event_type: str
    from_status: JobState | None = None
    to_status: JobState | None = None
    progress_percent: int | None = None
    safe_message: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class GenerationJob:
    job_id: UUID = field(default_factory=uuid4)
    token_digest: str = ""
    status: JobState = JobState.QUEUED
    progress_percent: int | None = None
    progress_message: str | None = None
    engine_job_id: str | None = None
    workflow_revision: str = ""
    input_asset_id: UUID | None = None
    output_asset_id: UUID | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempt_count: int = 0
    created_at: datetime = field(default_factory=utc_now)
    queued_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    expires_at: datetime | None = None
    updated_at: datetime | None = None
    _event_sequence: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        self.status = JobState(self.status)
        if self.queued_at is None:
            self.queued_at = self.created_at
        if self.expires_at is None:
            self.expires_at = self.created_at
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.attempt_count < 0:
            raise ValueError("attempt_count cannot be negative")
        self._validate_progress(self.progress_percent)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATES

    def update_progress(self, progress_percent: int | None, message: str | None = None) -> None:
        if self.is_terminal:
            raise InvalidJobTransition("terminal jobs cannot receive progress updates")
        self._validate_progress(progress_percent)
        if message is not None:
            SafeJobError(code="progress", message=message)
        self.progress_percent = progress_percent
        self.progress_message = message
        self.updated_at = utc_now()

    def record_progress(self, progress_percent: int | None, message: str | None = None) -> JobEvent:
        if self.status is not JobState.PROCESSING:
            raise InvalidJobTransition("only processing jobs can record progress")
        self.update_progress(progress_percent, message)
        self._event_sequence += 1
        return JobEvent(
            job_id=self.job_id,
            sequence=self._event_sequence,
            event_type="progress",
            from_status=JobState.PROCESSING,
            to_status=JobState.PROCESSING,
            progress_percent=self.progress_percent,
            safe_message=self.progress_message,
            created_at=self.updated_at or utc_now(),
        )

    def transition(
        self,
        target: JobState | str,
        *,
        now: datetime | None = None,
        progress_percent: int | None = None,
        progress_message: str | None = None,
        output_asset_id: UUID | None = None,
        error: SafeJobError | None = None,
    ) -> JobEvent:
        target_state = JobState(target)
        if target_state not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidJobTransition(f"cannot transition {self.status.value} to {target_state.value}")
        if target_state is JobState.COMPLETED and output_asset_id is None:
            raise InvalidJobTransition("completed jobs require exactly one output asset")
        if target_state is JobState.COMPLETED and self.output_asset_id is not None:
            raise InvalidJobTransition("completed jobs cannot replace an output asset")

        timestamp = now or utc_now()
        self._validate_progress(progress_percent)
        previous = self.status
        self.status = target_state
        self.updated_at = timestamp
        if progress_percent is not None or progress_message is not None:
            self.progress_percent = progress_percent
            self.progress_message = progress_message
        if target_state is JobState.PROCESSING:
            self.started_at = timestamp
        if target_state is JobState.COMPLETED:
            self.output_asset_id = output_asset_id
            self.finished_at = timestamp
        if target_state in {JobState.FAILED, JobState.CANCELLED}:
            safe_error = error or SafeJobError(code="generation_failed", message="Generation failed")
            self.error_code = safe_error.code
            self.error_message = safe_error.message
            self.finished_at = timestamp

        self._event_sequence += 1
        return JobEvent(
            job_id=self.job_id,
            sequence=self._event_sequence,
            event_type="state_changed",
            from_status=previous,
            to_status=target_state,
            progress_percent=self.progress_percent,
            safe_message=self.error_message or self.progress_message,
            created_at=timestamp,
        )

    def model_snapshot(self) -> dict[str, Any]:
        return {
            "job_id": str(self.job_id),
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "progress_message": self.progress_message,
            "output_asset_id": str(self.output_asset_id) if self.output_asset_id else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }

    @staticmethod
    def _validate_progress(progress_percent: int | None) -> None:
        if progress_percent is not None and not 0 <= progress_percent <= 100:
            raise ValueError("progress must be between 0 and 100")
