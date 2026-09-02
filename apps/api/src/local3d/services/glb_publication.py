from __future__ import annotations

import json
import os
import struct
import tempfile
from pathlib import Path
from typing import Sequence


class PublicationError(ValueError):
    """Raised when a candidate is not a single valid textured GLB."""


def _load_glb(path: Path) -> dict[str, object]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PublicationError("GLB candidate cannot be read") from exc
    if len(data) < 20 or data[:4] != b"glTF":
        raise PublicationError("invalid GLB header")
    version, declared_length = struct.unpack_from("<II", data, 4)
    if version != 2 or declared_length != len(data):
        raise PublicationError("unsupported GLB version or length")
    offset = 12
    json_chunk: bytes | None = None
    while offset + 8 <= len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        if offset + chunk_length > len(data):
            raise PublicationError("GLB chunk exceeds file length")
        chunk = data[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            json_chunk = chunk
    if json_chunk is None:
        raise PublicationError("missing GLB JSON chunk")
    try:
        document = json.loads(json_chunk.decode("utf-8").rstrip(" \t\r\n\0"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationError("invalid GLB JSON") from exc
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise PublicationError("missing glTF 2.0 metadata")
    return document


def _validate_textured_glb(path: Path) -> None:
    document = _load_glb(path)
    meshes = document.get("meshes", [])
    if not isinstance(meshes, list) or not meshes:
        raise PublicationError("GLB has no mesh")
    primitives = [
        primitive
        for mesh in meshes
        if isinstance(mesh, dict)
        for primitive in mesh.get("primitives", [])
        if isinstance(primitive, dict)
    ]
    if not any("POSITION" in primitive.get("attributes", {}) for primitive in primitives):
        raise PublicationError("GLB has no POSITION attribute")
    if not any("TEXCOORD_0" in primitive.get("attributes", {}) for primitive in primitives):
        raise PublicationError("GLB has no UV attribute")
    if not isinstance(document.get("materials"), list) or not document["materials"]:
        raise PublicationError("GLB has no material")
    if not isinstance(document.get("textures"), list) or not document["textures"]:
        raise PublicationError("GLB has no texture")
    if not isinstance(document.get("images"), list) or not document["images"]:
        raise PublicationError("GLB has no image")


def publish_glb(candidates: Sequence[Path], destination: Path) -> Path:
    if len(candidates) != 1:
        raise PublicationError("exactly one GLB candidate is required")
    candidate = Path(candidates[0])
    if not candidate.is_file():
        raise PublicationError("GLB candidate is missing")
    _validate_textured_glb(candidate)

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=target.parent, prefix=f".{target.name}.", suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            with candidate.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    temporary.write(chunk)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return target
