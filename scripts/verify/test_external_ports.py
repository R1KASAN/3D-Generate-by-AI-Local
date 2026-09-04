"""Probe the public edge's TCP ports from outside the university network (T092).

Confirms 443/80 are reachable and 3000/8000/8188/3389/2019 are not, from a
genuinely external vantage point. Never probes 161.200.90.3 - only the
approved edge address may be targeted by anything in this repository.
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, mask_ip, overall_verdict, write_evidence  # noqa: E402

APPROVED_PUBLIC_ADDRESS = "161.200.90.4"

EXPECTED_OPEN = {443: "HTTPS (Caddy)", 80: "ACME/redirect (Caddy)"}
EXPECTED_CLOSED = {
    3000: "Next.js (must be reachable only via the WireGuard tunnel, never publicly)",
    8000: "FastAPI (loopback-only on the laptop, never on the edge)",
    8188: "ComfyUI (loopback-only on the laptop, never on the edge)",
    3389: "RDP (must never be reachable, on either box)",
    2019: "Caddy admin API (admin off)",
}


def _tcp_open(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-address", required=True)
    parser.add_argument("--confirm-off-campus", action="store_true")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/ports.md"))
    args = parser.parse_args()

    if args.public_address != APPROVED_PUBLIC_ADDRESS:
        print(f"BLOCKED: --public-address must be exactly {APPROVED_PUBLIC_ADDRESS}; refusing to probe any other address.")
        return 1

    if not args.confirm_off_campus:
        checks = [Check("vantage-point", "--confirm-off-campus was not supplied", "run from outside the university network", "BLOCKED")]
        write_evidence(args.evidence, "External Port Exposure Evidence", "T092", [f"- Edge address (masked): {mask_ip(args.public_address)}"], checks, "BLOCKED")
        print(f"BLOCKED: port evidence written to {args.evidence}")
        return 1

    checks = [Check("vantage-point", "operator attested off-campus", "run from outside the university network", "PASS")]

    for port, label in EXPECTED_OPEN.items():
        open_state = _tcp_open(args.public_address, port)
        checks.append(Check(f"port-{port}-open", "reachable" if open_state else "unreachable", f"{label} must be reachable", "PASS" if open_state else "FAIL"))

    for port, label in EXPECTED_CLOSED.items():
        open_state = _tcp_open(args.public_address, port)
        checks.append(Check(f"port-{port}-closed", "reachable" if open_state else "connection refused/filtered", f"{label} must NOT be reachable", "FAIL" if open_state else "PASS"))

    verdict = overall_verdict(checks)
    write_evidence(
        args.evidence,
        "External Port Exposure Evidence",
        "T092",
        [f"- Edge address (masked): {mask_ip(args.public_address)}"],
        checks,
        verdict,
        footnote="161.200.90.3 is never probed by this script or any other part of this repository.",
    )
    print(f"{verdict}: port evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
