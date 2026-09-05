from pathlib import Path
import sys
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "verify"))

from _evidence import Check, mask_text, write_evidence  # noqa: E402


def test_mask_text_masks_standalone_ipv4_literals():
    assert mask_text("origin 161.200.90.4 and loopback 127.0.0.1") == (
        "origin 161.200.90.x and loopback 127.0.0.x"
    )


def test_write_evidence_masks_context_checks_and_footnote(tmp_path: Path):
    evidence = tmp_path / "evidence.md"
    write_evidence(
        evidence,
        "Test Evidence",
        "TEST",
        ["host=161.200.90.4"],
        [Check("probe", "connected to 10.10.0.2", "not 192.168.1.20", "PASS")],
        "PASS",
        footnote="never disclose 8.8.8.8",
    )

    text = evidence.read_text(encoding="utf-8")
    for address in ("161.200.90.4", "10.10.0.2", "192.168.1.20", "8.8.8.8"):
        assert address not in text
    assert "161.200.90.x" in text
    assert "10.10.0.x" in text


@pytest.mark.parametrize("filename", [
    "reboot-matrix.md", "interruption-recovery.md", "public-route-disable.md",
    "provider-limits.md", "fallback-policy.md", "egress-identity.md",
    "external-journey.md", "outbound-implementation.md",
    "wireguard-transport-boundary.md", "wireguard-transport-boundary-live.md",
    "transport-reachability.md", "mobility.md",
])
def test_phase_four_to_six_evidence_masks_every_field(tmp_path, filename):
    path = tmp_path / filename
    unsafe = "10.10.0.2 2001:db8::1234 X-Job-Token=synthetic-credential"
    write_evidence(path, unsafe, "T056", [unsafe],
                   [Check(unsafe, unsafe, unsafe, "BLOCKED")], "BLOCKED", unsafe)
    text = path.read_text(encoding="utf-8")
    assert "10.10.0.2" not in text
    assert "2001:db8::1234" not in text
    assert "synthetic-credential" not in text
