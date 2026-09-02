from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..adapters.generation.base import EngineObservation, JobObservationStatus
from ..domain.jobs import JobState, SafeJobError


@dataclass(frozen=True, slots=True)
class CoordinationDecision:
    """A safe, engine-agnostic interpretation of one adapter observation."""

    target_state: JobState
    progress_percent: int | None = None
    progress_message: str | None = None
    candidates: tuple[Path, ...] = ()
    error: SafeJobError | None = None


class GenerationCoordinator:
    """Map private adapter observations to the public job state machine."""

    def decide(
        self,
        observation: EngineObservation | JobObservationStatus | str,
        *,
        progress_percent: int | None = None,
        error_code: str | None = None,
        safe_message: str | None = None,
        candidates: tuple[Path, ...] = (),
    ) -> CoordinationDecision:
        if isinstance(observation, EngineObservation):
            status = observation.status
            progress_percent = observation.progress_percent
            error_code = observation.error_code
            safe_message = observation.safe_message
            candidates = observation.candidates
        else:
            status = JobObservationStatus(observation)

        if status is JobObservationStatus.QUEUED:
            return CoordinationDecision(JobState.QUEUED)
        if status is JobObservationStatus.PROCESSING:
            supported_progress = progress_percent if progress_percent is None or 0 <= progress_percent <= 100 else None
            return CoordinationDecision(
                JobState.PROCESSING,
                progress_percent=supported_progress,
                progress_message="Generating model" if supported_progress is not None else None,
            )
        if status is JobObservationStatus.SUCCEEDED:
            return CoordinationDecision(JobState.COMPLETED, progress_percent=100, candidates=candidates)
        if status is JobObservationStatus.CANCELLED:
            return CoordinationDecision(
                JobState.CANCELLED,
                error=SafeJobError(code="generation_cancelled", message="Generation was cancelled"),
            )

        if status is JobObservationStatus.UNKNOWN:
            code = "generation_timeout" if error_code in {"generation_timeout", "timeout"} else "engine_unavailable"
            message = "Generation status is unavailable"
        else:
            code = error_code or "generation_failed"
            message = safe_message or "Generation failed"
        try:
            safe_error = SafeJobError(code=code, message=message)
        except ValueError:
            safe_error = SafeJobError(code="generation_failed", message="Generation failed")
        return CoordinationDecision(JobState.FAILED, error=safe_error)


def observe_engine(observation: EngineObservation) -> CoordinationDecision:
    """Functional entry point used by integrations and tests."""

    return GenerationCoordinator().decide(observation)
