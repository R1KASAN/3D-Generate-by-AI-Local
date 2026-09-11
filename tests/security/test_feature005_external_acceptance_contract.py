from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("feature005_external", ROOT / "scripts/verify/test_feature005_external_acceptance.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "value",
    [
        "http://www.mangosgo.com/mango74/",
        "https://127.0.0.1:8000/api/v1",
        "https://161.200.90.4/api/v1",
        "https://example.trycloudflare.com/api/v1",
        "https://user:secret@example.com/api/v1",
    ],
)
def test_external_verifier_rejects_unsafe_endpoints(value: str) -> None:
    with pytest.raises(ValueError):
        MODULE.validate_public_endpoint(value)


def test_external_verifier_accepts_stable_https_hostname() -> None:
    assert MODULE.validate_public_endpoint("https://mango74-api.example.com/api/v1/") == "https://mango74-api.example.com/api/v1"
