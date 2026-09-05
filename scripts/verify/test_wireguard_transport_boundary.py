"""Local/static verifier for the origin's WireGuard transport boundary
(feature 003, T058b, SC-018, contracts/compute-link.md C1a-1).

Option A permits exactly one narrowly scoped WireGuard UDP transport
listener on the approved origin (contracts/compute-link.md C1a). That
listener is the origin's *only* Internet-reachable socket, so unlike feature
002 (where the WireGuard posture rode along behind a hardened `:443`
listener and was never independently tested) this feature specifies,
declares, and verifies that boundary on its own.

This script does **not** touch the live origin — no authorized connection
exists (evidence/public-deployment/operator-inputs.md). It validates the
**declared** boundary in `deploy/wireguard/origin-transport-boundary.md`
against every rule in C1a-1, and reports each rule as its own check so a
gap is named specifically rather than folded into one pass/fail. Matching
the running firewall against this declaration is separate, origin-local
work (tasks.md T066a) that stays MANUAL/BLOCKED until authorized access
exists.

**Fails closed by design**: a missing key, an empty value, or a value this
script does not recognise as satisfying the rule is BLOCKED or FAIL, never
treated as an implicit pass. A verifier that only confirms the *expected*
rules exist would also pass a declaration that has those rules *plus* a
violation (an extra listener, a widened peer scope, a catch-all rule) — see
`tests/security/test_wireguard_transport_boundary.py` for the negative
fixtures that exist specifically to catch that failure mode.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, overall_verdict, write_evidence  # noqa: E402

APPROVED_ORIGIN_ADDRESS = "161.200.90.4"
REQUIRED_PORT = 51820
REQUIRED_PROTOCOL = "udp"
REQUIRED_SERVICE = "wireguard"
REQUIRED_PEER_ADMISSION = "public_key"
REQUIRED_ORIGIN_ALLOWED_IPS = "10.10.0.2/32"
REQUIRED_LAPTOP_ALLOWED_IPS = "10.10.0.1/32"

# Fields whose only acceptable declared value is the literal "none" - each
# names one thing C1a-1 prohibits outright. A missing key, an empty value,
# or any value other than "none" fails the corresponding check.
PROHIBITED_NONE_FIELDS = (
    "tcp_application_listener",
    "management_listener",
    "catch_all_inbound_rule",
    "router_port_forwarding",
    "gpu_laptop_internet_exposure",
)

ALL_FIELDS = (
    "address",
    "protocol",
    "port",
    "service",
    "peer_admission",
    "origin_allowed_ips",
    "laptop_allowed_ips",
) + PROHIBITED_NONE_FIELDS

_FENCE = re.compile(r"```(?:boundary)?\s*\n(.*?)```", re.DOTALL)
_KV_LINE = re.compile(r"^\s*([a-z_]+)\s*:\s*(.+?)\s*$")


class DeclarationParseError(ValueError):
    """Raised when the declaration file has no parseable boundary block."""


def parse_declaration(text: str) -> dict[str, str]:
    """Extract the ```boundary fenced key:value block from a declaration
    document. Raises DeclarationParseError if no such block exists - a
    missing block is a parse failure, not an empty-but-valid declaration."""
    match = _FENCE.search(text)
    if not match:
        raise DeclarationParseError(
            "no ```boundary fenced block found in the declaration file"
        )
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        kv = _KV_LINE.match(line)
        if kv:
            fields[kv.group(1)] = kv.group(2)
    return fields


def validate_declaration(fields: dict[str, str]) -> list[Check]:
    """Check the parsed declaration against every C1a-1 rule. Returns one
    Check per rule; never raises on a missing or malformed field, so a
    caller always gets a complete, individually-named report."""
    checks: list[Check] = []

    def get(key: str) -> str | None:
        value = fields.get(key)
        return value if value else None

    address = get("address")
    checks.append(Check(
        "address",
        address if address else "not declared",
        APPROVED_ORIGIN_ADDRESS,
        "PASS" if address == APPROVED_ORIGIN_ADDRESS else ("BLOCKED" if address is None else "FAIL"),
    ))

    protocol = get("protocol")
    checks.append(Check(
        "protocol",
        protocol if protocol else "not declared",
        REQUIRED_PROTOCOL,
        "PASS" if protocol == REQUIRED_PROTOCOL else ("BLOCKED" if protocol is None else "FAIL"),
    ))

    port_raw = get("port")
    port_ok = False
    if port_raw is not None:
        try:
            port_ok = int(port_raw) == REQUIRED_PORT
        except ValueError:
            port_ok = False
    checks.append(Check(
        "port",
        port_raw if port_raw else "not declared",
        str(REQUIRED_PORT),
        "PASS" if port_ok else ("BLOCKED" if port_raw is None else "FAIL"),
    ))

    service = get("service")
    checks.append(Check(
        "service",
        service if service else "not declared",
        REQUIRED_SERVICE + " only",
        "PASS" if service == REQUIRED_SERVICE else ("BLOCKED" if service is None else "FAIL"),
    ))

    peer_admission = get("peer_admission")
    checks.append(Check(
        "peer_admission",
        peer_admission if peer_admission else "not declared",
        REQUIRED_PEER_ADMISSION,
        "PASS" if peer_admission == REQUIRED_PEER_ADMISSION else ("BLOCKED" if peer_admission is None else "FAIL"),
    ))

    origin_scope = get("origin_allowed_ips")
    checks.append(Check(
        "origin_allowed_ips",
        origin_scope if origin_scope else "not declared",
        REQUIRED_ORIGIN_ALLOWED_IPS,
        "PASS" if origin_scope == REQUIRED_ORIGIN_ALLOWED_IPS else ("BLOCKED" if origin_scope is None else "FAIL"),
    ))

    laptop_scope = get("laptop_allowed_ips")
    checks.append(Check(
        "laptop_allowed_ips",
        laptop_scope if laptop_scope else "not declared",
        REQUIRED_LAPTOP_ALLOWED_IPS,
        "PASS" if laptop_scope == REQUIRED_LAPTOP_ALLOWED_IPS else ("BLOCKED" if laptop_scope is None else "FAIL"),
    ))

    for field in PROHIBITED_NONE_FIELDS:
        value = get(field)
        checks.append(Check(
            field,
            value if value else "not declared",
            "none",
            "PASS" if value == "none" else ("BLOCKED" if value is None else "FAIL"),
        ))

    return checks


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--declaration",
        type=Path,
        default=Path("deploy/wireguard/origin-transport-boundary.md"),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("evidence/public-deployment/wireguard-transport-boundary.md"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.declaration.exists():
        print(f"BLOCKED: declaration file not found at {args.declaration}", file=sys.stderr)
        checks = [Check("declaration-file", "missing", str(args.declaration), "BLOCKED")]
        write_evidence(
            args.evidence,
            "WireGuard Transport Boundary Evidence",
            "T058b",
            [],
            checks,
            "BLOCKED",
            footnote="Declares no live origin evidence: this checks the declaration only (SC-018). Live evidence is T066a.",
        )
        return 2

    try:
        fields = parse_declaration(args.declaration.read_text(encoding="utf-8"))
    except DeclarationParseError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        checks = [Check("declaration-block", str(exc), "a ```boundary fenced block", "BLOCKED")]
        write_evidence(
            args.evidence,
            "WireGuard Transport Boundary Evidence",
            "T058b",
            [],
            checks,
            "BLOCKED",
        )
        return 2

    checks = validate_declaration(fields)
    verdict = overall_verdict(checks)
    for check in checks:
        print(f"{check.verdict}: {check.name} - observed {check.observed!r}, expected {check.expected!r}")

    write_evidence(
        args.evidence,
        "WireGuard Transport Boundary Evidence",
        "T058b",
        [f"- Declaration source: {args.declaration}"],
        checks,
        verdict,
        footnote=(
            "Validates the declared boundary against contracts/compute-link.md C1a-1 "
            "(SC-018). This is not live-origin evidence; that is tasks.md T066a."
        ),
    )
    print(f"{verdict}: wireguard-transport-boundary evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
