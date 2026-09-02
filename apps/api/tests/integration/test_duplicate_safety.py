from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from local3d.adapters.generation.base import GenerationRequest
from local3d.adapters.generation.mock import MockGenerationAdapter


FIXTURE = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def _request(tmp_path: Path, key: str) -> GenerationRequest:
    output_dir = tmp_path / key
    output_dir.mkdir(parents=True, exist_ok=True)
    return GenerationRequest(
        job_id=uuid4(),
        input_path=tmp_path / "input.png",
        output_dir=output_dir,
        workflow_revision="mock-rev-1",
        timeout_seconds=60,
        idempotency_key=key,
    )


def test_duplicate_adapter_submission_reuses_one_private_execution(tmp_path: Path) -> None:
    adapter = MockGenerationAdapter(fixture_path=FIXTURE)
    request = _request(tmp_path, "same-key")

    first = adapter.submit(request)
    second = adapter.submit(request)

    assert first == second
    assert adapter.submission_count == 1
    assert "prompt_id" not in repr(first).lower()
