from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import Mapping, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    workflow_manifest_path: Path = Path("workflows/hunyuan3d/workflow-manifest.json")

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
    "WORKFLOW_MANIFEST_PATH": "workflow_manifest_path",
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
    "RETENTION_",
    "MIN_",
    "WORKFLOW_",
)


def _is_secret_like_name(name: str) -> bool:
    normalized = name.upper()
    is_secret_like = any(
        normalized == marker
        or normalized.endswith(f"_{marker}")
        for marker in _SECRET_MARKERS
    )
    return is_secret_like and (
        normalized in _ENV_TO_FIELD
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
