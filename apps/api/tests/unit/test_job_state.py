from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from local3d.domain.jobs import (
    GenerationJob,
    InvalidJobTransition,
    JobState,
    SafeJobError,
)


def test_queued_job_can_enter_processing_and_processing_can_complete() -> None:
    job = GenerationJob(job_id=uuid4())
    output_asset_id = uuid4()

    job.transition(JobState.PROCESSING)
    job.transition(JobState.COMPLETED, output_asset_id=output_asset_id)

    assert job.status is JobState.COMPLETED
    assert job.output_asset_id == output_asset_id
    assert job.started_at is not None
    assert job.finished_at is not None


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (JobState.QUEUED, JobState.FAILED),
        (JobState.QUEUED, JobState.CANCELLED),
        (JobState.PROCESSING, JobState.FAILED),
        (JobState.PROCESSING, JobState.CANCELLED),
    ],
)
def test_failure_and_cancellation_are_valid_from_active_states(
    from_state: JobState, to_state: JobState
) -> None:
    job = GenerationJob(job_id=uuid4(), status=from_state)

    job.transition(to_state, error=SafeJobError(code="generation_failed", message="Generation failed"))

    assert job.status is to_state
    assert job.finished_at is not None
    assert job.error_code == "generation_failed"


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (JobState.PROCESSING, JobState.QUEUED),
        (JobState.COMPLETED, JobState.PROCESSING),
        (JobState.FAILED, JobState.QUEUED),
        (JobState.CANCELLED, JobState.PROCESSING),
    ],
)
def test_forbidden_transitions_raise_and_preserve_state(
    from_state: JobState, to_state: JobState
) -> None:
    job = GenerationJob(job_id=uuid4(), status=from_state)
    finished_at = job.finished_at

    with pytest.raises(InvalidJobTransition):
        job.transition(to_state)

    assert job.status is from_state
    assert job.finished_at == finished_at


def test_terminal_states_are_immutable_even_when_a_recovery_is_requested() -> None:
    job = GenerationJob(job_id=uuid4(), status=JobState.COMPLETED, output_asset_id=uuid4())
    original = job.model_snapshot()

    with pytest.raises(InvalidJobTransition):
        job.transition(JobState.FAILED, error=SafeJobError(code="recovery", message="Retry later"))

    assert job.model_snapshot() == original


def test_completed_requires_exactly_one_output_reference() -> None:
    job = GenerationJob(job_id=uuid4(), status=JobState.PROCESSING)

    with pytest.raises(InvalidJobTransition, match="output"):
        job.transition(JobState.COMPLETED)


def test_progress_is_nullable_but_when_present_is_bounded() -> None:
    job = GenerationJob(job_id=uuid4())

    job.transition(JobState.PROCESSING, progress_percent=None)
    assert job.progress_percent is None

    with pytest.raises(ValueError, match="progress"):
        job.update_progress(101, "Too far")


def test_processing_job_records_repeated_progress_without_state_transition() -> None:
    job = GenerationJob()
    job.transition(JobState.PROCESSING, progress_percent=10)

    event = job.record_progress(20, "Generating model")

    assert job.status is JobState.PROCESSING
    assert job.progress_percent == 20
    assert event.event_type == "progress"
    assert event.from_status is event.to_status is JobState.PROCESSING


def test_safe_error_rejects_internal_details() -> None:
    with pytest.raises(ValueError, match="safe"):
        SafeJobError(code="bad", message="Traceback: /private/storage/jobs/secret.glb")


def test_timestamps_are_utc_aware() -> None:
    job = GenerationJob(job_id=uuid4())

    assert job.created_at.tzinfo == timezone.utc
    assert isinstance(job.created_at, datetime)
