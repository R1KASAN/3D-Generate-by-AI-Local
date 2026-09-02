from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, File, Header, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..domain.jobs import GenerationJob, JobState
from ..services.image_validation import LowStorageError, UploadValidationError
from ..services.job_service import ExpiredJobError, JobNotFoundError, JobService, ResultNotReadyError


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _service(request: Request) -> JobService:
    return cast(JobService, request.app.state.job_service)


def _not_found() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "job_not_found", "message": "Job not found"}},
    )


def _not_ready() -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": {"code": "result_not_ready", "message": "Result is not ready"}},
    )


def _public_job(
    job: GenerationJob,
    *,
    token: str | None = None,
    queue_position: int | None = None,
) -> dict[str, object]:
    completed = job.status is JobState.COMPLETED
    job_id = str(job.job_id)
    body: dict[str, object] = {
        "job_id": job_id,
        "status": job.status.value,
        "progress_percent": job.progress_percent,
        "progress_message": job.progress_message,
        "queue_position": queue_position,
        "queue_position_is_approximate": True,
        "error": (
            {"code": job.error_code, "message": job.error_message}
            if job.error_code and job.error_message
            else None
        ),
        "model_url": f"/api/v1/jobs/{job_id}/model" if completed else None,
        "download_url": f"/api/v1/jobs/{job_id}/download" if completed else None,
        "created_at": _iso(job.created_at),
        "expires_at": _iso(job.expires_at or job.created_at),
    }
    if token is not None:
        body["job_token"] = token
    return body


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


@router.post("", status_code=201)
async def create_job(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    try:
        job, token = await _service(request).create_job(
            file.file,
            filename=file.filename or "",
            content_type=file.content_type,
        )
    except LowStorageError:
        return JSONResponse(
            status_code=507,
            content={"error": {"code": "low_storage", "message": "New jobs are temporarily disabled"}},
        )
    except UploadValidationError as exc:
        message = str(exc)
        if "large" in message:
            status_code, code = 413, "upload_too_large"
        elif "supported" in message:
            status_code, code = 415, "unsupported_image"
        else:
            status_code, code = 422, "corrupt_image"
        return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
    return JSONResponse(
        status_code=201,
        content=_public_job(job, token=token),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{job_id}")
async def get_job(
    request: Request,
    job_id: UUID,
    x_job_token: Annotated[str | None, Header(alias="X-Job-Token")] = None,
) -> JSONResponse:
    try:
        job = await _service(request).read_job(job_id, x_job_token)
    except (JobNotFoundError, ExpiredJobError):
        return _not_found()
    return JSONResponse(
        content=_public_job(job, queue_position=_service(request).queue_position(job.job_id)),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{job_id}/model", response_model=None)
async def preview_model(
    request: Request,
    job_id: UUID,
    x_job_token: Annotated[str | None, Header(alias="X-Job-Token")] = None,
) -> FileResponse | JSONResponse:
    try:
        path = await _service(request).read_result(job_id, x_job_token)
    except (JobNotFoundError, ExpiredJobError):
        return _not_found()
    except ResultNotReadyError:
        return _not_ready()
    return FileResponse(path, media_type="model/gltf-binary", headers={"Cache-Control": "private, no-store"})


@router.get("/{job_id}/download", response_model=None)
async def download_model(
    request: Request,
    job_id: UUID,
    x_job_token: Annotated[str | None, Header(alias="X-Job-Token")] = None,
) -> FileResponse | JSONResponse:
    try:
        path = await _service(request).read_result(job_id, x_job_token)
    except (JobNotFoundError, ExpiredJobError):
        return _not_found()
    except ResultNotReadyError:
        return _not_ready()
    return FileResponse(
        path,
        media_type="model/gltf-binary",
        filename=f"{job_id}.glb",
        headers={"Cache-Control": "private, no-store"},
    )
