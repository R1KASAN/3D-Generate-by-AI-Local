"""External corroboration for the four loopback-only application ports."""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

APPROVED_PUBLIC_ADDRESS = "161.200.90.4"
APPLICATION_PORTS = (3000, 8000, 8080, 8188)


def _probe(host: str, port: int, timeout: float) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "reachable"
    except ConnectionRefusedError:
        return "refused"
    except (TimeoutError, socket.timeout):
        return "timeout"
    except OSError:
        return "unreachable"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-address", required=True)
    parser.add_argument("--confirm-off-campus", action="store_true")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/feature-004/us4-public-boundary.md"))
    args = parser.parse_args()
    if args.public_address != APPROVED_PUBLIC_ADDRESS:
        print(f"BLOCKED: --public-address must be exactly {APPROVED_PUBLIC_ADDRESS}")
        return 2
    if not args.confirm_off_campus:
        print("BLOCKED: add --confirm-off-campus from a genuinely external network")
        return 2
    lines = ["# Feature 004 external application-port evidence", "", "- Vantage: operator-attested off-campus", f"- Address: {APPROVED_PUBLIC_ADDRESS}", "", "| Port | Observation | Expected |", "|---:|---|---|"]
    verdict = "PASS"
    for port in APPLICATION_PORTS:
        observation = _probe(args.public_address, port, 5.0)
        lines.append(f"| {port} | {observation} | refused/reset required; timeout is inconclusive |")
        if observation == "reachable":
            verdict = "FAIL"
        elif observation == "timeout" and verdict == "PASS":
            verdict = "INCONCLUSIVE"
    lines.extend(["", f"- Verdict: **{verdict}**", "- No DNS, forwarding, or firewall mutation was performed."])
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{verdict}: evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
