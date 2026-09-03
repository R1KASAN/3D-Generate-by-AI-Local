from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

from local3d.services.job_tokens import (
    create_job_token,
    digest_job_token,
    verify_job_token,
)
from local3d.storage.job_storage import JobStorage, PathViolation


def test_each_job_gets_separate_server_owned_directories(tmp_path: Path) -> None:
    storage = JobStorage(tmp_path / "storage")
    first = storage.ensure_job(uuid4())
    second = storage.ensure_job(uuid4())

    assert first.job_id != second.job_id
    assert first.upload_dir.is_dir()
    assert first.work_dir.is_dir()
    assert first.output_dir.is_dir()
    assert first.quarantine_dir.is_dir()
    assert first.output_dir != second.output_dir
    assert first.output_dir.is_relative_to(storage.root)


@pytest.mark.parametrize("relative_path", ["../other/model.glb", "../../model.glb", "/tmp/model.glb"])
def test_relative_path_must_not_escape_job_root(tmp_path: Path, relative_path: str) -> None:
    storage = JobStorage(tmp_path / "storage")
    job_id = uuid4()
    storage.ensure_job(job_id)

    with pytest.raises(PathViolation):
        storage.resolve_path(job_id, relative_path)


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    storage = JobStorage(tmp_path / "storage")
    job_id = uuid4()
    paths = storage.ensure_job(job_id)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, paths.work_dir / "escape")
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is unavailable")
        raise

    with pytest.raises(PathViolation):
        storage.resolve_path(job_id, "work/escape/secret.bin")


def test_atomic_write_publishes_only_after_complete_write(tmp_path: Path) -> None:
    storage = JobStorage(tmp_path / "storage")
    job_id = uuid4()
    storage.ensure_job(job_id)

    target = storage.atomic_write(job_id, "output", "model.glb", b"complete-glb")

    assert target.read_bytes() == b"complete-glb"
    assert not list(target.parent.glob("*.tmp"))
    assert target.is_relative_to(storage.root / str(job_id))


def test_token_is_returned_once_and_only_digest_verifies() -> None:
    token, digest = create_job_token()

    assert len(token) >= 43  # 256 bits encoded with URL-safe base64
    assert digest == digest_job_token(token)
    assert verify_job_token(token, digest)
    assert not verify_job_token(token + "x", digest)
    assert not verify_job_token(token, "0" * 64)

