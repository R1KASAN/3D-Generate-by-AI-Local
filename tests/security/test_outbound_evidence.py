"""Evidence must fail closed when observation is incomplete or contradictory."""
import io
import json
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/verify"))
import test_dns_disclosure as dns
import test_egress_identity as egress
import test_origin_lockdown as lockdown


@pytest.mark.parametrize("payload", [
    {"success": False, "result": [{"origin_ip": egress.APPROVED_ORIGIN_ADDRESS}]},
    {"success": True, "result": [{"conns": [
        {"origin_ip": egress.APPROVED_ORIGIN_ADDRESS, "is_pending_reconnect": False},
        {"origin_ip": "192.0.2.5", "is_pending_reconnect": False},
    ]}]},
    {"success": True, "result": [{"conns": [
        {"origin_ip": egress.APPROVED_ORIGIN_ADDRESS, "is_pending_reconnect": True},
    ]}]},
])
def test_cloudflare_does_not_pass_on_partial_or_inactive_match(monkeypatch, payload):
    monkeypatch.setattr(egress.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(payload).encode()))
    assert egress._cloudflare_check("account", "tunnel", "secret").verdict != "PASS"


def test_cloudflare_active_approved_connector(monkeypatch):
    payload = {"success": True, "result": [{"conns": [
        {"origin_ip": egress.APPROVED_ORIGIN_ADDRESS, "is_pending_reconnect": False},
    ]}]}
    monkeypatch.setattr(egress.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(payload).encode()))
    assert egress._cloudflare_check("account", "tunnel", "secret").verdict == "PASS"


def test_local_network_error_is_not_lockdown_evidence(monkeypatch):
    def unavailable(*args, **kwargs):
        raise socket.gaierror("resolver unavailable")
    monkeypatch.setattr(lockdown.socket, "create_connection", unavailable)
    outcome = lockdown.probe_tcp("192.0.2.1", 443, 1)
    assert lockdown.classify_probe(outcome)[0] == lockdown.INCONCLUSIVE


def test_dns_unverified_provider_ranges_exit_unsuccessfully(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["probe", "--hostname", "example.org", "--confirm-off-campus"])
    monkeypatch.setattr(dns, "_resolve", lambda _: {"1.1.1.1"})
    monkeypatch.setattr(dns, "_fetch_cloudflare_ranges", lambda: None)
    assert dns.main() != 0
