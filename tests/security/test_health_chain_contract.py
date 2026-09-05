"""Static contract tests for the feature-003 layered health chain
(scripts/windows/health_chain.ps1), per
specs/003-outbound-tunnel-entry/contracts/health-chain.md H1-H2 and FR-023c/
FR-023e.

These tests parse the health-chain script's text - they never run it or
touch hardware - and assert:

  - all six layers are implemented as independently callable functions
  - the GPU layer's probe is nvidia-smi (OS-level, engine-independent),
    per the decision recorded in evidence/public-deployment/health-probe-decision.md
  - the GPU layer probe does not call into the ComfyUI/AI-engine client,
    which would make it derive GPU health from the engine it must be
    independent of (the violation FR-023c forbids)
  - the AI-engine layer is a separate function from the GPU layer
  - no layer function silently returns "healthy" without actually probing
    anything (a bare `return $true` with no check is the failure mode this
    guards against)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HEALTH_CHAIN_SCRIPT = REPO_ROOT / "scripts" / "windows" / "health_chain.ps1"

# H1: layer name -> substrings expected to identify its probe function.
EXPECTED_LAYERS = [
    "PrivateBinding",
    "JobService",
    "Gpu",
    "AiEngine",
]


def _read_script() -> str:
    if not HEALTH_CHAIN_SCRIPT.exists():
        pytest.fail(f"{HEALTH_CHAIN_SCRIPT} does not exist yet.")
    return HEALTH_CHAIN_SCRIPT.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    """Strip full-line '#' comments so explanatory prose (which may
    legitimately name a forbidden call to explain why it's absent) doesn't
    trip a substring check meant for actual code."""
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))


def test_all_laptop_owned_layers_are_independently_callable_functions() -> None:
    text = _read_script()
    for layer in EXPECTED_LAYERS:
        assert re.search(rf"function\s+Test-{layer}Health", text, re.IGNORECASE), (
            f"Expected an independently callable Test-{layer}Health function; "
            "each layer must be checkable on its own (FR-023c)."
        )


def test_gpu_layer_uses_nvidia_smi_not_the_ai_engine() -> None:
    """Per the T027 decision: GPU health must come from an OS-level probe
    that does not depend on the AI engine, so GPU can be reported ahead of
    it without violating FR-023c."""
    text = _read_script()
    gpu_function_match = re.search(r"function\s+Test-GpuHealth\s*\{(.*?)\n\}", text, re.IGNORECASE | re.DOTALL)
    assert gpu_function_match, "Test-GpuHealth function not found."
    gpu_body = _code_only(gpu_function_match.group(1))

    assert "nvidia-smi" in gpu_body.lower(), "The GPU layer must probe via nvidia-smi, not derive its state from the AI engine."
    assert "system_stats" not in gpu_body.lower(), (
        "The GPU layer must not call the AI engine's /system_stats endpoint - "
        "that would make GPU health depend on a layer it is supposed to be independent of."
    )
    assert "comfy" not in gpu_body.lower(), "The GPU layer must not reference ComfyUI at all."


def test_ai_engine_layer_is_distinct_from_gpu_layer() -> None:
    text = _read_script()
    assert re.search(r"function\s+Test-AiEngineHealth\s*\{", text, re.IGNORECASE), "Test-AiEngineHealth function not found."
    engine_match = re.search(r"function\s+Test-AiEngineHealth\s*\{(.*?)\n\}", text, re.IGNORECASE | re.DOTALL)
    assert engine_match
    # The engine layer is expected to use ComfyUI's own status endpoint -
    # this is legitimate here (unlike in the GPU layer above), since the
    # engine layer's whole job is to report engine-specific readiness.
    assert "system_stats" in engine_match.group(1).lower(), (
        "Test-AiEngineHealth should probe ComfyUI's /system_stats for engine-specific readiness."
    )


def test_no_layer_function_is_a_bare_stub() -> None:
    """Guards against a layer reporting healthy without actually checking
    anything - the specific failure mode FR-023c's 'must not report healthy
    on the strength of a downstream layer it did not verify' is meant to
    prevent taken to its simplest form."""
    text = _read_script()
    for layer in EXPECTED_LAYERS:
        match = re.search(rf"function\s+Test-{layer}Health\s*\{{(.*?)\n\}}", text, re.IGNORECASE | re.DOTALL)
        assert match, f"Test-{layer}Health function body not found."
        body = match.group(1).strip()
        # A stub is a body whose only non-comment statement is a bare
        # return of a literal boolean.
        non_comment_lines = [line for line in body.splitlines() if line.strip() and not line.strip().startswith("#")]
        is_stub = len(non_comment_lines) <= 1 and re.match(r"^\s*return\s+\$(true|false)\s*$", non_comment_lines[0] if non_comment_lines else "", re.IGNORECASE)
        assert not is_stub, f"Test-{layer}Health must not be a bare stub that returns a literal without probing anything."
