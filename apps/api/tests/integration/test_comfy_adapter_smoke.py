from __future__ import annotations

import os
import platform
from pathlib import Path
from uuid import uuid4

import pytest

from local3d.adapters.generation.base import GenerationRequest, JobObservationStatus

pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="requires the Windows NVIDIA ComfyUI server (T074); this file only "
    "collects and documents the skip on other platforms, per the Phase 7/8 "
    "hardware gate.",
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SHAPE_SMOKE_WORKFLOW = _REPO_ROOT / "workflows/hunyuan3d/api/hunyuan3d-21-shape-smoke.json"
_INPUT_FIXTURE = _REPO_ROOT / "fixtures/inputs/valid-reference.png"


def test_real_comfy_adapter_is_constructible() -> None:
    """T068: fails cleanly if the real adapter/runtime pieces are missing.

    This assertion has no live-server or RUN_COMFY_INTEGRATION requirement -
    it only proves the real GenerationAdapter exists and can be built from
    the pinned shape-smoke workflow, which is the "missing adapter/runtime"
    gate T068 exists to show failing before T072/T073 are implemented.
    """

    from local3d.adapters.generation.comfy import ComfyGenerationAdapter
    from local3d.adapters.generation.comfy_client import ComfyClient
    from local3d.adapters.generation.output_resolver import OutputResolver
    from local3d.adapters.generation.workflow_mapper import WorkflowBinding, WorkflowMapper

    mapper = WorkflowMapper(
        workflow_path=_SHAPE_SMOKE_WORKFLOW,
        input_bindings=(WorkflowBinding(node_id="1", field="image"),),
        output_binding=WorkflowBinding(node_id="3", field="filename_prefix"),
        expected_sha256=_sha256(_SHAPE_SMOKE_WORKFLOW),
    )
    adapter = ComfyGenerationAdapter(
        client=ComfyClient("http://127.0.0.1:8188"),
        mapper=mapper,
        resolver=OutputResolver(_comfyui_output_root()),
    )
    try:
        assert adapter is not None
    finally:
        adapter.close()


@pytest.mark.skipif(
    os.environ.get("RUN_COMFY_INTEGRATION") != "1",
    reason="set RUN_COMFY_INTEGRATION=1 with a live ComfyUI instance bound to "
    "127.0.0.1:8188 to run the real end-to-end submission (T074).",
)
def test_real_adapter_submits_and_resolves_one_glb_via_comfyui() -> None:
    """T074: full live submission through the real adapter against ComfyUI."""

    from local3d.adapters.generation.comfy import ComfyGenerationAdapter
    from local3d.adapters.generation.comfy_client import ComfyClient
    from local3d.adapters.generation.output_resolver import OutputResolver
    from local3d.adapters.generation.workflow_mapper import WorkflowBinding, WorkflowMapper

    mapper = WorkflowMapper(
        workflow_path=_SHAPE_SMOKE_WORKFLOW,
        input_bindings=(WorkflowBinding(node_id="1", field="image"),),
        output_binding=WorkflowBinding(node_id="3", field="filename_prefix"),
        expected_sha256=_sha256(_SHAPE_SMOKE_WORKFLOW),
    )
    adapter = ComfyGenerationAdapter(
        client=ComfyClient("http://127.0.0.1:8188"),
        mapper=mapper,
        resolver=OutputResolver(_comfyui_output_root()),
    )
    job_id = uuid4()
    request = GenerationRequest(
        job_id=job_id,
        input_path=_INPUT_FIXTURE,
        output_dir=_comfyui_output_root() / "jobs" / str(job_id),
        workflow_revision="shape-smoke-t074",
        timeout_seconds=180,
        idempotency_key=f"t074-{job_id}",
    )
    try:
        handle = adapter.submit(request)
        assert handle.public_id is None

        observation = None
        for _ in range(120):
            observation = adapter.inspect(handle)
            if observation.status in (JobObservationStatus.SUCCEEDED, JobObservationStatus.FAILED):
                break
            import time

            time.sleep(2)

        assert observation is not None
        assert observation.status is JobObservationStatus.SUCCEEDED
        assert len(observation.candidates) == 1
        candidate = observation.candidates[0]
        assert candidate.is_file()
        assert candidate.stat().st_size > 0
        assert candidate.suffix == ".glb"
    finally:
        adapter.close()


def _comfyui_output_root() -> Path:
    override = os.environ.get("COMFYUI_OUTPUT_ROOT")
    if override:
        return Path(override)
    return Path.home() / "ComfyUI" / "output"


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
