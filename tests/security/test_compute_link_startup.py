"""Feature 003: the GPU laptop's application MUST start independently of the
private binding to the approved origin.

Feature 002 bound the web service to the WireGuard tunnel address and made
it depend on the WireGuard service, because under that architecture the
laptop's web entry *was* the public entry. Feature 003 moves the public
entry to the approved origin, so that arrangement is now a regression: if
WireGuard is down when the laptop boots, the LAN-only workflow (FR-037)
cannot start at all. See specs/003-outbound-tunnel-entry/contracts/compute-link.md C4.
"""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STARTUP_SCRIPT = REPO_ROOT / "scripts" / "windows" / "start_web_service.ps1"
WEB_SERVICE = REPO_ROOT / "deploy" / "windows" / "services" / "web.xml"
API_SERVICE = REPO_ROOT / "deploy" / "windows" / "services" / "api.xml"
COMFY_SERVICE = REPO_ROOT / "deploy" / "windows" / "services" / "comfyui.xml"


def test_web_startup_does_not_wait_on_the_private_binding():
    """FR-023a/FR-023d: starting the app must not be gated on WireGuard."""
    text = STARTUP_SCRIPT.read_text(encoding="utf-8")

    assert "Wait-ForTunnelAddress" not in text
    assert "Wait-ForRecentWireGuardHandshake" not in text
    assert "Wait-ForEdgeReachable" not in text
    assert "latest-handshakes" not in text


def test_web_service_binds_loopback_and_has_no_wireguard_dependency():
    """FR-023d: no feature 001 service may bind the private-binding address
    exclusively, or declare a WireGuard service dependency that would gate
    its own startup on the binding being present."""
    text = WEB_SERVICE.read_text(encoding="utf-8")

    assert "WireGuardTunnel$upstream" not in text
    assert "-TunnelAddress 10.10.0.2" not in text
    assert "-WireGuardInterface" not in text
    assert "10.10.0.2" not in re.sub(r"(?s)<description>.*?</description>", "", text)

    startup_text = STARTUP_SCRIPT.read_text(encoding="utf-8")
    assert "127.0.0.1" in startup_text, "The startup script must bind loopback."
    assert "10.10.0.2" not in startup_text


def test_api_and_comfy_services_have_no_wireguard_dependency():
    """These already bind loopback; confirm neither was ever made to depend
    on the private binding, so the same regression cannot appear here."""
    for service_file in (API_SERVICE, COMFY_SERVICE):
        text = service_file.read_text(encoding="utf-8")
        assert "WireGuardTunnel$upstream" not in text
        assert "10.10.0.2" not in text
