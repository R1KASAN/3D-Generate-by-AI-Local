from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from local3d.adapters.generation.base import GenerationRequest, JobObservationStatus
from local3d.adapters.generation.mock import MockGenerationAdapter


FIXTURE = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def _request(tmp_path: Path, job_id) -> GenerationRequest:
    output_dir = tmp_path / str(job_id)
    output_dir.mkdir()
    return GenerationRequest(
        job_id=job_id,
        input_path=tmp_path / "input.png",
        output_dir=output_dir,
        workflow_revision="mock-rev-1",
        timeout_seconds=60,
        idempotency_key=f"mock-{job_id}",
    )


def test_mock_adapter_progresses_to_one_isolated_textured_candidate(tmp_path: Path) -> None:
    adapter = MockGenerationAdapter(fixture_path=FIXTURE)
    first_id, second_id = uuid4(), uuid4()

    first = adapter.submit(_request(tmp_path, first_id))
    second = adapter.submit(_request(tmp_path, second_id))
    first_observations = [adapter.inspect(first) for _ in range(3)]
    second_observations = [adapter.inspect(second) for _ in range(3)]

    assert first_observations[-1].status is JobObservationStatus.SUCCEEDED
    assert second_observations[-1].status is JobObservationStatus.SUCCEEDED
    assert first_observations[-1].candidates[0].is_relative_to(tmp_path / str(first_id))
    assert second_observations[-1].candidates[0].is_relative_to(tmp_path / str(second_id))
    assert first_observations[-1].candidates[0] != second_observations[-1].candidates[0]


def test_engine_handle_is_opaque_and_does_not_expose_prompt_ids(tmp_path: Path) -> None:
    adapter = MockGenerationAdapter(fixture_path=FIXTURE)
    handle = adapter.submit(_request(tmp_path, uuid4()))

    assert handle.public_id is None
    assert "prompt_id" not in repr(handle).lower()

