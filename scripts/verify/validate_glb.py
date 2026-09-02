#!/usr/bin/env python3
"""Perform structural GLB checks required by the MVP publication contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys


def load_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("invalid GLB header")
    version, declared_length = struct.unpack_from("<II", data, 4)
    if version != 2 or declared_length != len(data):
        raise ValueError("unsupported GLB version or length mismatch")
    offset = 12
    json_chunk: bytes | None = None
    while offset + 8 <= len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            json_chunk = chunk
    if json_chunk is None:
        raise ValueError("missing JSON chunk")
    document = json.loads(json_chunk.decode("utf-8").rstrip(" \t\r\n\0"))
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise ValueError("missing glTF 2.0 asset metadata")
    return document


def validate(path: Path, require_mesh: bool, require_uv: bool, require_material: bool, require_texture: bool) -> list[str]:
    document = load_glb(path)
    errors: list[str] = []
    meshes = document.get("meshes", [])
    if require_mesh and not meshes:
        errors.append("no meshes")
    primitives = [primitive for mesh in meshes for primitive in mesh.get("primitives", [])]
    if require_mesh and not any("POSITION" in primitive.get("attributes", {}) for primitive in primitives):
        errors.append("no mesh primitive with POSITION")
    if require_uv and not any("TEXCOORD_0" in primitive.get("attributes", {}) for primitive in primitives):
        errors.append("no TEXCOORD_0 UV attribute")
    if require_material and not document.get("materials"):
        errors.append("no materials")
    if require_texture and not document.get("textures"):
        errors.append("no textures")
    if require_texture and not document.get("images"):
        errors.append("no images")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--require-mesh", action="store_true")
    parser.add_argument("--require-uv", action="store_true")
    parser.add_argument("--require-material", action="store_true")
    parser.add_argument("--require-texture", action="store_true")
    args = parser.parse_args()
    try:
        errors = validate(args.path, args.require_mesh, args.require_uv, args.require_material, args.require_texture)
    except (OSError, ValueError, json.JSONDecodeError, struct.error) as exc:
        errors = [str(exc)]
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

