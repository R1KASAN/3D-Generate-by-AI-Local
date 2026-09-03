from __future__ import annotations

import asyncio
import logging
import shutil
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from ..adapters.generation.base import EngineHandle, GenerationAdapter, GenerationRequest
from ..adapters.generation.mock import MockGenerationAdapter
from ..config import Settings
from ..domain.jobs import AssetKind, GenerationJob, JobAsset, JobState, SafeJobError
from ..persistence.database import Database
from ..persistence.jobs import JobRepository
from ..storage.job_storage import JobStorage
from .glb_publication import PublicationError, publish_glb
from .generation_coordinator import GenerationCoordinator
from .image_validation import ensure_disk_admission, validate_upload
from .job_tokens import create_job_token, verify_job_token
from .serial_dispatcher import SerialDispatcher


logger = logging.getLogger(__name__)


class JobNotFoundError(LookupError):
    """Unknown, expired, or unauthorized job; callers must return uniform 404."""


class ResultNotReadyError(RuntimeError):
    """Job is known and authorized but has no completed result."""


class ExpiredJobError(RuntimeError):
    """Terminal job is outside its retention window."""


class JobService:
    def __init__(
        self,
        settings: Settings,
        *,
        database: Database | None = None,
        storage: JobStorage | None = None,
        adapter: GenerationAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.storage = storage or JobStorage(settings.storage_root)
        fixture = Path(__file__).resolve().parents[5] / "fixtures/models/sample-textured.glb"
        if adapter is None:
            if settings.generation_adapter != "mock":
                raise RuntimeError("ComfyUI generation adapter is not configured")
            adapter = MockGenerationAdapter(fixture_path=fixture)
        self.adapter: GenerationAdapter = adapter
        self.repository = JobRepository(self.database)
        self._jobs: dict[UUID, GenerationJob] = {}
        self._handles: dict[UUID, EngineHandle] = {}
        self._requests: dict[UUID, GenerationRequest] = {}
        self.dispatcher = SerialDispatcher()
        self.coordinator = GenerationCoordinator()
        self._advance_lock = asyncio.Lock()
        self._worker_task: asyncio.Task[None] | None = None

    async def startup(self) -> None:
        await self.database.initialize()
        await self.cleanup_expired(datetime.now(timezone.utc))

    async def cleanup_expired(self, now: datetime) -> list[UUID]:
        """Remove expired terminal job files before deleting their metadata."""
        removed: list[UUID] = []
        for job_id in await self.repository.list_expired_terminal(now):
            self.storage.remove_job(job_id)
            await self.repository.delete_job(job_id)
            self._jobs.pop(job_id, None)
            self._handles.pop(job_id, None)
            self._requests.pop(job_id, None)
            removed.append(job_id)
        return removed

    def start_maintenance(self, *, interval_seconds: float = 300) -> asyncio.Task[None]:
        if interval_seconds <= 0:
            raise ValueError("maintenance interval must be positive")
        return asyncio.create_task(self._maintenance_loop(interval_seconds))

    async def stop_maintenance(self, task: asyncio.Task[None]) -> None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    def start_worker(self, *, interval_seconds: float = 1.0) -> asyncio.Task[None]:
        """Start the in-process queue worker that advances jobs without polling clients."""
        if interval_seconds <= 0:
            raise ValueError("worker interval must be positive")
        if self._worker_task is not None and not self._worker_task.done():
            raise RuntimeError("queue worker is already running")
        self._worker_task = asyncio.create_task(self._worker_loop(interval_seconds))
        return self._worker_task

    async def stop_worker(self, task: asyncio.Task[None]) -> None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        if self._worker_task is task:
            self._worker_task = None

    async def _worker_loop(self, interval_seconds: float) -> None:
        while True:
            try:
                await self._advance_next_queued_job()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Keep a transient adapter/database failure from permanently
                # stopping queue progress; the next iteration retries safely.
                logger.exception("background generation worker iteration failed")
            await asyncio.sleep(interval_seconds)

    async def _advance_next_queued_job(self) -> None:
        active_id = self.dispatcher.active_job
        if active_id is not None:
            job = self._jobs.get(UUID(active_id))
            if job is None:
                job = await self.repository.get_job(UUID(active_id))
                if job is not None:
                    self._jobs[job.job_id] = job
            if job is not None:
                await self._advance(job)
            return

        pending = self.dispatcher.pending
        if not pending:
            return
        job_id = UUID(pending[0])
        job = self._jobs.get(job_id)
        if job is None:
            job = await self.repository.get_job(job_id)
            if job is not None:
                self._jobs[job.job_id] = job
        if job is not None:
            await self._advance(job)

    async def _maintenance_loop(self, interval_seconds: float) -> None:
        while True:
            await asyncio.sleep(interval_seconds)
            await self.cleanup_expired(datetime.now(timezone.utc))

    async def rehydrate_queued(self, job: GenerationJob) -> bool:
        """Restore an accepted, never-submitted job into the serial dispatcher."""
        if job.status is not JobState.QUEUED or job.input_asset_id is None or job.attempt_count != 0:
            return False
        asset = await self.repository.get_asset(job.input_asset_id)
        if asset is None or asset.job_id != job.job_id:
            return False
        input_path = self.storage.resolve_asset(job.job_id, asset.relative_path)
        if not input_path.is_file():
            return False
        events = await self.repository.list_events(job.job_id)
        job._event_sequence = events[-1].sequence if events else 0
        paths = self.storage.ensure_job(job.job_id)
        self._jobs[job.job_id] = job
        self._requests[job.job_id] = GenerationRequest(
            job_id=job.job_id,
            input_path=input_path,
            output_dir=paths.work_dir,
            workflow_revision=job.workflow_revision,
            timeout_seconds=600,
            idempotency_key=str(job.job_id),
        )
        return self.dispatcher.enqueue(str(job.job_id))

    async def create_job(
        self,
        stream: BinaryIO,
        *,
        filename: str,
        content_type: str | None,
    ) -> tuple[GenerationJob, str]:
        usage = shutil.disk_usage(self.storage.root)
        free_percent = (usage.free / usage.total * 100) if usage.total else 0
        ensure_disk_admission(free_percent, minimum_free_percent=self.settings.min_free_disk_percent)
        validated = validate_upload(
            stream,
            filename=filename,
            content_type=content_type,
            max_bytes=self.settings.max_upload_bytes,
        )
        now = datetime.now(timezone.utc)
        job_id = uuid4()
        token, token_digest = create_job_token()
        expires_at = now + timedelta(hours=self.settings.retention_hours)
        paths = self.storage.ensure_job(job_id)
        stored_name = f"input{validated.filename_extension}"
        stored_path = self.storage.atomic_write(job_id, "upload", stored_name, validated.data)
        input_asset = JobAsset(
            job_id=job_id,
            kind=AssetKind.INPUT,
            relative_path=str(stored_path.relative_to(self.storage.root)),
            content_type=validated.content_type,
            size_bytes=validated.size_bytes,
            sha256=validated.sha256,
            created_at=now,
            expires_at=expires_at,
        )
        job = GenerationJob(
            job_id=job_id,
            token_digest=token_digest,
            workflow_revision="mock-fixture-rev-1",
            input_asset_id=input_asset.asset_id,
            created_at=now,
            queued_at=now,
            expires_at=expires_at,
            updated_at=now,
        )
        await self.repository.accept_job(job, input_asset)
        # The accepted event occupies sequence 1 in the durable event log.
        job._event_sequence = 1
        request = GenerationRequest(
            job_id=job_id,
            input_path=stored_path,
            output_dir=paths.work_dir,
            workflow_revision=job.workflow_revision,
            timeout_seconds=600,
            idempotency_key=str(job_id),
        )
        self._requests[job_id] = request
        self.dispatcher.enqueue(str(job_id))
        self._jobs[job_id] = job
        return job, token

    async def read_job(self, job_id: UUID, token: str | None) -> GenerationJob:
        job = self._jobs.get(job_id) or await self.repository.get_job(job_id)
        if job is None or not token or not verify_job_token(token, job.token_digest):
            raise JobNotFoundError
        if job.expires_at and job.expires_at <= datetime.now(timezone.utc):
            raise ExpiredJobError
        await self._advance(job)
        return job

    async def read_result(self, job_id: UUID, token: str | None) -> Path:
        job = await self.read_job(job_id, token)
        if job.status is not JobState.COMPLETED or job.output_asset_id is None:
            raise ResultNotReadyError
        path = self.storage.resolve_path(job_id, "outputs/model.glb")
        if not path.is_file():
            raise ResultNotReadyError
        return path

    async def _advance(self, job: GenerationJob) -> None:
        async with self._advance_lock:
            await self._advance_unlocked(job)

    async def _advance_unlocked(self, job: GenerationJob) -> None:
        if job.is_terminal:
            return
        handle = self._handles.get(job.job_id)
        if handle is None:
            claimed = self.dispatcher.claim_next()
            if claimed != str(job.job_id):
                return
            request = self._requests.get(job.job_id)
            if request is None:
                self.dispatcher.complete(str(job.job_id))
                return
            try:
                if not await self.repository.reserve_submission(job.job_id):
                    self.dispatcher.complete(str(job.job_id))
                    self._requests.pop(job.job_id, None)
                    return
                job.attempt_count = 1
                handle = self.adapter.submit(request)
                job.engine_job_id = handle.internal_id
                await self.repository.update_job(job)
                self._handles[job.job_id] = handle
                # Consume the adapter's initial queued observation at admission
                # so the next client read has stable queued → processing
                # semantics without executing GPU work twice.
                self.adapter.inspect(handle)
            except Exception:
                error = SafeJobError(code="engine_unavailable", message="Generation unavailable")
                event = job.transition(JobState.FAILED, error=error)
                await self.repository.persist_transition(job, event)
                self.dispatcher.complete(str(job.job_id))
                self._requests.pop(job.job_id, None)
            return
        observation = self.adapter.inspect(handle)
        decision = self.coordinator.decide(observation)
        if decision.target_state is JobState.QUEUED:
            return
        if decision.target_state is JobState.PROCESSING:
            if job.status is JobState.PROCESSING:
                if (
                    job.progress_percent == decision.progress_percent
                    and job.progress_message == decision.progress_message
                ):
                    return
                event = job.record_progress(decision.progress_percent, decision.progress_message)
            else:
                event = job.transition(
                    JobState.PROCESSING,
                    progress_percent=decision.progress_percent,
                    progress_message=decision.progress_message,
                )
            await self.repository.persist_transition(job, event)
        elif decision.target_state is JobState.COMPLETED:
            try:
                output_path = publish_glb(
                    decision.candidates,
                    self.storage.ensure_job(job.job_id).output_dir / "model.glb",
                )
            except PublicationError:
                error = SafeJobError(code="invalid_result", message="Generated model is unavailable")
                event = job.transition(JobState.FAILED, error=error)
                await self.repository.persist_transition(job, event)
                self.dispatcher.complete(str(job.job_id))
                self._handles.pop(job.job_id, None)
                self._requests.pop(job.job_id, None)
                return
            output_asset = JobAsset(
                job_id=job.job_id,
                kind=AssetKind.OUTPUT,
                relative_path=str(output_path.relative_to(self.storage.root)),
                content_type="model/gltf-binary",
                size_bytes=output_path.stat().st_size,
                sha256=_sha256(output_path),
                created_at=datetime.now(timezone.utc),
                expires_at=job.expires_at or datetime.now(timezone.utc),
            )
            # A fast or cached engine execution can finish between polls, so
            # the public API may never observe an intermediate running state.
            # Preserve the domain state machine by recording the processing
            # bridge before completion; successful output is definitive proof
            # that processing occurred.
            if job.status is JobState.QUEUED:
                processing_event = job.transition(JobState.PROCESSING)
                await self.repository.persist_transition(job, processing_event)
            event = job.transition(JobState.COMPLETED, output_asset_id=output_asset.asset_id, progress_percent=100)
            await self.repository.persist_transition(job, event, asset=output_asset)
            self.dispatcher.complete(str(job.job_id))
            self._handles.pop(job.job_id, None)
            self._requests.pop(job.job_id, None)
        else:
            event = job.transition(decision.target_state, error=decision.error)
            await self.repository.persist_transition(job, event)
            self.dispatcher.complete(str(job.job_id))
            self._handles.pop(job.job_id, None)
            self._requests.pop(job.job_id, None)

    def queue_position(self, job_id: UUID) -> int | None:
        return self.dispatcher.position(str(job_id))

def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
