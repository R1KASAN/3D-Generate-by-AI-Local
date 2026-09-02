from __future__ import annotations

from datetime import datetime
from pathlib import Path, PureWindowsPath
from uuid import UUID


class OutputDiscoveryError(ValueError):
    """Raised when a job does not have exactly one safe GLB candidate."""


class OutputResolver:
    """Resolve one fresh GLB below ``ComfyUI/output/jobs/<job_id>``."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = Path(output_root).expanduser().resolve()

    def resolve(
        self,
        job_id: UUID | str,
        *,
        prefix: str = "model",
        not_before: datetime | None = None,
    ) -> Path:
        parsed_id = _parse_job_id(job_id)
        if not prefix or Path(prefix).name != prefix or PureWindowsPath(prefix).name != prefix:
            raise OutputDiscoveryError("output prefix is invalid")
        job_dir = (self.output_root / "jobs" / str(parsed_id)).resolve(strict=False)
        if not job_dir.is_relative_to(self.output_root):
            raise OutputDiscoveryError("job output must remain inside output root")
        if not job_dir.is_dir():
            raise OutputDiscoveryError("expected exactly one GLB candidate")

        candidates: list[Path] = []
        for path in job_dir.rglob("*"):
            if path.suffix.lower() != ".glb":
                continue
            resolved = path.resolve(strict=False)
            if not resolved.is_relative_to(job_dir):
                raise OutputDiscoveryError("candidate must remain inside job output")
            if not path.is_file() or not path.name.startswith(prefix):
                continue
            if not path.stat().st_size:
                continue
            if not_before is not None and path.stat().st_mtime < not_before.timestamp():
                continue
            candidates.append(resolved)

        if len(candidates) != 1:
            raise OutputDiscoveryError("expected exactly one GLB candidate")
        return candidates[0]


def _parse_job_id(job_id: UUID | str) -> UUID:
    try:
        return job_id if isinstance(job_id, UUID) else UUID(str(job_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise OutputDiscoveryError("job id is invalid") from exc
