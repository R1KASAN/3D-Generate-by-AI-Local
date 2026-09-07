from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


HealthStatus = Literal["ok", "degraded", "unavailable"]
_ALLOWED_STATUS = frozenset({"ok", "degraded", "unavailable"})


def health_payload(status: str) -> dict[str, str]:
    if status not in _ALLOWED_STATUS:
        raise ValueError("health status is not allowed")
    return {"status": status}


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return health_payload("ok")


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    if getattr(request.app.state, "adapter_ready", True) is False:
        return JSONResponse(status_code=503, content=health_payload("unavailable"))
    job_service = getattr(request.app.state, "job_service", None)
    if job_service is None:
        return JSONResponse(status_code=503, content=health_payload("unavailable"))
    try:
        storage_ready = job_service.storage.root.is_dir()
        database_ready = job_service.database.path.parent.is_dir()
    except (AttributeError, OSError):
        storage_ready = database_ready = False
    if not (storage_ready and database_ready):
        return JSONResponse(status_code=503, content=health_payload("unavailable"))
    return JSONResponse(status_code=200, content=health_payload("ok"))


@router.get("/engine")
async def engine(request: Request) -> JSONResponse:
    """Feature 003 FR-025/SC-008: a fast, dedicated liveness probe for the
    AI engine, distinct from /ready. /ready reports whether the adapter was
    configured successfully at startup and never changes afterward; this
    endpoint answers "is the engine reachable right now", which is what
    detects the spec's Edge Case of an engine that hangs after a healthy
    startup while the tunnel and web entry remain up. Never exposes an
    engine identifier, address, or port - only the same safe status shape
    /ready and /live already use.
    """
    job_service = getattr(request.app.state, "job_service", None)
    if job_service is None or getattr(request.app.state, "adapter_ready", True) is False:
        return JSONResponse(status_code=503, content=health_payload("unavailable"))
    if not job_service.adapter.is_live():
        return JSONResponse(status_code=503, content=health_payload("unavailable"))
    return JSONResponse(status_code=200, content=health_payload("ok"))
