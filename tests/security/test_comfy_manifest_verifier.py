from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts" / "verify" / "verify_comfy_manifest.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_comfy_manifest", VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workflow_hash_is_stable_across_windows_line_endings(tmp_path: Path) -> None:
    verifier = load_verifier()
    lf = b'{\n  "1": {"class_type": "LoadImage"}\n}\n'
    workflow = tmp_path / "workflow.json"
    workflow.write_bytes(lf.replace(b"\n", b"\r\n"))

    assert verifier.sha256_json_file(workflow) == hashlib.sha256(lf).hexdigest()


def test_workflow_hash_does_not_reformat_json(tmp_path: Path) -> None:
    verifier = load_verifier()
    workflow = tmp_path / "workflow.json"
    workflow.write_bytes(b'{"a":1}')

    assert verifier.sha256_json_file(workflow) != hashlib.sha256(b'{"a": 1}').hexdigest()
