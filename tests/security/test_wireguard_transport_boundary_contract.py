"""Contract test for the origin's WireGuard transport boundary
(feature 003, T056a/T056b, SC-018, contracts/compute-link.md C1a-1).

Two things must both hold, and this file checks them separately:

1. The checked-in declaration (`deploy/wireguard/origin-transport-boundary.md`,
   T058a) actually satisfies every C1a-1 rule (T056a).
2. The verifier that reads it (`scripts/verify/test_wireguard_transport_boundary.py`,
   T058b) genuinely rejects a boundary that violates each rule, rather than
   passing vacuously because it only confirms the expected fields exist
   (T056b). A verifier that never sees a bad declaration cannot prove it
   would catch one.
"""

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "verify"))

import test_wireguard_transport_boundary as boundary  # noqa: E402

DECLARATION_PATH = REPO_ROOT / "deploy" / "wireguard" / "origin-transport-boundary.md"

VALID_FIELDS: dict[str, str] = {
    "address": boundary.APPROVED_ORIGIN_ADDRESS,
    "protocol": boundary.REQUIRED_PROTOCOL,
    "port": str(boundary.REQUIRED_PORT),
    "service": boundary.REQUIRED_SERVICE,
    "peer_admission": boundary.REQUIRED_PEER_ADMISSION,
    "origin_allowed_ips": boundary.REQUIRED_ORIGIN_ALLOWED_IPS,
    "laptop_allowed_ips": boundary.REQUIRED_LAPTOP_ALLOWED_IPS,
    "tcp_application_listener": "none",
    "management_listener": "none",
    "catch_all_inbound_rule": "none",
    "router_port_forwarding": "none",
    "gpu_laptop_internet_exposure": "none",
}


def _all_pass(checks: list[boundary.Check]) -> bool:
    return all(c.verdict == "PASS" for c in checks)


def _verdict_for(checks: list[boundary.Check], name: str) -> str:
    matches = [c.verdict for c in checks if c.name == name]
    assert matches, f"no check named {name!r} was produced"
    return matches[0]


# --- T056a: the checked-in declaration is real and satisfies every rule ----

def test_declaration_file_exists():
    assert DECLARATION_PATH.exists(), (
        "deploy/wireguard/origin-transport-boundary.md must exist (T058a) "
        "before this contract can be satisfied"
    )


def test_declaration_file_parses():
    fields = boundary.parse_declaration(DECLARATION_PATH.read_text(encoding="utf-8"))
    assert fields, "the declaration's ```boundary block parsed to no fields"


def test_declaration_satisfies_every_c1a1_rule():
    fields = boundary.parse_declaration(DECLARATION_PATH.read_text(encoding="utf-8"))
    checks = boundary.validate_declaration(fields)
    failing = [(c.name, c.observed, c.expected) for c in checks if c.verdict != "PASS"]
    assert not failing, f"declared boundary fails C1a-1 rules: {failing}"


def test_every_all_field_is_covered_by_the_declaration():
    fields = boundary.parse_declaration(DECLARATION_PATH.read_text(encoding="utf-8"))
    missing = [f for f in boundary.ALL_FIELDS if f not in fields]
    assert not missing, f"declaration is missing fields: {missing}"


# --- T056b: the verifier rejects each individual violation -----------------

def test_valid_fixture_passes_every_rule():
    checks = boundary.validate_declaration(dict(VALID_FIELDS))
    assert _all_pass(checks), [c for c in checks if c.verdict != "PASS"]


@pytest.mark.parametrize(
    "mutation, failing_field",
    [
        ({"address": "203.0.113.9"}, "address"),
        ({"protocol": "tcp"}, "protocol"),
        ({"port": "8443"}, "port"),
        ({"service": "wireguard+ssh"}, "service"),
        ({"peer_admission": "source_ip"}, "peer_admission"),
        ({"origin_allowed_ips": "10.10.0.0/24"}, "origin_allowed_ips"),
        ({"laptop_allowed_ips": "0.0.0.0/0"}, "laptop_allowed_ips"),
        ({"tcp_application_listener": "8080/tcp"}, "tcp_application_listener"),
        ({"management_listener": "22/tcp ssh"}, "management_listener"),
        ({"catch_all_inbound_rule": "any/any -> allow"}, "catch_all_inbound_rule"),
        ({"router_port_forwarding": "51820/udp -> 10.10.0.1"}, "router_port_forwarding"),
        ({"gpu_laptop_internet_exposure": "3000/tcp forwarded"}, "gpu_laptop_internet_exposure"),
    ],
)
def test_each_prohibited_or_narrow_field_rejects_its_violation(
    mutation: dict[str, str], failing_field: str
):
    """A widened peer scope, an added listener, a catch-all rule, or a
    router forward must each be REJECTED — this is the negative-fixture
    obligation T056b adds so the verifier cannot pass vacuously."""
    fields = dict(VALID_FIELDS)
    fields.update(mutation)
    checks = boundary.validate_declaration(fields)
    assert _verdict_for(checks, failing_field) == "FAIL"
    # Every other field must remain unaffected by one field's violation -
    # the report names the specific offending rule, not a blanket failure.
    other_failures = [c.name for c in checks if c.name != failing_field and c.verdict != "PASS"]
    assert not other_failures, f"unrelated fields also failed: {other_failures}"


@pytest.mark.parametrize("missing_field", list(VALID_FIELDS))
def test_a_missing_field_blocks_rather_than_passes(missing_field: str):
    """Fail-closed: an omitted field must never be treated as satisfied by
    default. It is reported BLOCKED (insufficient evidence), never PASS."""
    fields = dict(VALID_FIELDS)
    del fields[missing_field]
    checks = boundary.validate_declaration(fields)
    assert _verdict_for(checks, missing_field) == "BLOCKED"


def test_an_empty_value_blocks_rather_than_passes():
    fields = dict(VALID_FIELDS)
    fields["service"] = ""
    checks = boundary.validate_declaration(fields)
    assert _verdict_for(checks, "service") == "BLOCKED"


def test_overall_verdict_is_fail_when_any_rule_fails():
    fields = dict(VALID_FIELDS)
    fields["catch_all_inbound_rule"] = "any/any -> allow"
    checks = boundary.validate_declaration(fields)
    assert boundary.overall_verdict(checks) == "FAIL"


def test_overall_verdict_is_blocked_when_a_rule_is_unevaluable_but_none_fail():
    fields = dict(VALID_FIELDS)
    del fields["router_port_forwarding"]
    checks = boundary.validate_declaration(fields)
    assert boundary.overall_verdict(checks) == "BLOCKED"


def test_a_declaration_file_with_no_boundary_block_is_a_parse_error():
    with pytest.raises(boundary.DeclarationParseError):
        boundary.parse_declaration("# Just a heading\n\nNo fenced block here.\n")


def test_main_reports_blocked_when_the_declaration_file_is_missing(tmp_path, capsys):
    exit_code = boundary.main([
        "--declaration", str(tmp_path / "does-not-exist.md"),
        "--evidence", str(tmp_path / "evidence.md"),
    ])
    assert exit_code == 2
    assert "BLOCKED" in capsys.readouterr().err


def test_main_passes_on_the_real_checked_in_declaration(tmp_path, capsys):
    exit_code = boundary.main([
        "--declaration", str(DECLARATION_PATH),
        "--evidence", str(tmp_path / "evidence.md"),
    ])
    assert exit_code == 0
    assert (tmp_path / "evidence.md").exists()
