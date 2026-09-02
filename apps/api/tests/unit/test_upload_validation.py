from __future__ import annotations

import io
from pathlib import Path

import pytest

from local3d.services.image_validation import (
    LowStorageError,
    UploadValidationError,
    ensure_disk_admission,
    validate_upload,
)


FIXTURES = Path(__file__).parents[4] / "fixtures/inputs"
MAX_BYTES = 10 * 1024 * 1024


@pytest.mark.parametrize(
    ("name", "content_type"),
    [("valid-reference.png", "image/png"), ("valid-reference.jpg", "image/jpeg")],
)
def test_valid_jpeg_and_png_are_decoded_and_hashed(name: str, content_type: str) -> None:
    result = validate_upload(
        io.BytesIO((FIXTURES / name).read_bytes()),
        filename=name,
        content_type=content_type,
        max_bytes=MAX_BYTES,
    )

    assert result.content_type == content_type
    assert result.size_bytes > 0
    assert len(result.sha256) == 64


def test_exact_configured_limit_is_allowed() -> None:
    data = (FIXTURES / "valid-reference.png").read_bytes()
    result = validate_upload(io.BytesIO(data), filename="input.png", content_type="image/png", max_bytes=len(data))

    assert result.size_bytes == len(data)


@pytest.mark.parametrize(
    "name",
    ["corrupt-image.png", "spoofed-extension.jpg", "oversized-reference.png"],
)
def test_corrupt_spoofed_and_oversized_uploads_are_rejected(name: str) -> None:
    with pytest.raises(UploadValidationError):
        validate_upload(
            io.BytesIO((FIXTURES / name).read_bytes()),
            filename=name,
            content_type="image/png" if name.endswith(".png") else "image/jpeg",
            max_bytes=MAX_BYTES,
        )


def test_stream_is_bounded_before_image_decode() -> None:
    stream = io.BytesIO(b"x" * (MAX_BYTES + 1))

    with pytest.raises(UploadValidationError, match="large"):
        validate_upload(stream, filename="input.png", content_type="image/png", max_bytes=MAX_BYTES)


def test_low_disk_blocks_new_job_admission() -> None:
    with pytest.raises(LowStorageError):
        ensure_disk_admission(9.99, minimum_free_percent=10)
    ensure_disk_admission(10, minimum_free_percent=10)

