from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "verify"))
import test_origin_lockdown as lockdown  # noqa: E402


def test_single_node_ports_are_the_only_prohibited_application_ports():
    assert lockdown.PROHIBITED_TCP_PORTS == (3000, 8000, 8080, 8188)
    assert "wireguard" not in Path(ROOT / "scripts/verify/test_origin_lockdown.py").read_text().lower()


def test_connected_fails_and_refused_or_reset_passes():
    assert lockdown.classify_probe(lockdown.CONNECTED)[0] == lockdown.FAIL
    assert lockdown.classify_probe(lockdown.REFUSED)[0] == lockdown.PASS
    assert lockdown.classify_probe(lockdown.RESET)[0] == lockdown.PASS


def test_timeout_is_inconclusive():
    verdict, reason = lockdown.classify_probe(lockdown.TIMEOUT)
    assert verdict == lockdown.INCONCLUSIVE
    assert "not proof" in reason


def test_external_attestation_and_address_are_required(capsys):
    assert lockdown.main([]) == 2
    assert "confirm-off-campus" in capsys.readouterr().err
    assert lockdown.main(["--confirm-off-campus", "--origin-address", "203.0.113.9"]) == 2
    assert lockdown.APPROVED_ORIGIN_ADDRESS in capsys.readouterr().err
