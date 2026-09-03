from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from local3d.adapters.generation.output_resolver import OutputDiscoveryError, OutputResolver


def _job_dir(tmp_path: Path, job_id: str) -> Path:
    path = tmp_path / "output" / "jobs" / job_id
    path.mkdir(parents=True)
    return path


def test_resolver_returns_one_matching_glb(tmp_path: Path) -> None:
    job_id = str(uuid4())
    job_dir = _job_dir(tmp_path, job_id)
    candidate = job_dir / "model_00001.glb"
    candidate.write_bytes(b"glb")

    assert OutputResolver(tmp_path / "output").resolve(job_id) == candidate


def test_resolver_rejects_zero_candidates(tmp_path: Path) -> None:
    job_id = str(uuid4())
    _job_dir(tmp_path, job_id)

    with pytest.raises(OutputDiscoveryError, match="exactly one"):
        OutputResolver(tmp_path / "output").resolve(job_id)


def test_resolver_rejects_multiple_candidates(tmp_path: Path) -> None:
    job_id = str(uuid4())
    job_dir = _job_dir(tmp_path, job_id)
    (job_dir / "model_a.glb").write_bytes(b"a")
    (job_dir / "model_b.glb").write_bytes(b"b")

    with pytest.raises(OutputDiscoveryError, match="exactly one"):
        OutputResolver(tmp_path / "output").resolve(job_id)


def test_resolver_rejects_wrong_job_prefix_and_stale_files(tmp_path: Path) -> None:
    job_id = str(uuid4())
    job_dir = _job_dir(tmp_path, job_id)
    wrong_prefix = job_dir / "other.glb"
    wrong_prefix.write_bytes(b"wrong")
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    os.utime(wrong_prefix, (old.timestamp(), old.timestamp()))

    with pytest.raises(OutputDiscoveryError, match="exactly one"):
        OutputResolver(tmp_path / "output").resolve(job_id, not_before=datetime.now(timezone.utc))


def test_resolver_rejects_path_escape_and_other_job_output(tmp_path: Path) -> None:
    job_id = str(uuid4())
    job_dir = _job_dir(tmp_path, job_id)
    outside = tmp_path / "outside.glb"
    outside.write_bytes(b"outside")
    try:
        (job_dir / "model.glb").symlink_to(outside)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is unavailable")
        raise
    other = _job_dir(tmp_path, str(uuid4())) / "model.glb"
    other.write_bytes(b"other")

    with pytest.raises(OutputDiscoveryError, match="inside"):
        OutputResolver(tmp_path / "output").resolve(job_id)


def test_resolver_rejects_non_uuid_job_ids(tmp_path: Path) -> None:
    with pytest.raises(OutputDiscoveryError, match="job"):
        OutputResolver(tmp_path / "output").resolve("../../other")
