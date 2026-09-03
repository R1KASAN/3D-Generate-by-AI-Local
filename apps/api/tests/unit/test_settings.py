from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError

from local3d.config import Settings, load_settings
from local3d.services.job_service import JobService


def test_defaults_lock_the_mvp_limits_and_retention_policy() -> None:
    settings = Settings()

    assert settings.max_upload_bytes == 10 * 1024 * 1024
    assert settings.retention_hours == 24
    assert settings.min_free_disk_percent == 10
    assert settings.storage_root == Path("storage")
    assert settings.database_path == Path("storage/jobs.sqlite3")


@pytest.mark.parametrize("adapter", ["mock", "comfyui"])
def test_supported_generation_adapters_are_selectable(adapter: Literal["mock", "comfyui"]) -> None:
    settings = Settings(generation_adapter=adapter)

    assert settings.generation_adapter == adapter


def test_unknown_generation_adapter_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(generation_adapter="cloud")  # type: ignore[arg-type]


def test_unimplemented_real_adapter_fails_closed_instead_of_using_mock() -> None:
    with pytest.raises(RuntimeError, match="ComfyUI generation adapter is not configured"):
        JobService(Settings(generation_adapter="comfyui"))


def test_engine_url_is_loopback_only() -> None:
    settings = Settings(comfyui_base_url="http://127.0.0.1:8188")

    assert settings.comfyui_base_url == "http://127.0.0.1:8188"

    with pytest.raises(ValidationError):
        Settings(comfyui_base_url="http://192.168.1.50:8188")


def test_limits_cannot_exceed_the_approved_mvp_policy() -> None:
    with pytest.raises(ValidationError):
        Settings(max_upload_bytes=(10 * 1024 * 1024) + 1)
    with pytest.raises(ValidationError):
        Settings(retention_hours=25)
    with pytest.raises(ValidationError):
        Settings(min_free_disk_percent=101)


def test_secret_like_environment_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="secret-like"):
        load_settings(
            {
                "GENERATION_ADAPTER": "mock",
                "COMFYUI_API_TOKEN": "must-not-enter-application-config",
            }
        )


def test_unrelated_process_credentials_do_not_break_application_startup() -> None:
    settings = load_settings(
        {
            "GENERATION_ADAPTER": "mock",
            "GITHUB_PERSONAL_ACCESS_TOKEN": "external-tool-credential",
        }
    )

    assert settings.generation_adapter == "mock"


def test_environment_aliases_are_loaded_without_posix_path_assumptions() -> None:
    settings = load_settings(
        {
            "GENERATION_ADAPTER": "mock",
            "STORAGE_ROOT": "runtime/storage",
            "DATABASE_PATH": "runtime/storage/jobs.sqlite3",
            "MAX_UPLOAD_BYTES": "10485760",
            "RETENTION_HOURS": "24",
            "MIN_FREE_DISK_PERCENT": "10",
            "COMFYUI_BASE_URL": "http://127.0.0.1:8188",
        }
    )

    assert settings.storage_root == Path("runtime/storage")
    assert settings.database_path == Path("runtime/storage/jobs.sqlite3")
