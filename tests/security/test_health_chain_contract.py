from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/windows/health_chain.ps1"


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_single_node_health_layers_are_independent_and_loopback_bound() -> None:
    body = _text()
    for layer in ("Caddy", "Web", "Api", "Storage", "Workflow", "Comfy", "Gpu", "QuickTunnel", "PublicRoute", "ListenerBoundary", "ProcessBoundary"):
        assert re.search(rf"function\s+Test-{layer}Health", body, re.I)
    assert "WireGuard" not in body
    assert "10.10.0." not in body
    assert "127.0.0.1:${CaddyPort}" in body
    assert "127.0.0.1:${ComfyPort}" in body


def test_health_output_is_safe_and_bounded() -> None:
    body = _text()
    assert "TimeoutSec 5" in body
    assert "ConvertTo-Json" in body
    assert "Quick Tunnel URL not supplied" in body
    assert "credentials" not in body.lower()
