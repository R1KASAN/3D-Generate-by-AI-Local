from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from .database import Database
from ..domain.jobs import AssetKind, GenerationJob, JobAsset, JobEvent, JobState


def _serialize_time(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class JobRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def accept_job(self, job: GenerationJob, input_asset: JobAsset) -> None:
        if input_asset.job_id != job.job_id:
            raise ValueError("input asset must belong to the accepted job")
        async with self.database.connection() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            await connection.execute(
                """
                INSERT INTO generation_jobs (
                    id, token_digest, status, progress_percent, progress_message,
                    engine_job_id, workflow_revision, input_asset_id, output_asset_id,
                    error_code, error_message, attempt_count, created_at, queued_at,
                    started_at, finished_at, expires_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(job.job_id),
                    job.token_digest,
                    job.status.value,
                    job.progress_percent,
                    job.progress_message,
                    job.engine_job_id,
                    job.workflow_revision,
                    str(job.input_asset_id) if job.input_asset_id else str(input_asset.asset_id),
                    str(job.output_asset_id) if job.output_asset_id else None,
                    job.error_code,
                    job.error_message,
                    job.attempt_count,
                    _serialize_time(job.created_at),
                    _serialize_time(job.queued_at or job.created_at),
                    _serialize_time(job.started_at) if job.started_at else None,
                    _serialize_time(job.finished_at) if job.finished_at else None,
                    _serialize_time(job.expires_at or job.created_at),
                    _serialize_time(job.updated_at or job.created_at),
                ),
            )
            await connection.execute(
                """
                INSERT INTO job_assets (
                    id, job_id, kind, relative_path, content_type, size_bytes,
                    sha256, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._asset_values(input_asset),
            )
            await connection.execute(
                """
                INSERT INTO job_events (
                    job_id, sequence, event_type, from_status, to_status,
                    progress_percent, safe_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(job.job_id),
                    1,
                    "accepted",
                    None,
                    JobState.QUEUED.value,
                    job.progress_percent,
                    None,
                    _serialize_time(job.queued_at or job.created_at),
                ),
            )
            await connection.commit()

    async def add_asset(self, asset: JobAsset) -> None:
        async with self.database.connection() as connection:
            await connection.execute(
                """
                INSERT INTO job_assets (
                    id, job_id, kind, relative_path, content_type, size_bytes,
                    sha256, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._asset_values(asset),
            )
            await connection.commit()

    async def update_job(self, job: GenerationJob) -> None:
        async with self.database.connection() as connection:
            await connection.execute(
                """
                UPDATE generation_jobs SET
                    token_digest = ?, status = ?, progress_percent = ?, progress_message = ?,
                    engine_job_id = ?, workflow_revision = ?, input_asset_id = ?, output_asset_id = ?,
                    error_code = ?, error_message = ?, attempt_count = ?, created_at = ?, queued_at = ?,
                    started_at = ?, finished_at = ?, expires_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    job.token_digest,
                    job.status.value,
                    job.progress_percent,
                    job.progress_message,
                    job.engine_job_id,
                    job.workflow_revision,
                    str(job.input_asset_id) if job.input_asset_id else None,
                    str(job.output_asset_id) if job.output_asset_id else None,
                    job.error_code,
                    job.error_message,
                    job.attempt_count,
                    _serialize_time(job.created_at),
                    _serialize_time(job.queued_at or job.created_at),
                    _serialize_time(job.started_at) if job.started_at else None,
                    _serialize_time(job.finished_at) if job.finished_at else None,
                    _serialize_time(job.expires_at or job.created_at),
                    _serialize_time(job.updated_at or job.created_at),
                    str(job.job_id),
                ),
            )
            await connection.commit()

    async def append_event(self, event: JobEvent) -> None:
        async with self.database.connection() as connection:
            await connection.execute(
                """
                INSERT INTO job_events (
                    job_id, sequence, event_type, from_status, to_status,
                    progress_percent, safe_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.job_id),
                    event.sequence,
                    event.event_type,
                    event.from_status.value if event.from_status else None,
                    event.to_status.value if event.to_status else None,
                    event.progress_percent,
                    event.safe_message,
                    _serialize_time(event.created_at),
                ),
            )
            await connection.commit()

    async def persist_transition(
        self,
        job: GenerationJob,
        event: JobEvent,
        *,
        asset: JobAsset | None = None,
    ) -> None:
        """Commit an optional output asset, job snapshot, and event atomically."""
        if event.job_id != job.job_id or (asset is not None and asset.job_id != job.job_id):
            raise ValueError("transition records must belong to the same job")
        async with self.database.connection() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            if asset is not None:
                await connection.execute(
                    """
                    INSERT INTO job_assets (
                        id, job_id, kind, relative_path, content_type, size_bytes,
                        sha256, created_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._asset_values(asset),
                )
            await connection.execute(
                """
                UPDATE generation_jobs SET
                    token_digest = ?, status = ?, progress_percent = ?, progress_message = ?,
                    engine_job_id = ?, workflow_revision = ?, input_asset_id = ?, output_asset_id = ?,
                    error_code = ?, error_message = ?, attempt_count = ?, created_at = ?, queued_at = ?,
                    started_at = ?, finished_at = ?, expires_at = ?, updated_at = ?
                WHERE id = ?
                """,
                self._job_update_values(job),
            )
            await connection.execute(
                """
                INSERT INTO job_events (
                    job_id, sequence, event_type, from_status, to_status,
                    progress_percent, safe_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._event_values(event),
            )
            await connection.commit()

    async def get_job(self, job_id: UUID) -> GenerationJob | None:
        async with self.database.connection() as connection:
            cursor = await connection.execute("SELECT * FROM generation_jobs WHERE id = ?", (str(job_id),))
            row = await cursor.fetchone()
        return self._job_from_row(row) if row else None

    async def get_asset(self, asset_id: UUID) -> JobAsset | None:
        async with self.database.connection() as connection:
            cursor = await connection.execute("SELECT * FROM job_assets WHERE id = ?", (str(asset_id),))
            row = await cursor.fetchone()
        return self._asset_from_row(row) if row else None

    async def list_nonterminal(self) -> list[GenerationJob]:
        async with self.database.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT * FROM generation_jobs
                WHERE status IN ('queued', 'processing')
                ORDER BY queued_at ASC, id ASC
                """
            )
            rows = await cursor.fetchall()
        return [self._job_from_row(row) for row in rows]

    async def list_completed(self) -> list[GenerationJob]:
        async with self.database.connection() as connection:
            cursor = await connection.execute(
                "SELECT * FROM generation_jobs WHERE status = 'completed' ORDER BY finished_at, id"
            )
            rows = await cursor.fetchall()
        return [self._job_from_row(row) for row in rows]

    async def list_expired_terminal(self, now: datetime) -> list[UUID]:
        async with self.database.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT id FROM generation_jobs
                WHERE expires_at <= ? AND status IN ('completed', 'failed', 'cancelled')
                ORDER BY expires_at, id
                """,
                (_serialize_time(now),),
            )
            rows = await cursor.fetchall()
        return [UUID(row[0]) for row in rows]

    async def delete_job(self, job_id: UUID) -> None:
        async with self.database.connection() as connection:
            await connection.execute("DELETE FROM generation_jobs WHERE id = ?", (str(job_id),))
            await connection.commit()

    async def reserve_submission(self, job_id: UUID) -> bool:
        """Atomically reserve the only automatic engine submission for a job."""
        async with self.database.connection() as connection:
            await connection.execute("BEGIN IMMEDIATE")
            cursor = await connection.execute(
                """
                UPDATE generation_jobs
                SET attempt_count = attempt_count + 1, updated_at = ?
                WHERE id = ? AND status = 'queued' AND attempt_count = 0
                """,
                (_serialize_time(datetime.now(timezone.utc)), str(job_id)),
            )
            await connection.commit()
        return cursor.rowcount == 1

    async def list_events(self, job_id: UUID) -> list[JobEvent]:
        async with self.database.connection() as connection:
            cursor = await connection.execute(
                "SELECT * FROM job_events WHERE job_id = ? ORDER BY sequence ASC", (str(job_id),)
            )
            rows = await cursor.fetchall()
        return [self._event_from_row(row) for row in rows]

    async def count_assets(self, job_id: UUID) -> int:
        async with self.database.connection() as connection:
            cursor = await connection.execute("SELECT COUNT(*) FROM job_assets WHERE job_id = ?", (str(job_id),))
            row = await cursor.fetchone()
        if row is None:
            return 0
        return int(row[0])

    async def delete_expired(self, now: datetime) -> list[UUID]:
        timestamp = _serialize_time(now)
        async with self.database.connection() as connection:
            cursor = await connection.execute(
                """
                SELECT id FROM generation_jobs
                WHERE expires_at <= ? AND status IN ('completed', 'failed', 'cancelled')
                ORDER BY expires_at, id
                """,
                (timestamp,),
            )
            rows = await cursor.fetchall()
            ids = [UUID(row[0]) for row in rows]
            await connection.execute(
                """
                DELETE FROM generation_jobs
                WHERE expires_at <= ? AND status IN ('completed', 'failed', 'cancelled')
                """,
                (timestamp,),
            )
            await connection.commit()
        return ids

    @staticmethod
    def _asset_values(asset: JobAsset) -> tuple[Any, ...]:
        return (
            str(asset.asset_id),
            str(asset.job_id),
            asset.kind.value,
            asset.relative_path,
            asset.content_type,
            asset.size_bytes,
            asset.sha256,
            _serialize_time(asset.created_at),
            _serialize_time(asset.expires_at),
        )

    @staticmethod
    def _job_update_values(job: GenerationJob) -> tuple[Any, ...]:
        return (
            job.token_digest,
            job.status.value,
            job.progress_percent,
            job.progress_message,
            job.engine_job_id,
            job.workflow_revision,
            str(job.input_asset_id) if job.input_asset_id else None,
            str(job.output_asset_id) if job.output_asset_id else None,
            job.error_code,
            job.error_message,
            job.attempt_count,
            _serialize_time(job.created_at),
            _serialize_time(job.queued_at or job.created_at),
            _serialize_time(job.started_at) if job.started_at else None,
            _serialize_time(job.finished_at) if job.finished_at else None,
            _serialize_time(job.expires_at or job.created_at),
            _serialize_time(job.updated_at or job.created_at),
            str(job.job_id),
        )

    @staticmethod
    def _event_values(event: JobEvent) -> tuple[Any, ...]:
        return (
            str(event.job_id),
            event.sequence,
            event.event_type,
            event.from_status.value if event.from_status else None,
            event.to_status.value if event.to_status else None,
            event.progress_percent,
            event.safe_message,
            _serialize_time(event.created_at),
        )

    @staticmethod
    def _job_from_row(row: Any) -> GenerationJob:
        return GenerationJob(
            job_id=UUID(row["id"]),
            token_digest=row["token_digest"],
            status=JobState(row["status"]),
            progress_percent=row["progress_percent"],
            progress_message=row["progress_message"],
            engine_job_id=row["engine_job_id"],
            workflow_revision=row["workflow_revision"],
            input_asset_id=UUID(row["input_asset_id"]) if row["input_asset_id"] else None,
            output_asset_id=UUID(row["output_asset_id"]) if row["output_asset_id"] else None,
            error_code=row["error_code"],
            error_message=row["error_message"],
            attempt_count=row["attempt_count"],
            created_at=_parse_time(row["created_at"]),
            queued_at=_parse_time(row["queued_at"]),
            started_at=_parse_time(row["started_at"]) if row["started_at"] else None,
            finished_at=_parse_time(row["finished_at"]) if row["finished_at"] else None,
            expires_at=_parse_time(row["expires_at"]),
            updated_at=_parse_time(row["updated_at"]),
        )

    @staticmethod
    def _asset_from_row(row: Any) -> JobAsset:
        return JobAsset(
            asset_id=UUID(row["id"]),
            job_id=UUID(row["job_id"]),
            kind=AssetKind(row["kind"]),
            relative_path=row["relative_path"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            created_at=_parse_time(row["created_at"]),
            expires_at=_parse_time(row["expires_at"]),
        )

    @staticmethod
    def _event_from_row(row: Any) -> JobEvent:
        return JobEvent(
            job_id=UUID(row["job_id"]),
            sequence=row["sequence"],
            event_type=row["event_type"],
            from_status=JobState(row["from_status"]) if row["from_status"] else None,
            to_status=JobState(row["to_status"]) if row["to_status"] else None,
            progress_percent=row["progress_percent"],
            safe_message=row["safe_message"],
            created_at=_parse_time(row["created_at"]),
        )
