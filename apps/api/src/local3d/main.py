from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .adapters.generation.factory import AdapterConfigurationError, build_real_adapter
from .api.errors import unhandled_exception_handler
from .api.health import router as health_router
from .api.jobs import router as jobs_router
from .config import Settings, load_settings
from .services.job_service import JobService
from .services.recovery import RecoveryService


def create_app(settings: Settings | None = None, service: JobService | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    adapter_ready = True
    job_service = service
    if job_service is None:
        if resolved_settings.generation_adapter == "comfyui":
            try:
                real_adapter = build_real_adapter(resolved_settings)
            except AdapterConfigurationError:
                # Fail closed: the app still starts so /health/live and other
                # diagnostics work, but readiness reports unavailable and no
                # job is admitted against a manifest/runtime that failed its
                # startup compatibility check.
                adapter_ready = False
                job_service = None
            else:
                job_service = JobService(resolved_settings, adapter=real_adapter)
        else:
            job_service = JobService(resolved_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if job_service is not None:
            await job_service.startup()
            await RecoveryService(job_service).reconcile()
            worker_task = job_service.start_worker()
            maintenance_task = job_service.start_maintenance()
            try:
                yield
            finally:
                await job_service.stop_worker(worker_task)
                await job_service.stop_maintenance(maintenance_task)
        else:
            yield

    app = FastAPI(title="Local 3D Generation API", version="0.1.0", lifespan=lifespan)
    app.state.job_service = job_service
    app.state.adapter_ready = adapter_ready
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app


app = create_app()
