from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta, timezone
from uuid import UUID

from .base import EngineHandle, EngineObservation, GenerationRequest, JobObservationStatus
from .comfy_client import ComfyClient, ComfyClientError
from .output_resolver import OutputDiscoveryError, OutputResolver
from .workflow_mapper import WorkflowMapper, WorkflowMappingError


class ComfyGenerationAdapter:
    """Real ``GenerationAdapter`` backed by a loopback ComfyUI instance.

    ``JobService`` calls ``submit``/``inspect`` synchronously (it awaits its
    own methods, not the adapter's), while ``ComfyClient`` is fully async
    because it performs real network I/O. This class bridges the two by
    running a dedicated background event loop for its lifetime and blocking
    the calling thread on the result, the same pattern used to embed an
    async client behind a sync interface.
    """

    def __init__(
        self,
        *,
        client: ComfyClient,
        mapper: WorkflowMapper,
        resolver: OutputResolver,
        output_prefix_pattern: str = "jobs/{job_id}/model",
    ) -> None:
        self._client = client
        self._mapper = mapper
        self._resolver = resolver
        self._output_prefix_pattern = output_prefix_pattern
        self._submitted_at: dict[str, tuple[datetime, float, UUID]] = {}
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="comfy-adapter-loop", daemon=True
        )
        self._thread.start()

    def close(self) -> None:
        async def _shutdown() -> None:
            await self._client.aclose()

        try:
            asyncio.run_coroutine_threadsafe(_shutdown(), self._loop).result(timeout=5)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    def _run(self, coro):  # type: ignore[no-untyped-def]
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def submit(self, request: GenerationRequest) -> EngineHandle:
        output_prefix = self._output_prefix_pattern.format(job_id=request.job_id)
        try:
            workflow = self._mapper.map_request(
                input_path=request.input_path, output_prefix=output_prefix
            )
            uploaded_name = self._run(self._client.upload_image(request.input_path))
            _set_load_image_binding(workflow, self._mapper, uploaded_name)
            handle = self._run(self._client.submit(workflow))
        except (WorkflowMappingError, ComfyClientError) as exc:
            raise RuntimeError("real adapter submission failed") from exc
        self._submitted_at[handle.internal_id] = (
            datetime.now(timezone.utc),
            request.timeout_seconds,
            request.job_id,
        )
        return handle

    def inspect(self, handle: EngineHandle) -> EngineObservation:
        try:
            observation = self._run(self._client.reconcile(handle))
        except ComfyClientError:
            return EngineObservation(
                status=JobObservationStatus.UNKNOWN,
                error_code="engine_unavailable",
                safe_message="Generation status is unavailable",
            )

        tracked = self._submitted_at.get(handle.internal_id)
        if (
            tracked is not None
            and observation.status in (JobObservationStatus.QUEUED, JobObservationStatus.PROCESSING)
        ):
            submitted_at, timeout_seconds, _ = tracked
            if datetime.now(timezone.utc) - submitted_at > timedelta(seconds=timeout_seconds):
                return EngineObservation(
                    status=JobObservationStatus.UNKNOWN,
                    error_code="generation_timeout",
                    safe_message="Generation status is unavailable",
                )

        if observation.status is not JobObservationStatus.SUCCEEDED:
            return observation

        # Per the workflow manifest contract, ComfyUI's own reported success
        # is provisional (Hy3DExportMesh may return a bare string path
        # rather than a normal UI output entry): the source of truth is
        # scanning the job's own output directory for exactly one fresh GLB.
        job_id = tracked[2] if tracked is not None else None
        if job_id is None:
            return EngineObservation(status=JobObservationStatus.SUCCEEDED, candidates=())
        try:
            resolved = self._resolver.resolve(job_id)
        except OutputDiscoveryError:
            return EngineObservation(status=JobObservationStatus.SUCCEEDED, candidates=())
        return EngineObservation(status=JobObservationStatus.SUCCEEDED, candidates=(resolved,))


def _set_load_image_binding(workflow: dict, mapper: WorkflowMapper, uploaded_name: str) -> None:
    """Overwrite the input binding(s) with the server-side uploaded filename.

    ``WorkflowMapper.map_request`` already wrote the local file's basename
    into the allowlisted binding; ComfyUI only recognizes a name that exists
    under its own ``input/`` directory, which is whatever ``upload_image``
    returned (it may differ from the local name on collision).
    """

    for binding in mapper.input_bindings:
        node = workflow.get(binding.node_id)
        if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
            node["inputs"][binding.field] = uploaded_name
