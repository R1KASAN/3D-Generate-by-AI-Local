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
    return JSONResponse(status_code=200, content=health_payload("ok"))
