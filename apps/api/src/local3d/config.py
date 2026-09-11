from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import Any, Mapping, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_APPROVED_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_APPROVED_RETENTION_HOURS = 24


class Settings(BaseModel):
    """Validated process settings shared by mock and ComfyUI adapters."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    app_env: Literal["development", "test", "production"] = "development"
    generation_adapter: Literal["mock", "comfyui"] = "mock"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_output_root: Path | None = None
    storage_root: Path = Path("storage")
    database_path: Path = Path("storage/jobs.sqlite3")
    max_upload_bytes: int = Field(default=MAX_APPROVED_UPLOAD_BYTES, gt=0, le=MAX_APPROVED_UPLOAD_BYTES)
    retention_hours: int = Field(default=MAX_APPROVED_RETENTION_HOURS, gt=0, le=MAX_APPROVED_RETENTION_HOURS)
    min_free_disk_percent: int = Field(default=10, ge=0, le=100)
    max_pending_jobs: int = Field(default=20, ge=1)
    max_submissions_per_minute: int = Field(default=30, ge=1)
    max_identical_per_minute: int = Field(default=5, ge=1)
    job_timeout_seconds: int = Field(default=600, gt=0, le=86_400)
    worker_interval_seconds: int = Field(default=1, gt=0, le=60)
    maintenance_interval_seconds: int = Field(default=300, gt=0, le=86_400)
    orphan_grace_hours: int = Field(default=1, gt=0, le=24)
    workflow_manifest_path: Path = Path("workflows/hunyuan3d/workflow-manifest.json")
    cors_allowed_origins: tuple[str, ...] = ("https://www.mangosgo.com",)
    cors_preview_origin_enabled: bool = False
    cors_preview_origin: str = "https://inw3d-ai-local.web.app"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            value = tuple(part.strip() for part in value.split(",") if part.strip())
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise ValueError("CORS_ALLOWED_ORIGINS must be a comma-separated origin list")
        origins = tuple(str(origin).strip() for origin in value if str(origin).strip())
        if not origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one origin")
        for origin in origins:
            _validate_browser_origin(origin, "CORS_ALLOWED_ORIGINS")
        if "*" in origins:
            raise ValueError("wildcard CORS origins are not allowed")
        return origins

    @field_validator("cors_preview_origin")
    @classmethod
    def validate_preview_origin(cls, value: str) -> str:
        _validate_browser_origin(value, "CORS_PREVIEW_ORIGIN")
        return value

    @model_validator(mode="after")
    def enforce_production_cors(self) -> "Settings":
        if self.app_env == "production":
            for origin in (*self.cors_allowed_origins, self.cors_preview_origin):
                _validate_browser_origin(origin, "production CORS origin", https_only=True)
        return self

    @field_validator("comfyui_base_url")
    @classmethod
    def validate_comfyui_loopback(cls, value: str) -> str:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        if (
            parsed.scheme not in {"http", "https"}
            or hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("COMFYUI_BASE_URL must be a loopback HTTP URL")

        normalized_host = hostname.rstrip(".").lower()
        is_loopback_name = normalized_host == "localhost"
        try:
            is_loopback_address = ipaddress.ip_address(normalized_host).is_loopback
        except ValueError:
            is_loopback_address = False
        if not (is_loopback_name or is_loopback_address):
            raise ValueError("COMFYUI_BASE_URL must resolve to a loopback address")
        return value.rstrip("/")


def _validate_browser_origin(value: str, name: str, *, https_only: bool = False) -> None:
    parsed = urlsplit(value)
    local_test_origin = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        parsed.scheme not in {"https", "http"}
        or (https_only and parsed.scheme != "https")
        or (parsed.scheme == "http" and not local_test_origin)
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or (parsed.port is not None and (https_only or not local_test_origin))
    ):
        raise ValueError(f"{name} must be an exact HTTPS origin without a path or port")


_ENV_TO_FIELD = {
    "APP_ENV": "app_env",
    "GENERATION_ADAPTER": "generation_adapter",
    "API_HOST": "api_host",
    "API_PORT": "api_port",
    "COMFYUI_BASE_URL": "comfyui_base_url",
    "COMFYUI_OUTPUT_ROOT": "comfyui_output_root",
    "STORAGE_ROOT": "storage_root",
    "DATABASE_PATH": "database_path",
    "MAX_UPLOAD_BYTES": "max_upload_bytes",
    "RETENTION_HOURS": "retention_hours",
    "MIN_FREE_DISK_PERCENT": "min_free_disk_percent",
    "MAX_PENDING_JOBS": "max_pending_jobs",
    "MAX_SUBMISSIONS_PER_MINUTE": "max_submissions_per_minute",
    "MAX_IDENTICAL_PER_MINUTE": "max_identical_per_minute",
    "JOB_TIMEOUT_SECONDS": "job_timeout_seconds",
    "WORKER_INTERVAL_SECONDS": "worker_interval_seconds",
    "MAINTENANCE_INTERVAL_SECONDS": "maintenance_interval_seconds",
    "ORPHAN_GRACE_HOURS": "orphan_grace_hours",
    "WORKFLOW_MANIFEST_PATH": "workflow_manifest_path",
    "CORS_ALLOWED_ORIGINS": "cors_allowed_origins",
    "CORS_PREVIEW_ORIGIN_ENABLED": "cors_preview_origin_enabled",
    "CORS_PREVIEW_ORIGIN": "cors_preview_origin",
}
_SECRET_MARKERS = ("SECRET", "PASSWORD", "TOKEN", "API_KEY")
_APPLICATION_ENV_PREFIXES = (
    "APP_",
    "GENERATION_",
    "API_",
    "COMFYUI_",
    "STORAGE_",
    "DATABASE_",
    "MAX_",
    "JOB_",
    "ORPHAN_",
    "WORKER_",
    "MAINTENANCE_",
    "RETENTION_",
    "MIN_",
    "WORKFLOW_",
    "CORS_",
)


def _is_secret_like_name(name: str) -> bool:
    normalized = name.upper()
    is_secret_like = any(
        normalized == marker
        or normalized.endswith(f"_{marker}")
        for marker in _SECRET_MARKERS
    )
    return is_secret_like and (
        normalized in _SECRET_MARKERS
        or normalized in _ENV_TO_FIELD
        or normalized.startswith(_APPLICATION_ENV_PREFIXES)
    )


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Load the allowlisted environment variables without accepting secrets."""

    source = dict(os.environ if environ is None else environ)
    secret_names = sorted(name for name in source if _is_secret_like_name(name))
    if secret_names:
        raise ValueError(
            "secret-like configuration keys are not accepted: " + ", ".join(secret_names)
        )

    values = {
        field_name: source[env_name]
        for env_name, field_name in _ENV_TO_FIELD.items()
        if env_name in source
    }
    return Settings.model_validate(values)
