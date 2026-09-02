from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain.jobs import SafeJobError


@dataclass(frozen=True, slots=True)
class PublicErrorResponse:
    status_code: int
    body: dict[str, dict[str, str]]


def map_exception(exc: Exception, *, job_id: object | None = None) -> PublicErrorResponse:
    """Map internal exceptions to a small, non-sensitive public error envelope."""

    if isinstance(exc, SafeJobError):
        return PublicErrorResponse(
            status_code=400,
            body={"error": {"code": exc.code, "message": exc.message}},
        )
    return PublicErrorResponse(
        status_code=500,
        body={"error": {"code": "internal_error", "message": "The job could not be completed."}},
    )


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    safe = SafeJobError(code=code, message=message)
    return {"error": {"code": safe.code, "message": safe.message}}


async def unhandled_exception_handler(_request: Any, exc: Exception) -> Any:
    """Return a framework response without serializing the internal exception."""

    from fastapi.responses import JSONResponse

    mapped = map_exception(exc)
    return JSONResponse(status_code=mapped.status_code, content=mapped.body)
