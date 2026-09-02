from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError


class UploadValidationError(ValueError):
    """Raised when an upload is unsupported, corrupt, or exceeds its limit."""


class LowStorageError(ValueError):
    """Raised when admission is disabled by the configured free-space floor."""


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    data: bytes
    filename_extension: str
    content_type: str
    size_bytes: int
    sha256: str


_SUPPORTED = {".png": ("PNG", "image/png"), ".jpg": ("JPEG", "image/jpeg"), ".jpeg": ("JPEG", "image/jpeg")}


def validate_upload(
    stream: BinaryIO,
    *,
    filename: str,
    content_type: str | None,
    max_bytes: int,
) -> ValidatedUpload:
    extension = Path(filename).suffix.lower()
    windows_name = PureWindowsPath(filename).name
    if not filename or Path(filename).name != filename or windows_name != filename:
        raise UploadValidationError("filename is not supported")
    expected = _SUPPORTED.get(extension)
    if expected is None or content_type != expected[1]:
        raise UploadValidationError("only JPEG and PNG images are supported")
    if max_bytes <= 0:
        raise UploadValidationError("upload limit is invalid")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(min(64 * 1024, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise UploadValidationError("file is too large")
    data = b"".join(chunks)
    if not data:
        raise UploadValidationError("file is empty")

    try:
        with Image.open(io.BytesIO(data)) as image:
            detected_format = image.format
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UploadValidationError("image cannot be decoded") from exc
    if detected_format != expected[0]:
        raise UploadValidationError("image content does not match its extension")

    return ValidatedUpload(
        data=data,
        filename_extension=extension,
        content_type=expected[1],
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def ensure_disk_admission(free_percent: float, *, minimum_free_percent: float = 10) -> None:
    if free_percent < minimum_free_percent:
        raise LowStorageError("new jobs are temporarily disabled because storage is low")
