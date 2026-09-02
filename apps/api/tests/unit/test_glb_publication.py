from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from local3d.services.glb_publication import PublicationError, publish_glb


FIXTURE = Path(__file__).parents[4] / "fixtures/models/sample-textured.glb"


def _write_minimal_glb(path: Path, *, textured: bool) -> None:
    document = {
        "asset": {"version": "2.0"},
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "TEXCOORD_0": 1}}]}],
        "materials": [{}],
    }
    if textured:
        document["textures"] = [{}]
        document["images"] = [{}]
    encoded = json.dumps(document, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    length = 12 + 8 + len(encoded)
    path.write_bytes(b"glTF" + struct.pack("<II", 2, length) + struct.pack("<II", len(encoded), 0x4E4F534A) + encoded)


def test_zero_or_multiple_candidates_are_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "model.glb"

    with pytest.raises(PublicationError, match="exactly one"):
        publish_glb([], destination)

    with pytest.raises(PublicationError, match="exactly one"):
        publish_glb([FIXTURE, FIXTURE], destination)


def test_malformed_and_shape_only_candidates_are_rejected(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.glb"
    malformed.write_bytes(b"not-glb")
    shape_only = tmp_path / "shape-only.glb"
    _write_minimal_glb(shape_only, textured=False)

    for candidate in (malformed, shape_only):
        with pytest.raises(PublicationError):
            publish_glb([candidate], tmp_path / "out.glb")


def test_valid_textured_glb_is_atomically_published(tmp_path: Path) -> None:
    destination = tmp_path / "published" / "model.glb"

    result = publish_glb([FIXTURE], destination)

    assert result == destination
    assert destination.read_bytes() == FIXTURE.read_bytes()
    assert not list(destination.parent.glob("*.tmp"))

