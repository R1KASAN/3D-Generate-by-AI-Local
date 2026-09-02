from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Literal
from uuid import UUID


class PathViolation(ValueError):
    """Raised when a requested path is outside its server-owned job directory."""


@dataclass(frozen=True, slots=True)
class JobPaths:
    job_id: UUID
    job_root: Path
    upload_dir: Path
    work_dir: Path
    output_dir: Path
    quarantine_dir: Path


class JobStorage:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def ensure_job(self, job_id: UUID | str) -> JobPaths:
        parsed_id = self._parse_job_id(job_id)
        job_root = self.root / str(parsed_id)
        upload_dir = job_root / "uploads"
        work_dir = job_root / "work"
        output_dir = job_root / "outputs"
        quarantine_dir = job_root / "quarantine"
        for directory in (upload_dir, work_dir, output_dir, quarantine_dir):
            directory.mkdir(parents=True, exist_ok=True)
        return JobPaths(parsed_id, job_root, upload_dir, work_dir, output_dir, quarantine_dir)

    def resolve_path(self, job_id: UUID | str, relative_path: str) -> Path:
        paths = self.ensure_job(job_id)
        requested = Path(relative_path)
        windows_requested = PureWindowsPath(relative_path)
        if (
            requested.is_absolute()
            or windows_requested.is_absolute()
            or windows_requested.drive
            or "\x00" in relative_path
        ):
            raise PathViolation("absolute paths are not allowed")
        resolved = (paths.job_root / requested).resolve(strict=False)
        if not resolved.is_relative_to(paths.job_root.resolve()):
            raise PathViolation("path escapes the job directory")
        return resolved

    def atomic_write(
        self,
        job_id: UUID | str,
        kind: Literal["upload", "work", "output", "quarantine"],
        filename: str,
        data: bytes,
    ) -> Path:
        paths = self.ensure_job(job_id)
        directory = {
            "upload": paths.upload_dir,
            "work": paths.work_dir,
            "output": paths.output_dir,
            "quarantine": paths.quarantine_dir,
        }[kind]
        if not filename or Path(filename).name != filename or PureWindowsPath(filename).name != filename:
            raise PathViolation("filename must be one path component")
        target = self.resolve_path(job_id, f"{directory.relative_to(paths.job_root)}/{filename}")
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=directory, prefix=f".{filename}.", suffix=".tmp", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, target)
            return target
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def resolve_asset(self, job_id: UUID | str, relative_path: str) -> Path:
        """Resolve a persisted storage-root-relative asset within one job."""
        parsed_id = self._parse_job_id(job_id)
        requested = Path(relative_path)
        windows_requested = PureWindowsPath(relative_path)
        if requested.is_absolute() or windows_requested.is_absolute() or windows_requested.drive:
            raise PathViolation("asset path must be relative")
        job_root = (self.root / str(parsed_id)).resolve(strict=False)
        resolved = (self.root / requested).resolve(strict=False)
        if not resolved.is_relative_to(job_root):
            raise PathViolation("asset path escapes the job directory")
        return resolved

    def remove_job(self, job_id: UUID | str) -> None:
        """Remove one server-owned job tree without accepting arbitrary paths."""
        parsed_id = self._parse_job_id(job_id)
        job_root = (self.root / str(parsed_id)).resolve(strict=False)
        if not job_root.is_relative_to(self.root):
            raise PathViolation("job path escapes storage root")
        if job_root.exists():
            shutil.rmtree(job_root)

    @staticmethod
    def _parse_job_id(job_id: UUID | str) -> UUID:
        try:
            return job_id if isinstance(job_id, UUID) else UUID(str(job_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise PathViolation("job id must be a UUID") from exc
