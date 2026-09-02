from __future__ import annotations

from ..domain.jobs import GenerationJob, JobEvent, JobState, SafeJobError
from .job_service import JobService


class RecoveryService:
    """Reconcile durable jobs after a process restart without resubmitting work."""

    def __init__(self, job_service: JobService) -> None:
        self.job_service = job_service

    async def reconcile(self) -> list[str]:
        jobs = await self.job_service.repository.list_nonterminal()
        reconciled: list[str] = []
        for job in jobs:
            if job.status is JobState.QUEUED:
                if await self.job_service.rehydrate_queued(job):
                    reconciled.append(str(job.job_id))
                else:
                    await self._mark_restart_failure(job)
                    reconciled.append(str(job.job_id))
                continue
            if job.status is JobState.PROCESSING and job.job_id not in self.job_service._handles:
                await self._mark_restart_failure(job)
                reconciled.append(str(job.job_id))
        for job in await self.job_service.repository.list_completed():
            if await self._record_missing_output(job):
                reconciled.append(str(job.job_id))
        return reconciled

    async def _mark_restart_failure(self, job: GenerationJob) -> None:
        events = await self.job_service.repository.list_events(job.job_id)
        job._event_sequence = events[-1].sequence if events else 0
        event = job.transition(
            JobState.FAILED,
            error=SafeJobError(code="restart_recovery", message="Generation could not be recovered after restart"),
        )
        await self.job_service.repository.persist_transition(job, event)

    async def _record_missing_output(self, job: GenerationJob) -> bool:
        if job.output_asset_id is None:
            missing = True
        else:
            asset = await self.job_service.repository.get_asset(job.output_asset_id)
            missing = (
                asset is None
                or asset.job_id != job.job_id
                or not self.job_service.storage.resolve_asset(job.job_id, asset.relative_path).is_file()
            )
        if not missing:
            return False
        events = await self.job_service.repository.list_events(job.job_id)
        if any(event.event_type == "output_missing" for event in events):
            return False
        sequence = events[-1].sequence + 1 if events else 1
        await self.job_service.repository.append_event(
            JobEvent(
                job_id=job.job_id,
                sequence=sequence,
                event_type="output_missing",
                from_status=JobState.COMPLETED,
                to_status=JobState.COMPLETED,
                safe_message="Generated model is unavailable",
            )
        )
        return True


async def reconcile_after_restart(job_service: JobService) -> list[str]:
    return await RecoveryService(job_service).reconcile()
