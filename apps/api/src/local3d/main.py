from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .api.errors import unhandled_exception_handler
from .api.health import router as health_router
from .api.jobs import router as jobs_router
from .config import Settings, load_settings
from .services.job_service import JobService
from .services.recovery import RecoveryService


def create_app(settings: Settings | None = None, service: JobService | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    job_service = service or JobService(resolved_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await job_service.startup()
        await RecoveryService(job_service).reconcile()
        maintenance_task = job_service.start_maintenance()
        try:
            yield
        finally:
            await job_service.stop_maintenance(maintenance_task)

    app = FastAPI(title="Local 3D Generation API", version="0.1.0", lifespan=lifespan)
    app.state.job_service = job_service
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app


app = create_app()
