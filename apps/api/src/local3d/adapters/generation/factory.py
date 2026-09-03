from __future__ import annotations

from .base import GenerationAdapter
from .comfy import ComfyGenerationAdapter
from .comfy_client import ComfyClient
from .output_resolver import OutputResolver
from .workflow_mapper import WorkflowMapper, WorkflowMappingError
from ...config import Settings


class AdapterConfigurationError(RuntimeError):
    """Raised when the configured real generation adapter cannot be built safely.

    Callers must treat this as a fail-closed signal (safe 503 on readiness),
    never as a reason to silently fall back to another adapter.
    """


def build_real_adapter(settings: Settings) -> GenerationAdapter:
    """Build the real ComfyUI-backed adapter from the pinned workflow manifest.

    Verifies the manifest can be loaded and its referenced workflow's hash
    matches before any network client is constructed, per the workflow
    manifest contract's startup compatibility check.
    """

    if settings.comfyui_output_root is None:
        raise AdapterConfigurationError(
            "COMFYUI_OUTPUT_ROOT is not configured; the real adapter cannot "
            "verify job output without it"
        )
    try:
        mapper = WorkflowMapper.from_manifest(settings.workflow_manifest_path)
    except WorkflowMappingError as exc:
        raise AdapterConfigurationError(f"workflow manifest is invalid: {exc}") from exc
    except OSError as exc:
        raise AdapterConfigurationError("workflow manifest is unreadable") from exc

    client = ComfyClient(settings.comfyui_base_url)
    resolver = OutputResolver(settings.comfyui_output_root)
    return ComfyGenerationAdapter(client=client, mapper=mapper, resolver=resolver)
